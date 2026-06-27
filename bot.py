# Установка: pip install aiogram
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ВСТАВЬТЕ СЮДА ВАШ ТОКЕН ОТ @BotFather
BOT_TOKEN = "8606858777:AAG8beK0_nsqLJmcekljugRbl-vR1onBdWM"
ADMIN_PASSWORD = "Qwerty12345"
ADMIN_USERNAME = "@PavelAlexandroviich"
PORTFOLIO_LINK = "https://t.me/BeaverStudio"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота, диспетчера и хранилища состояний
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Хранилище заявок (в памяти)
orders_db = []
admin_users = set()  # ID авторизованных админов

# Текст приветствия
START_TEXT = "Ква!🐸Рада приветствовать вас! Надеюсь вам у нас понравится!"

# ==================== FSM ДЛЯ ЗАКАЗА ====================
class OrderForm(StatesGroup):
    name = State()
    service_type = State()
    details = State()
    manager_contact = State()

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Цены и услуги", callback_data="prices")
    builder.button(text="📦 Доставка", callback_data="delivery")
    builder.button(text="✨ Гарантии и правки", callback_data="guarantees")
    builder.button(text="⏱️ Сроки выполнения", callback_data="terms")
    builder.button(text="🖼️ Портфолио", callback_data="portfolio")
    builder.button(text="📝 Оформление заказа", callback_data="order")
    builder.button(text="🔐 Войти как администратор", callback_data="admin_login")
    builder.adjust(1)
    return builder.as_markup()

def get_prices_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_back_button():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_yes_no_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Да")
    builder.button(text="❌ Нет")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_admin_panel():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Непросмотренные заявки", callback_data="admin_unseen")
    builder.button(text="🗂️ Все заявки", callback_data="admin_all")
    builder.button(text="🔙 Выйти из админки", callback_data="admin_logout")
    builder.adjust(1)
    return builder.as_markup()

def get_order_actions(order_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data=f"admin_done_{order_id}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    builder.button(text="💬 Написать пользователю", callback_data=f"admin_contact_{order_id}")
    builder.button(text="🔙 Назад", callback_data="admin_unseen")
    builder.adjust(1)
    return builder.as_markup()

# ==================== ТЕКСТЫ РАЗДЕЛОВ ====================
PRICES_TEXT = """
🎨 **ПРАЙС-ЛИСТ**

**• Диджитал работы** — от 800 ₽
_Учитывается объём, детализация и стиль._

**• Традиционные картины** — от 5 000 ₽
_Учитывается объём работы и затрата материалов._

**• Плакаты и кастом** — от 1 000 ₽
_Учитывается качество одежды, затрата материалов, разработка дизайна и стиль._

📌 **Традиционные работы:**
1. Дощечка с росписью (Гжель, Хохлома, Городетская и так далее)
2. Витраж
3. Текстурная картина (Белая/рельеф и цветная)

👕 **Изделия для повседневности:**
1. Роспись тканевой сумки
2. Футболки, толстовки
3. Хаори
4. Штаны

💬 Для точного расчета стоимости напишите в личные сообщения — стоимость уточняется при общении!
"""

DELIVERY_TEXT = """
📦 **ДОСТАВКА**

Отдельно оплачивается и зависит от выбранного пункта выдачи:

🚚 **Службы доставки:**
• Яндекс Доставка
• Ozon
• Wildberries
• СДЭК

💰 Стоимость уточняется при общении по вашему адресу.

Напишите ваш город и удобный пункт выдачи — рассчитаю стоимость доставки!
"""

GUARANTEES_TEXT = """
✨ **ГАРАНТИИ И ПРАВКИ**

✅ Гарантирую качество всех работ

🎨 **Что входит:**
• Все правки принимаются БЕЗ доплаты
• Делаю эскизы перед началом работы
• Адаптирую дизайн под ваши вкусы и пожелания
• Индивидуальный подход к каждому заказу

Ваше удовлетворение — мой приоритет! 🐸
"""

TERMS_TEXT = """
⏱️ **СРОКИ ВЫПОЛНЕНИЯ**

🖥️ **Диджитал, плакаты, кастом:**
1–2 недели

🎨 **Картины (традиционные):**
До 1 месяца

⚡ Возможна срочная работа — уточняйте при общении!
"""

PORTFOLIO_TEXT = f"""
🖼️ **ПОРТФОЛИО**

Для публикации вашего заказа в портфолио буду запрашивать ваше разрешение.

📸 Все работы публикуются только с согласия заказчика!

🔗 Посмотреть примеры работ: {PORTFOLIO_LINK}

Хотите заказать что-то похожее? Оформите заказ ниже! 🐸
"""

ORDER_START_TEXT = """
📝 **ОФОРМЛЕНИЕ ЗАКАЗА**

Давайте начнём! Пожалуйста, ответьте на несколько вопросов.

🔹 **Шаг 1/4**: Как к вам обращаться? (Ваше имя)
"""

ADMIN_LOGIN_TEXT = """
🔐 **ВХОД В АДМИН-ПАНЕЛЬ**

Введите пароль для доступа к панели управления.
"""

# ==================== ОБРАБОТЧИКИ КОМАНД И КНОПОК ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(START_TEXT, reply_markup=get_main_menu())

@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.answer(PRICES_TEXT, reply_markup=get_prices_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "delivery")
async def show_delivery(callback: types.CallbackQuery):
    await callback.message.answer(DELIVERY_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "guarantees")
async def show_guarantees(callback: types.CallbackQuery):
    await callback.message.answer(GUARANTEES_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "terms")
async def show_terms(callback: types.CallbackQuery):
    await callback.message.answer(TERMS_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "portfolio")
async def show_portfolio(callback: types.CallbackQuery):
    await callback.message.answer(PORTFOLIO_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "order")
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(ORDER_START_TEXT, reply_markup=types.ReplyKeyboardRemove())
    await callback.answer()
    await state.set_state(OrderForm.name)

@dp.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔹 **Шаг 2/4**: Что вы хотите заказать? (например: диджитал-арт, роспись футболки, картина и т.д.)", parse_mode="Markdown")
    await state.set_state(OrderForm.service_type)

@dp.message(OrderForm.service_type)
async def process_service(message: types.Message, state: FSMContext):
    await state.update_data(service_type=message.text)
    await message.answer("🔹 **Шаг 3/4**: Опишите подробнее ваше ТЗ (идея, референсы, размер, стиль и т.п.)", parse_mode="Markdown")
    await state.set_state(OrderForm.details)

@dp.message(OrderForm.details)
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    await message.answer("🔹 **Шаг 4/4**: Требуется ли вам связь с менеджером для уточнения деталей?", reply_markup=get_yes_no_keyboard(), parse_mode="Markdown")
    await state.set_state(OrderForm.manager_contact)

@dp.message(OrderForm.manager_contact, F.text.in_(["✅ Да", "❌ Нет"]))
async def process_manager_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    need_manager = (message.text == "✅ Да")
    
    # Формируем заявку
    order = {
        "id": len(orders_db) + 1,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Не указан",
        "name": data["name"],
        "service": data["service_type"],
        "details": data["details"],
        "need_manager": need_manager,
        "status": "new",  # new, done, rejected
        "date": message.date.strftime("%Y-%m-%d %H:%M")
    }
    orders_db.append(order)
    
    # Ответ пользователю
    if need_manager:
        await message.answer(
            f"✅ **Спасибо, {data['name']}!**\n\n"
            f"Ваша заявка №{order['id']} принята.\n"
            f"Менеджер свяжется с вами в ближайшее время: {ADMIN_USERNAME}\n\n"
            f"🐸 Хорошего дня!",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"✅ **Спасибо, {data['name']}!**\n\n"
            f"Ваша заявка №{order['id']} принята.\n"
            f"Мы свяжемся с вами при необходимости.\n\n"
            f"🐸 Хорошего дня!",
            reply_markup=get_back_button(),
            parse_mode="Markdown"
        )
    
    await state.clear()

# ==================== АДМИН-ПАНЕЛЬ ====================
@dp.callback_query(F.data == "admin_login")
async def admin_login_prompt(callback: types.CallbackQuery):
    await callback.message.answer(ADMIN_LOGIN_TEXT)
    await callback.answer()
    # Ждём ввод пароля через обычный обработчик сообщений

@dp.message(F.text == ADMIN_PASSWORD)
async def admin_auth_success(message: types.Message):
    user_id = message.from_user.id
    admin_users.add(user_id)
    await message.answer("✅ **Доступ разрешён!** Добро пожаловать в админ-панель 🐸", reply_markup=get_admin_panel(), parse_mode="Markdown")

@dp.message(F.text != ADMIN_PASSWORD)
async def admin_auth_fail(message: types.Message):
    if message.text and message.text.strip() and not message.text.startswith("/"):
        await message.answer("❌ Неверный пароль. Попробуйте ещё раз или нажмите /start для возврата в меню.")

@dp.callback_query(F.data == "admin_logout")
async def admin_logout(callback: types.CallbackQuery):
    admin_users.discard(callback.from_user.id)
    await callback.message.edit_text("🔐 Вы вышли из админ-панели.", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_unseen")
async def show_unseen_orders(callback: types.CallbackQuery):
    unseen = [o for o in orders_db if o["status"] == "new"]
    if not unseen:
        await callback.message.answer("🎉 Нет новых заявок!", reply_markup=get_admin_panel())
        await callback.answer()
        return
    
    for order in unseen:
        text = (
            f"📋 **Заявка №{order['id']}**\n"
            f"👤 Имя: {order['name']}\n"
            f"🔖 Пользователь: @{order['username']} (ID: {order['user_id']})\n"
            f"🎨 Услуга: {order['service']}\n"
            f"📝 ТЗ: {order['details']}\n"
            f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
            f"🕒 Дата: {order['date']}\n"
            f"📊 Статус: {order['status'].upper()}"
        )
        await callback.message.answer(text, reply_markup=get_order_actions(order["id"]), parse_mode="Markdown")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_done_"))
async def mark_order_done(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    for order in orders_db:
        if order["id"] == order_id:
            order["status"] = "done"
            break
    await callback.message.edit_text(f"✅ Заявка №{order_id} отмечена как выполненная.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_reject_"))
async def mark_order_rejected(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    for order in orders_db:
        if order["id"] == order_id:
            order["status"] = "rejected"
            break
    await callback.message.edit_text(f"❌ Заявка №{order_id} отклонена.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_contact_"))
async def contact_user(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    order = next((o for o in orders_db if o["id"] == order_id), None)
    if order:
        username = order["username"] if order["username"] != "Не указан" else f"ID: {order['user_id']}"
        await callback.message.answer(f"💬 Чтобы связаться с пользователем, напишите: @{username}" if username.startswith("@") else f"💬 Пользователь не имеет username. Его ID: {order['user_id']}")
    await callback.answer()

@dp.callback_query(F.data == "admin_all")
async def show_all_orders(callback: types.CallbackQuery):
    if not orders_db:
        await callback.message.answer("📭 Заявок пока нет.", reply_markup=get_admin_panel())
        await callback.answer()
        return
    
    for order in orders_db:
        text = (
            f"📋 **Заявка №{order['id']}**\n"
            f"👤 Имя: {order['name']}\n"
            f"🔖 Пользователь: @{order['username']}\n"
            f"🎨 Услуга: {order['service']}\n"
            f"📝 ТЗ: {order['details'][:100]}{'...' if len(order['details']) > 100 else ''}\n"
            f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
            f"🕒 Дата: {order['date']}\n"
            f"📊 Статус: {order['status'].upper()}"
        )
        await callback.message.answer(text, reply_markup=get_back_button(), parse_mode="Markdown")
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    # Если пользователь в админке — сначала выходим
    if callback.from_user.id in admin_users:
        await callback.message.edit_text(START_TEXT, reply_markup=get_main_menu())
    else:
        await callback.message.delete()
        await callback.message.answer(START_TEXT, reply_markup=get_main_menu())
    await callback.answer()

# ==================== ЗАПУСК ====================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

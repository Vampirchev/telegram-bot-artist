# Установка: pip install aiogram
import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8606858777:AAG8beK0_nsqLJmcekljugRbl-vR1onBdWM"
ADMIN_PASSWORD = "Qwerty12345"
MANAGERS = ["PavelAlexandoviich", "tosha_grak"]  # Юзернеймы менеджеров (без @)
PORTFOLIO_LINK = "https://t.me/BeaverStudio"
ORDERS_FILE = "orders.json"

logging.basicConfig(level=logging.INFO)

# ==================== РАБОТА С ФАЙЛОМ ====================
def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Ошибка загрузки файла заявок: {e}")
    return []

def save_orders():
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders_db, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка сохранения файла заявок: {e}")

# Инициализация
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
orders_db = load_orders()  # Загружаем при старте
admin_sessions = {}

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
    builder.button(text="💬 Связаться с менеджером", callback_data="contact_managers")
    builder.button(text="🔐 Админ-панель", callback_data="admin_login")
    builder.adjust(1)
    return builder.as_markup()

def get_contact_menu():
    builder = InlineKeyboardBuilder()
    for mgr in MANAGERS:
        builder.button(text=f"💬 @{mgr}", url=f"https://t.me/{mgr}")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
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
    builder.button(text="💬 Связаться с пользователем", callback_data=f"admin_contact_{order_id}")
    builder.button(text="🔙 Назад к заявкам", callback_data="admin_unseen")
    builder.adjust(1)
    return builder.as_markup()

# ==================== ТЕКСТЫ ====================
START_TEXT = "Ква!🐸Рада приветствовать вас! Надеюсь вам у нас понравится!"

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

💡 *Напишите /cancel в любой момент, чтобы отменить заказ*
"""

ADMIN_LOGIN_TEXT = """
🔐 **ВХОД В АДМИН-ПАНЕЛЬ**

Введите пароль для доступа к панели управления.
"""

# ==================== ОБРАБОТЧИКИ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(START_TEXT, reply_markup=get_main_menu())

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Заказ отменён. Возвращаюсь в главное меню 🐸", reply_markup=get_main_menu())
    else:
        await message.answer("🤔 Вы не оформляете заказ. Используйте меню для навигации 🐸")

# --- Основные кнопки меню ---
@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.edit_text(PRICES_TEXT, reply_markup=get_prices_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "delivery")
async def show_delivery(callback: types.CallbackQuery):
    await callback.message.edit_text(DELIVERY_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "guarantees")
async def show_guarantees(callback: types.CallbackQuery):
    await callback.message.edit_text(GUARANTEES_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "terms")
async def show_terms(callback: types.CallbackQuery):
    await callback.message.edit_text(TERMS_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "portfolio")
async def show_portfolio(callback: types.CallbackQuery):
    await callback.message.edit_text(PORTFOLIO_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "contact_managers")
async def contact_managers_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("💬 **Выберите менеджера для связи:**", reply_markup=get_contact_menu(), parse_mode="Markdown")
    await callback.answer()

# --- Форма заказа ---
@dp.callback_query(F.data == "order")
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        ORDER_START_TEXT, 
        reply_markup=get_contact_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()
    await state.set_state(OrderForm.name)

@dp.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    await state.update_data(name=message.text)
    await message.answer("🔹 **Шаг 2/4**: Что вы хотите заказать? (например: диджитал-арт, роспись футболки, картина и т.д.)", parse_mode="Markdown")
    await state.set_state(OrderForm.service_type)

@dp.message(OrderForm.service_type)
async def process_service(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    await state.update_data(service_type=message.text)
    await message.answer("🔹 **Шаг 3/4**: Опишите подробнее ваше ТЗ (идея, референсы, размер, стиль и т.п.)", parse_mode="Markdown")
    await state.set_state(OrderForm.details)

@dp.message(OrderForm.details)
async def process_details(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    await state.update_data(details=message.text)
    await message.answer("🔹 **Шаг 4/4**: Требуется ли вам связь с менеджером для уточнения деталей?", reply_markup=get_yes_no_keyboard(), parse_mode="Markdown")
    await state.set_state(OrderForm.manager_contact)

@dp.message(OrderForm.manager_contact, F.text.in_(["✅ Да", "❌ Нет"]))
async def process_manager_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    need_manager = (message.text == "✅ Да")
    
    order = {
        "id": len(orders_db) + 1,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Не указан",
        "name": data["name"],
        "service": data["service_type"],
        "details": data["details"],
        "need_manager": need_manager,
        "status": "new",
        "date": message.date.strftime("%Y-%m-%d %H:%M")
    }
    orders_db.append(order)
    save_orders()  # 💾 Сохраняем в файл
    
    if need_manager:
        await message.answer(
            f"✅ **Спасибо, {data['name']}!**\n\n"
            f"Ваша заявка №{order['id']} принята.\n"
            f"📩 Менеджеры свяжутся с вами: @PavelAlexandoviich или @tosha_grak\n\n"
            f"🐸 Хорошего дня!",
            reply_markup=get_contact_menu(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"✅ **Спасибо, {data['name']}!**\n\n"
            f"Ваша заявка №{order['id']} принята.\n"
            f"Мы свяжемся с вами при необходимости.\n\n"
            f"🐸 Хорошего дня!",
            reply_markup=get_contact_menu(),
            parse_mode="Markdown"
        )
    await state.clear()

# --- Админ-панель ---
@dp.callback_query(F.data == "admin_login")
async def admin_login_prompt(callback: types.CallbackQuery):
    await callback.message.edit_text(ADMIN_LOGIN_TEXT)
    await callback.answer()
    admin_sessions[callback.from_user.id] = {"step": "waiting_password"}

@dp.message(F.text == ADMIN_PASSWORD)
async def admin_auth_success(message: types.Message):
    user_id = message.from_user.id
    if admin_sessions.get(user_id, {}).get("step") == "waiting_password":
        admin_sessions[user_id] = {"step": "authorized"}
        await message.answer("✅ **Доступ разрешён!** Добро пожаловать в админ-панель 🐸", reply_markup=get_admin_panel(), parse_mode="Markdown")
    else:
        await message.answer("❌ Сначала войдите через кнопку в меню", reply_markup=get_main_menu())

@dp.message(F.text != ADMIN_PASSWORD)
async def admin_auth_fail(message: types.Message):
    user_id = message.from_user.id
    if admin_sessions.get(user_id, {}).get("step") == "waiting_password":
        await message.answer("❌ Неверный пароль. Попробуйте ещё раз или нажмите /start для возврата в меню.")

@dp.callback_query(F.data == "admin_logout")
async def admin_logout(callback: types.CallbackQuery):
    admin_sessions.pop(callback.from_user.id, None)
    await callback.message.edit_text("🔐 Вы вышли из админ-панели.", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_unseen")
async def show_unseen_orders(callback: types.CallbackQuery):
    unseen = [o for o in orders_db if o["status"] == "new"]
    if not unseen:
        await callback.message.edit_text("🎉 Нет новых заявок!", reply_markup=get_admin_panel())
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
    order = next((o for o in orders_db if o["id"] == order_id), None)
    
    if order:
        order["status"] = "done"
        save_orders()  # 💾 Сохраняем
        try:
            await bot.send_message(
                chat_id=order["user_id"],
                text=f"✅ **Заявка №{order_id} выполнена!**\n\n"
                     f"Спасибо за заказ, {order['name']}! 🐸\n"
                     f"Если остались вопросы — напишите @PavelAlexandoviich или @tosha_grak",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить уведомление пользователю {order['user_id']}: {e}")
        
        await callback.message.edit_text(f"✅ Заявка №{order_id} отмечена как выполненная. Пользователь уведомлён.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_reject_"))
async def mark_order_rejected(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    order = next((o for o in orders_db if o["id"] == order_id), None)
    
    if order:
        order["status"] = "rejected"
        save_orders()  # 💾 Сохраняем
        try:
            await bot.send_message(
                chat_id=order["user_id"],
                text=f"❌ **Заявка №{order_id} отклонена**\n\n"
                     f"{order['name']}, к сожалению, мы не можем выполнить ваш заказ в текущем виде.\n"
                     f"Вы можете уточнить детали у @PavelAlexandoviich или @tosha_grak и оформить новую заявку 🐸",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить уведомление пользователю {order['user_id']}: {e}")
        
        await callback.message.edit_text(f"❌ Заявка №{order_id} отклонена. Пользователь уведомлён.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_contact_"))
async def contact_user(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[-1])
    order = next((o for o in orders_db if o["id"] == order_id), None)
    if order:
        if order["username"] != "Не указан":
            await callback.message.answer(f"💬 Чтобы связаться с пользователем, напишите: @{order['username']}")
        else:
            await callback.message.answer(f"⚠️ У пользователя нет username. Его ID: {order['user_id']}\n\n"
                                        f"Вы можете написать ему, если он первым напишет боту.")
    await callback.answer()

@dp.callback_query(F.data == "admin_all")
async def show_all_orders(callback: types.CallbackQuery):
    if not orders_db:
        await callback.message.edit_text("📭 Заявок пока нет.", reply_markup=get_admin_panel())
        await callback.answer()
        return
    
    for order in orders_db:
        text = (
            f"📋 **Заявка №{order['id']}**\n"
            f"👤 Имя: {order['name']}\n"
            f"🔖 Пользователь: @{order['username']}\n"
            f"🎨 Услуга: {order['service']}\n"
            f"📝 ТЗ: {order['details'][:150]}{'...' if len(order['details']) > 150 else ''}\n"
            f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
            f"🕒 Дата: {order['date']}\n"
            f"📊 Статус: {order['status'].upper()}"
        )
        await callback.message.answer(text, reply_markup=get_back_button(), parse_mode="Markdown")
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(START_TEXT, reply_markup=get_main_menu())
    await callback.answer()

# ==================== ЗАПУСК ====================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info(f"✅ Загружено {len(orders_db)} заявок из файла")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# Установка: pip install aiogram
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8606858777:AAG8beK0_nsqLJmcekljugRbl-vR1onBdWM"
ADMIN_IDS = [713645590]  # 🔴 ЗАМЕНИТЕ на ID администраторов (узнайте у @userinfobot)
ADMIN_CHAT_ID = 5345617201  # 🔴 ЗАМЕНИТЕ на ID админ-чата или личного аккаунта
MANAGER_CONTACT = "PavelAlexandroviich"  # Только один менеджер
PORTFOLIO_LINK = "https://t.me/BeaverStudio"
DB_FILE = "orders.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ==================== РАБОТА С БАЗОЙ ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            details TEXT NOT NULL,
            need_manager BOOLEAN NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_order(user_id, username, name, service, details, need_manager, created_at):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, username, name, service, details, need_manager, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
    """, (user_id, username, name, service, details, need_manager, created_at))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_orders(status=None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM orders WHERE status = ? ORDER BY id DESC", (status,))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_order_status(order_id, new_status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

def get_order_by_id(order_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM orders")
    stats["total"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'new'")
    stats["new"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'done'")
    stats["done"] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'rejected'")
    stats["rejected"] = cursor.fetchone()[0]
    conn.close()
    return stats

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
init_db()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== FSM ДЛЯ ЗАКАЗА ====================
class OrderForm(StatesGroup):
    name = State()
    service_type = State()
    details = State()
    manager_contact = State()

# ==================== КЛАВИАТУРЫ ====================
def get_main_menu(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Цены и услуги", callback_data="prices")
    builder.button(text="📦 Доставка", callback_data="delivery")
    builder.button(text="✨ Гарантии и правки", callback_data="guarantees")
    builder.button(text="⏱️ Сроки выполнения", callback_data="terms")
    builder.button(text="🖼️ Портфолио", callback_data="portfolio")
    builder.button(text="📝 Оформление заказа", callback_data="order")
    builder.button(text="💬 Связаться с менеджером", callback_data="contact_managers")
    if user_id in ADMIN_IDS:
        builder.button(text="⚙️ Панель администратора", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()

def get_contact_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💬 @{MANAGER_CONTACT}", url=f"https://t.me/{MANAGER_CONTACT}")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_order_complete_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Вернуться в меню", callback_data="back_to_main")
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
    builder.button(text="🔙 Выйти из админки", callback_data="back_to_main")
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

# ==================== ОБРАБОТЧИКИ ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(START_TEXT, reply_markup=get_main_menu(message.from_user.id))

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Заказ отменён. Возвращаюсь в главное меню 🐸", reply_markup=get_main_menu(message.from_user.id))
    else:
        await message.answer("🤔 Вы не оформляете заказ. Используйте меню для навигации 🐸")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(START_TEXT, reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()

# --- Основные кнопки меню ---
@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.edit_text(PRICES_TEXT, reply_markup=get_back_button(), parse_mode="Markdown")
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
    await callback.message.edit_text("💬 **Написать менеджеру:**", reply_markup=get_contact_menu(), parse_mode="Markdown")
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
    
    # 💾 Сохраняем в SQLite
    order_id = add_order(
        user_id=message.from_user.id,
        username=message.from_user.username,
        name=data["name"],
        service=data["service_type"],
        details=data["details"],
        need_manager=need_manager,
        created_at=message.date.strftime("%Y-%m-%d %H:%M")
    )
    
    # 📢 Уведомление в админ-чат
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🆕 **Новая заявка №{order_id}**\n"
                f"👤 {data['name']} (@{message.from_user.username or 'нет юзернейма'})\n"
                f"🎨 Услуга: {data['service_type']}\n"
                f"📝 ТЗ: {data['details'][:120]}{'...' if len(data['details'])>120 else ''}\n"
                f"📞 Менеджер: {'✅ Да' if need_manager else '❌ Нет'}\n"
                f"🕒 Дата: {message.date.strftime('%Y-%m-%d %H:%M')}"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление в админ-чат: {e}")
    
    # Ответ пользователю
    await message.answer(
        f"✅ **Заявка №{order_id} отправлена!**\n\n"
        f"Спасибо, {data['name']}! 🐸\n"
        f"Мы свяжемся с вами при необходимости.\n\n"
        f"Нажмите кнопку ниже, чтобы вернуться в меню 👇",
        reply_markup=get_order_complete_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()

# --- Админ-панель ---
@dp.callback_query(F.data == "admin_panel")
async def open_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    stats = get_stats()
    stats_text = (
        f"📊 **СТАТИСТИКА ЗАЯВОК**\n\n"
        f"📦 Всего: {stats['total']}\n"
        f"🆕 Новые: {stats['new']}\n"
        f"✅ Выполнено: {stats['done']}\n"
        f"❌ Отклонено: {stats['rejected']}\n\n"
        f"🔹 Выберите действие:"
    )
    await callback.message.edit_text(stats_text, reply_markup=get_admin_panel(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_unseen")
async def show_unseen_orders(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
        
    unseen = get_orders(status="new")
    if not unseen:
        await callback.message.edit_text("🎉 Нет новых заявок!", reply_markup=get_admin_panel())
        await callback.answer()
        return
    
    for order in unseen:
        text = (
            f"📋 **Заявка №{order['id']}**\n"
            f"👤 Имя: {order['name']}\n"
            f"🔖 Пользователь: @{order['username'] or 'Не указан'} (ID: {order['user_id']})\n"
            f"🎨 Услуга: {order['service']}\n"
            f"📝 ТЗ: {order['details']}\n"
            f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
            f"🕒 Дата: {order['created_at']}\n"
            f"📊 Статус: {order['status'].upper()}"
        )
        await callback.message.answer(text, reply_markup=get_order_actions(order["id"]), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_done_"))
async def mark_order_done(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    order_id = int(callback.data.split("_")[-1])
    order = get_order_by_id(order_id)
    if order:
        update_order_status(order_id, "done")
        try:
            await bot.send_message(
                chat_id=order["user_id"],
                text=f"✅ **Заявка №{order_id} выполнена!**\n\nСпасибо за заказ, {order['name']}! 🐸\nЕсли остались вопросы — напишите @{MANAGER_CONTACT}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Не удалось уведомить пользователя {order['user_id']}: {e}")
        await callback.message.edit_text(f"✅ Заявка №{order_id} отмечена как выполненная.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_reject_"))
async def mark_order_rejected(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    order_id = int(callback.data.split("_")[-1])
    order = get_order_by_id(order_id)
    if order:
        update_order_status(order_id, "rejected")
        try:
            await bot.send_message(
                chat_id=order["user_id"],
                text=f"❌ **Заявка №{order_id} отклонена**\n\n{order['name']}, к сожалению, мы не можем выполнить заказ в текущем виде.\nУточните детали у @{MANAGER_CONTACT} и оформите новую заявку 🐸",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"Не удалось уведомить пользователя {order['user_id']}: {e}")
        await callback.message.edit_text(f"❌ Заявка №{order_id} отклонена.", reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_contact_"))
async def contact_user(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    order_id = int(callback.data.split("_")[-1])
    order = get_order_by_id(order_id)
    if order:
        username = order["username"]
        if username:
            await callback.message.answer(f"💬 Написать пользователю: @{username}")
        else:
            await callback.message.answer(f"⚠️ У пользователя нет username. Его ID: {order['user_id']}")
    await callback.answer()

@dp.callback_query(F.data == "admin_all")
async def show_all_orders(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    all_orders = get_orders()
    if not all_orders:
        await callback.message.edit_text("📭 Заявок пока нет.", reply_markup=get_admin_panel())
        await callback.answer()
        return
    for order in all_orders:
        text = (
            f"📋 **Заявка №{order['id']}**\n"
            f"👤 Имя: {order['name']}\n"
            f"🔖 Пользователь: @{order['username'] or 'Не указан'}\n"
            f"🎨 Услуга: {order['service']}\n"
            f"📝 ТЗ: {order['details'][:150]}{'...' if len(order['details']) > 150 else ''}\n"
            f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
            f"🕒 Дата: {order['created_at']}\n"
            f"📊 Статус: {order['status'].upper()}"
        )
        await callback.message.answer(text, reply_markup=get_back_button(), parse_mode="Markdown")
    await callback.answer()

# ==================== ЗАПУСК ====================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info(f"✅ Бот запущен. Админ-панель доступна для ID: {ADMIN_IDS}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

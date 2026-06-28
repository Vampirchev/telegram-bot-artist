# Установка: pip install aiogram aiohttp
import asyncio
import logging
import sqlite3
import os
import signal
import sys
import unicodedata
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8606858777:AAG8beK0_nsqLJmcekljugRbl-vR1onBdWM"
ADMIN_IDS = [123456789, 713645590]  # ✅ Ваши ID администраторов
ADMIN_CHAT_ID = -5345617201        # ✅ ID чата для уведомлений
MANAGER_CONTACT = "PavelAlexandroviich"
PORTFOLIO_LINK = "https://t.me/BeaverStudio"
DB_FILE = "orders.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ==================== УТИЛИТЫ ====================
def clean_telegram_text(text: str) -> str:
    """Удаляет скрытые символы, нормализует Unicode и убирает всё, что ломает Telegram"""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '<', '>']:
        text = text.replace(char, '')
    return text.strip()

# ==================== БАЗА ДАННЫХ ====================
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
            photo_file_id TEXT,
            need_manager BOOLEAN NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT NOT NULL
        )
    """)
    # Миграция: добавляем колонку photo_file_id, если её нет
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if "photo_file_id" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN photo_file_id TEXT")
    conn.commit()
    conn.close()

def add_order(user_id, username, name, service, details, photo_file_id, need_manager, created_at):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, username, name, service, details, photo_file_id, need_manager, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)
    """, (user_id, username, name, service, details, photo_file_id, need_manager, created_at))
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

# ==================== FSM ====================
class OrderForm(StatesGroup):
    name = State()
    service_type = State()
    details = State()
    photo = State()
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
🎨 <b>ПРАЙС-ЛИСТ</b>

<b>• Диджитал работы</b> — от 800 ₽
<i>Учитывается объём, детализация и стиль.</i>

<b>• Традиционные картины</b> — от 5 000 ₽
<i>Учитывается объём работы и затрата материалов.</i>

<b>• Плакаты и кастом</b> — от 1 000 ₽
<i>Учитывается качество одежды, затрата материалов, разработка дизайна и стиль.</i>

📌 <b>Традиционные работы:</b>
1. Дощечка с росписью (Гжель, Хохлома, Городетская и так далее)
2. Витраж
3. Текстурная картина (Белая/рельеф и цветная)

👕 <b>Изделия для повседневности:</b>
1. Роспись тканевой сумки
2. Футболки, толстовки
3. Хаори
4. Штаны

💬 Для точного расчета стоимости напишите в личные сообщения — стоимость уточняется при общении!
"""

DELIVERY_TEXT = """
📦 <b>ДОСТАВКА</b>

Отдельно оплачивается и зависит от выбранного пункта выдачи:

🚚 <b>Службы доставки:</b>
• Яндекс Доставка
• Ozon
• Wildberries
• СДЭК

💰 Стоимость уточняется при общении по вашему адресу.

Напишите ваш город и удобный пункт выдачи — рассчитаю стоимость доставки!
"""

GUARANTEES_TEXT = """
✨ <b>ГАРАНТИИ И ПРАВКИ</b>

✅ Гарантирую качество всех работ

🎨 <b>Что входит:</b>
• Все правки принимаются БЕЗ доплаты
• Делаю эскизы перед началом работы
• Адаптирую дизайн под ваши вкусы и пожелания
• Индивидуальный подход к каждому заказу

Ваше удовлетворение — мой приоритет! 🐸
"""

TERMS_TEXT = """
⏱️ <b>СРОКИ ВЫПОЛНЕНИЯ</b>

🖥️ <b>Диджитал, плакаты, кастом:</b>
1–2 недели

🎨 <b>Картины (традиционные):</b>
До 1 месяца

⚡ Возможна срочная работа — уточняйте при общении!
"""

PORTFOLIO_TEXT = f"""
🖼️ <b>ПОРТФОЛИО</b>

Для публикации вашего заказа в портфолио буду запрашивать ваше разрешение.

📸 Все работы публикуются только с согласия заказчика!

🔗 Посмотреть примеры работ: {PORTFOLIO_LINK}

Хотите заказать что-то похожее? Оформите заказ ниже! 🐸
"""

ORDER_START_TEXT = """
📝 <b>ОФОРМЛЕНИЕ ЗАКАЗА</b>

Давайте начнём! Пожалуйста, ответьте на несколько вопросов.

🔹 <b>Шаг 1/5</b>: Как к вам обращаться? (Ваше имя)

💡 <i>Напишите /cancel в любой момент, чтобы отменить заказ</i>
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

@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.edit_text(PRICES_TEXT, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "delivery")
async def show_delivery(callback: types.CallbackQuery):
    await callback.message.edit_text(DELIVERY_TEXT, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "guarantees")
async def show_guarantees(callback: types.CallbackQuery):
    await callback.message.edit_text(GUARANTEES_TEXT, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "terms")
async def show_terms(callback: types.CallbackQuery):
    await callback.message.edit_text(TERMS_TEXT, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "portfolio")
async def show_portfolio(callback: types.CallbackQuery):
    await callback.message.edit_text(PORTFOLIO_TEXT, reply_markup=get_back_button(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "contact_managers")
async def contact_managers_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("💬 <b>Написать менеджеру:</b>", reply_markup=get_contact_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "order")
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(ORDER_START_TEXT, reply_markup=get_contact_menu(), parse_mode="HTML")
    await callback.answer()
    await state.set_state(OrderForm.name)

@dp.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"): return
    await state.update_data(name=message.text)
    await message.answer("🔹 <b>Шаг 2/5</b>: Что вы хотите заказать?", parse_mode="HTML")
    await state.set_state(OrderForm.service_type)

@dp.message(OrderForm.service_type)
async def process_service(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"): return
    await state.update_data(service_type=message.text)
    await message.answer("🔹 <b>Шаг 3/5</b>: Опишите подробнее ваше ТЗ", parse_mode="HTML")
    await state.set_state(OrderForm.details)

@dp.message(OrderForm.details)
async def process_details(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/"): return
    await state.update_data(details=message.text)
    await message.answer("🔹 <b>Шаг 4/5</b>: Прикрепите фото/референс (необязательно). Отправьте изображение или напишите 'нет' для пропуска.", parse_mode="HTML")
    await state.set_state(OrderForm.photo)

@dp.message(OrderForm.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    await message.answer("🔹 <b>Шаг 5/5</b>: Требуется ли связь с менеджером?", reply_markup=get_yes_no_keyboard(), parse_mode="HTML")
    await state.set_state(OrderForm.manager_contact)

@dp.message(OrderForm.manager_contact, F.text.in_(["✅ Да", "❌ Нет"]))
async def process_manager_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    need_manager = (message.text == "✅ Да")
    
    order_id = add_order(
        user_id=message.from_user.id,
        username=message.from_user.username,
        name=data["name"],
        service=data["service_type"],
        details=data["details"],
        photo_file_id=data.get("photo_file_id"),
        need_manager=need_manager,
        created_at=message.date.strftime("%Y-%m-%d %H:%M")
    )
    
    try:
        admin_text = (
            f"🆕 Новая заявка №{order_id}\n"
            f"👤 {data['name']} (@{message.from_user.username or 'нет'})\n"
            f"🎨 Услуга: {data['service_type']}\n"
            f"📝 ТЗ: {data['details'][:150]}{'...' if len(data['details'])>150 else ''}\n"
            f"📎 Фото: {'✅ Есть' if data.get('photo_file_id') else '❌ Нет'}\n"
            f"📞 Менеджер: {'✅ Да' if need_manager else '❌ Нет'}\n"
            f"🕒 Дата: {message.date.strftime('%Y-%m-%d %H:%M')}"
        )
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    except Exception as e:
        logging.warning(f"Не отправлено в админ-чат: {e}")
    
    await message.answer(
        f"✅ <b>Заявка №{order_id} отправлена!</b>\n\n"
        f"Спасибо, {clean_telegram_text(data['name'])}! 🐸\n"
        f"Мы свяжемся с вами при необходимости.\n\n"
        f"Нажмите кнопку ниже 👇",
        reply_markup=get_order_complete_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()

# --- Админ-панель ---
@dp.callback_query(F.data == "admin_panel")
async def open_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    stats = get_stats()
    await callback.message.edit_text(
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"📦 Всего: {stats['total']}\n"
        f"🆕 Новые: {stats['new']}\n"
        f"✅ Выполнено: {stats['done']}\n"
        f"❌ Отклонено: {stats['rejected']}\n\n"
        f"🔹 Выберите действие:",
        reply_markup=get_admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()

def format_order_caption(order: dict) -> str:
    return (
        f"📋 Заявка №{order['id']}\n"
        f"👤 Имя: {clean_telegram_text(order['name'])}\n"
        f"🔖 Пользователь: @{clean_telegram_text(order['username'] or 'Не указан')} (ID: {order['user_id']})\n"
        f"🎨 Услуга: {clean_telegram_text(order['service'])}\n"
        f"📝 ТЗ: {clean_telegram_text(order['details'])}\n"
        f"📎 Фото: {'✅ Прикреплено' if order.get('photo_file_id') else '❌ Нет'}\n"
        f"📞 Менеджер: {'✅ Да' if order['need_manager'] else '❌ Нет'}\n"
        f"🕒 Дата: {order['created_at']}\n"
        f"📊 Статус: {order['status'].upper()}"
    )

async def send_order_to_admin(callback: types.CallbackQuery, order: dict, reply_markup):
    caption = format_order_caption(order)
    try:
        if order.get("photo_file_id"):
            await callback.message.answer_photo(
                photo=order["photo_file_id"],
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await callback.message.answer(text=caption, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Ошибка отправки заявки {order['id']}: {e}")
        await callback.message.answer("⚠️ Не удалось отобразить заявку", reply_markup=get_back_button())

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
        await send_order_to_admin(callback, order, get_order_actions(order["id"]))
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
                text=f"✅ Заявка №{order_id} выполнена!\n\nСпасибо за заказ, {clean_telegram_text(order['name'])}! 🐸\nЕсли остались вопросы — напишите @{MANAGER_CONTACT}"
            )
        except: pass
        await callback.message.edit_text(f"✅ Заявка №{order_id} выполнена.", reply_markup=get_admin_panel())
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
                text=f"❌ Заявка №{order_id} отклонена\n\n{clean_telegram_text(order['name'])}, к сожалению, мы не можем выполнить заказ в текущем виде.\nУточните детали у @{MANAGER_CONTACT} и оформите новую заявку 🐸"
            )
        except: pass
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
            await callback.message.answer(f"💬 Написать пользователю: @{clean_telegram_text(username)}")
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
        await send_order_to_admin(callback, order, get_back_button())
    await callback.answer()

# ==================== HTTP-SERVER ДЛЯ RENDER ====================
async def handle_health(request):
    return web.Response(text="🐸 Bot is alive!", content_type="text/plain")

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info(f"🌐 HTTP-сервер запущен на порту {port}")
    return runner

# ==================== ЗАПУСК ====================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    if os.getenv("PORT"):
        await start_http_server()
    logging.info("✅ Бот запущен (polling + dummy HTTP)")
    await dp.start_polling(bot)

def handle_shutdown(signum, frame):
    logging.info("🔄 Завершение работы...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

if __name__ == "__main__":
    asyncio.run(main())

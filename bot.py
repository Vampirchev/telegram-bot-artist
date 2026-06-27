# Установка: pip install aiogram
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ВСТАВЬТЕ СЮДА ВАШ ТОКЕН ОТ @BotFather
BOT_TOKEN = "8606858777:AAG8beK0_nsqLJmcekljugRbl-vR1onBdWM"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Текст приветствия
START_TEXT = "Ква!🐸Рада приветствовать вас! Надеюсь вам у нас понравится!"

# Создаем главное меню
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Цены и услуги", callback_data="prices")
    builder.button(text="📦 Доставка", callback_data="delivery")
    builder.button(text="✨ Гарантии и правки", callback_data="guarantees")
    builder.button(text="⏱️ Сроки выполнения", callback_data="terms")
    builder.button(text="️ Портфолио", callback_data="portfolio")
    builder.button(text="📝 Оформление заказа", callback_data="order")
    builder.adjust(1)  # Кнопки в один столбец
    return builder.as_markup()

# Цены и услуги
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

💬 Для точного расчета стоимости напишите в ЛС!
"""

def get_prices_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

# Доставка
DELIVERY_TEXT = """
📦 **ДОСТАВКА**

Отдельно оплачивается и зависит от выбранного пункта выдачи:

🚚 **Службы доставки:**
• Яндекс Доставка
• Ozon
• Wildberries
• СДЭК

💰 Стоимость уточняется по вашему адресу.

Напишите ваш город и удобный пункт выдачи — рассчитаю стоимость доставки!
"""

# Гарантии
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

# Сроки
TERMS_TEXT = """
⏱️ **СРОКИ ВЫПОЛНЕНИЯ**

🖥️ **Диджитал, плакаты, кастом:**
1–2 недели

🎨 **Картины (традиционные):**
До 1 месяца

⚡ Возможна срочная работа — уточняйте в ЛС!
"""

# Портфолио
PORTFOLIO_TEXT = """
🖼️ **ПОРТФОЛИО**

Для публикации вашего заказа в портфолио буду запрашивать ваше разрешение.

📸 Все работы публикуются только с согласия заказчика!

Хотите посмотреть примеры работ? Напишите в ЛС — с радостью покажу!
"""

# Оформление заказа
ORDER_TEXT = """
📝 **ОФОРМЛЕНИЕ ЗАКАЗОВ**

Заказы обсуждаются в личных сообщениях (ЛС).

📋 **Что нужно указать:**
1. Тип работы (диджитал/традиция/кастом)
2. Размер/формат
3. Идею или референсы
4. Желаемые сроки

💬 **Напишите мне:**
@YOUR_USERNAME (замените на ваш ник)

Или просто напишите любое сообщение — я отвечу! 🐸
"""

def get_back_button():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        START_TEXT,
        reply_markup=get_main_menu()
    )

# Обработчики кнопок
@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.answer(
        PRICES_TEXT,
        reply_markup=get_prices_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "delivery")
async def show_delivery(callback: types.CallbackQuery):
    await callback.message.answer(
        DELIVERY_TEXT,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "guarantees")
async def show_guarantees(callback: types.CallbackQuery):
    await callback.message.answer(
        GUARANTEES_TEXT,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "terms")
async def show_terms(callback: types.CallbackQuery):
    await callback.message.answer(
        TERMS_TEXT,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "portfolio")
async def show_portfolio(callback: types.CallbackQuery):
    await callback.message.answer(
        PORTFOLIO_TEXT,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "order")
async def show_order(callback: types.CallbackQuery):
    await callback.message.answer(
        ORDER_TEXT,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        START_TEXT,
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# 1. Загружаем настройки
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ Ошибка: Не найден BOT_TOKEN в файле .env")
    exit(1)

# 2. Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

# 3. Тексты и кнопки
START_TEXT = "Ква!🐸Рада приветствовать вас! Надеюсь вам у нас понравится!"

def get_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Цены", callback_data="prices")
    builder.button(text=" Доставка", callback_data="delivery")
    builder.button(text="✨ Гарантии", callback_data="guarantees")
    builder.button(text="⏱️ Сроки", callback_data="terms")
    builder.button(text="🖼️ Портфолио", callback_data="portfolio")
    builder.button(text="📝 Заказ", callback_data="order")
    builder.adjust(1)
    return builder.as_markup()

def get_back():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()

PRICES_TEXT = """
🎨 **ПРАЙС-ЛИСТ**
**• Диджитал работы** — от 800 ₽
**• Традиционные картины** — от 5 000 ₽
**• Плакаты и кастом** — от 1 000 ₽
_Подробнее в ЛС_
"""

# 4. Инициализация бота
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(START_TEXT, reply_markup=get_menu())

@dp.callback_query(F.data == "prices")
async def show_prices(callback: types.CallbackQuery):
    await callback.message.answer(PRICES_TEXT, reply_markup=get_back(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(START_TEXT, reply_markup=get_menu())
    await callback.answer()

# 5. Запуск
async def main():
    # Создаем бота БЕЗ явного указания session (использует системный интернет)
    bot = Bot(token=BOT_TOKEN)
    
    try:
        logger.info("🚀 Бот запущен! Жду команды /start...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

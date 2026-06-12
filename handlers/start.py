"""
========================================================================
 МОДУЛЬ: 1-я страница менеджера (/start, главное меню).
========================================================================
"""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from database import add_user, get_user_bots
from keyboards import main_menu_kb

router = Router()

# Текст первой страницы (как на скриншоте).
MAIN_PAGE_TEXT = (
    "👑 <b>Ваши боты:</b>\n\n"
    "🟣 У нас реализована функция обработки заявок в канал!\n\n"
    "❗️ Добавьте созданного вами бота в админы закрытого канала, "
    "и при подаче заявки бот напишет человеку первым!"
)


async def show_main_page(message: Message) -> None:
    add_user(message.chat.id, message.chat.username)
    user_bots = get_user_bots(message.chat.id)
    await message.answer(MAIN_PAGE_TEXT, reply_markup=main_menu_kb(user_bots))


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await show_main_page(message)


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery) -> None:
    user_bots = get_user_bots(callback.from_user.id)
    await callback.message.edit_text(
        MAIN_PAGE_TEXT, reply_markup=main_menu_kb(user_bots)
    )
    await callback.answer()

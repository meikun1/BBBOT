"""
Утилиты единого «якорного» сообщения.

Чтобы чат не превращался в простыню: при запросе ввода запоминаем
сообщение бота (anchor), а после ответа пользователя — удаляем его
сообщение и редактируем тот же anchor, показывая результат.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def remember_anchor(callback: CallbackQuery, state: FSMContext) -> None:
    """Запомнить сообщение, которое потом будем редактировать."""
    msg = callback.message
    if msg is not None:
        await state.update_data(_anchor_chat=msg.chat.id, _anchor_msg=msg.message_id)


async def edit_anchor(
    message: Message,
    data: dict,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Удалить сообщение пользователя и показать результат в anchor-сообщении."""
    with suppress(Exception):
        await message.delete()  # боты могут удалять входящие в личке
    chat = data.get("_anchor_chat")
    mid = data.get("_anchor_msg")
    if chat and mid:
        with suppress(TelegramBadRequest):
            await message.bot.edit_message_text(
                text, chat_id=chat, message_id=mid, reply_markup=reply_markup
            )
            return
    # фолбэк, если anchor потерян/не редактируется
    await message.answer(text, reply_markup=reply_markup)

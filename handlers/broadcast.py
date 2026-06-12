"""
========================================================================
 МОДУЛЬ: «📨 Рассылка» (для одного бота)
------------------------------------------------------------------------
 Рассылает сообщение всем, кто запускал выбранного бота. Отправка идёт
 от имени самого дочернего бота (по его токену).
========================================================================
"""

import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import get_bot, get_bot_user_ids
from handlers.cards import owns

router = Router()


class Broadcast(StatesGroup):
    waiting_for_text = State()


def _back_kb(bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bot:{bot_id}")]
        ]
    )


@router.callback_query(F.data.startswith("broadcast:"))
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(callback.data.split(":")[1])
    bot = get_bot(bot_id)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    audience = len(get_bot_user_ids(bot.get("tg_id"))) if bot.get("tg_id") else 0
    await state.set_state(Broadcast.waiting_for_text)
    await state.update_data(bot_id=bot_id)
    await callback.message.edit_text(
        f"📨 <b>Рассылка</b> — {bot['username']}\n\n"
        f"Аудитория: <b>{audience}</b> чел.\n\n"
        "Пришлите текст сообщения для рассылки 👇",
        reply_markup=_back_kb(bot_id),
    )
    await callback.answer()


@router.message(Broadcast.waiting_for_text, F.text)
async def do_broadcast(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bot_id = data["bot_id"]
    await state.clear()

    bot = get_bot(bot_id)
    if not bot or not bot.get("tg_id"):
        await message.answer("Бот не найден.")
        return

    user_ids = get_bot_user_ids(bot["tg_id"])
    if not user_ids:
        await message.answer(
            "Некому отправлять — бота ещё никто не запускал.",
            reply_markup=_back_kb(bot_id),
        )
        return

    text = message.text
    status = await message.answer(f"Отправляю… 0/{len(user_ids)}")

    child = Bot(token=bot["token"])
    sent = failed = 0
    try:
        for i, uid in enumerate(user_ids, 1):
            try:
                await child.send_message(uid, text)
                sent += 1
            except Exception:
                failed += 1
            if i % 25 == 0:
                try:
                    await status.edit_text(f"Отправляю… {i}/{len(user_ids)}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)  # бережём лимиты Telegram
    finally:
        await child.session.close()

    await status.edit_text(
        f"✅ Рассылка завершена.\n\nДоставлено: {sent}\nНе доставлено: {failed}",
        reply_markup=_back_kb(bot_id),
    )

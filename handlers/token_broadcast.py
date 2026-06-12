"""
========================================================================
 МОДУЛЬ: «📣 Рассылка по токенам» (с главной страницы)
------------------------------------------------------------------------
 Рассылает одно сообщение через ВСЕ боты владельца: каждый бот шлёт
 текст своим запускавшим юзерам.
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

from database import get_bot_user_ids, get_user_bots

router = Router()


class TokenBroadcast(StatesGroup):
    waiting_for_text = State()


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ]
    )


@router.callback_query(F.data == "token_broadcast")
async def start(callback: CallbackQuery, state: FSMContext) -> None:
    bots = get_user_bots(callback.from_user.id)
    if not bots:
        await callback.answer("У вас пока нет ботов.", show_alert=True)
        return
    await state.set_state(TokenBroadcast.waiting_for_text)
    await callback.message.edit_text(
        "📣 <b>Рассылка по токенам</b>\n\n"
        f"Сообщение уйдёт через все ваши боты ({len(bots)} шт.) их юзерам.\n\n"
        "Пришлите текст рассылки 👇",
        reply_markup=_back_kb(),
    )
    await callback.answer()


@router.message(TokenBroadcast.waiting_for_text, F.text)
async def run(message: Message, state: FSMContext) -> None:
    await state.clear()
    bots = get_user_bots(message.from_user.id)
    text = message.text

    status = await message.answer("Запускаю рассылку по токенам… ⏳")
    total_sent = total_failed = 0

    for bot in bots:
        tg_id = bot.get("tg_id")
        if not tg_id:
            continue
        user_ids = get_bot_user_ids(tg_id)
        if not user_ids:
            continue
        child = Bot(token=bot["token"])
        try:
            for uid in user_ids:
                try:
                    await child.send_message(uid, text)
                    total_sent += 1
                except Exception:
                    total_failed += 1
                await asyncio.sleep(0.05)
        finally:
            await child.session.close()

    await status.edit_text(
        f"✅ Рассылка по токенам завершена.\n\n"
        f"Доставлено: {total_sent}\nНе доставлено: {total_failed}",
        reply_markup=_back_kb(),
    )

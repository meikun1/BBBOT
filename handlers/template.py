"""
========================================================================
 МОДУЛЬ: «📋 Изменить шаблон»
------------------------------------------------------------------------
 Выбор шаблона дочернего бота — что он показывает юзеру после входа.
========================================================================
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_bot, update_bot_field
from handlers.cards import owns
from templates import TEMPLATES, template_name

router = Router()


def _kb(bot: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    current = bot.get("template") or "standard"
    for tid, name in TEMPLATES.items():
        mark = "✅ " if tid == current else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{mark}{name}", callback_data=f"tpl_set:{bot['id']}:{tid}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bot:{bot['id']}")
    )
    return builder.as_markup()


def _text(bot: dict) -> str:
    return (
        "📋 <b>Изменить шаблон</b>\n\n"
        f"Текущий шаблон: <b>{template_name(bot.get('template'))}</b>\n\n"
        "Выберите шаблон ниже:"
    )


@router.callback_query(F.data.startswith("template:"))
async def open_template(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    await callback.message.edit_text(_text(bot), reply_markup=_kb(bot))
    await callback.answer()


@router.callback_query(F.data.startswith("tpl_set:"))
async def set_template(callback: CallbackQuery) -> None:
    _, bot_id_str, tid = callback.data.split(":")
    bot_id = int(bot_id_str)
    bot = get_bot(bot_id)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    if tid not in TEMPLATES:
        await callback.answer("Неизвестный шаблон.", show_alert=True)
        return
    update_bot_field(bot_id, "template", tid)
    bot = get_bot(bot_id)
    await callback.message.edit_text(_text(bot), reply_markup=_kb(bot))
    await callback.answer("Шаблон изменён ✅")

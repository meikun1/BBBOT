"""
========================================================================
 МОДУЛЬ: «📋 Изменить шаблон» → меню шаблонов
------------------------------------------------------------------------
 Шаблон дочернего бота — что он показывает/пишет юзеру после входа.

 Структура (как в макете):
   📋 Меню шаблонов
   [ Текущий шаблон ]                 ← открывает выбор шаблона
   [⚙️ Создать шаблон] [➕ Стандартный шаблон]
   [💎 Шаблоны мини-апп]
   [📥 Добавить по коду] [⬅️ Назад]

 Пункты «Создать/Добавить/Мини-апп» — заглушки (в разработке), наполняем
 по мере развития модуля.
========================================================================
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_bot, update_bot_field
from handlers.cards import owns
from templates import TEMPLATES, template_name

router = Router()


# ----------------------------------------------------------- меню шаблонов
def _menu_text(bot: dict) -> str:
    return "📋 <b>Меню шаблонов:</b>"


def _menu_kb(bot: dict) -> InlineKeyboardMarkup:
    bid = bot["id"]
    b = InlineKeyboardBuilder()
    # текущий шаблон (на всю ширину) — открывает выбор
    b.row(
        InlineKeyboardButton(
            text=template_name(bot.get("template")),
            callback_data=f"tpl_pick:{bid}",
        )
    )
    b.row(
        InlineKeyboardButton(
            text="⚙️ Создать шаблон", callback_data=f"tpl_soon:{bid}:create"
        ),
        InlineKeyboardButton(
            text="➕ Стандартный шаблон", callback_data=f"tpl_soon:{bid}:addstd"
        ),
    )
    b.row(
        InlineKeyboardButton(
            text="💎 Шаблоны мини-апп", callback_data=f"tpl_soon:{bid}:miniapp"
        )
    )
    b.row(
        InlineKeyboardButton(
            text="📥 Добавить по коду", callback_data=f"tpl_soon:{bid}:code"
        ),
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bot:{bid}"),
    )
    return b.as_markup()


# --------------------------------------------------------- выбор шаблона
def _picker_text(bot: dict) -> str:
    return (
        "📋 <b>Выбор шаблона</b>\n\n"
        f"Текущий: <b>{template_name(bot.get('template'))}</b>\n\n"
        "Нажмите, чтобы выбрать:"
    )


def _picker_kb(bot: dict) -> InlineKeyboardMarkup:
    bid = bot["id"]
    current = bot.get("template") or "standard"
    b = InlineKeyboardBuilder()
    for tid, name in TEMPLATES.items():
        mark = "✅ " if tid == current else ""
        b.row(
            InlineKeyboardButton(
                text=f"{mark}{name}", callback_data=f"tpl_set:{bid}:{tid}"
            )
        )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"template:{bid}"))
    return b.as_markup()


# ----------------------------------------------------------------- хендлеры
@router.callback_query(F.data.startswith("template:"))
async def open_menu(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    await callback.message.edit_text(_menu_text(bot), reply_markup=_menu_kb(bot))
    await callback.answer()


@router.callback_query(F.data.startswith("tpl_pick:"))
async def open_picker(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    await callback.message.edit_text(_picker_text(bot), reply_markup=_picker_kb(bot))
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
    # после выбора возвращаемся в меню шаблонов
    await callback.message.edit_text(_menu_text(bot), reply_markup=_menu_kb(bot))
    await callback.answer("Шаблон изменён ✅")


@router.callback_query(F.data.startswith("tpl_soon:"))
async def not_ready(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)

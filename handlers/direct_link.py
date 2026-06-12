"""
========================================================================
 МОДУЛЬ: «🔗 Прямая ссылка» (внутри Настроек бота)
------------------------------------------------------------------------
 Обёртка над пакетом direct_link/ для управления из бота-менеджера.

 Что делает:
  • показывает постоянную прямую ссылку на мини-апп (startapp=<токен>),
    генерируется один раз на бота;
  • переключатель вкл/выкл;
  • объясняет, что нужно поставить мини-апп ссылку в @BotFather (мануал),
    и что после включения бот перестаёт реагировать на /start;
  • при заходе в мини-апп без правильной ссылки юзера редиректит на
    сторонний ресурс (DIRECT_LINK_REDIRECT_URL).
========================================================================
"""

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import get_bot
from directlink_service import get_module
from handlers.cards import owns

router = Router()


async def _render(callback: CallbackQuery, bot: dict) -> None:
    tg_id = bot.get("tg_id")
    module = get_module()

    if not tg_id:
        await callback.message.edit_text(
            "⚠️ Бот ещё не инициализирован (нет telegram-id). "
            "Перезапустите бота и попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"settings:{bot['id']}")]
                ]
            ),
        )
        return

    state = await module.get_or_init(tg_id)
    startapp_url = await module.build_url(tg_id)
    manual_url = module.config.manual_url
    enabled = state["enabled"]

    text = (
        "🔗 <b>Прямая ссылка</b>\n\n"
        "❓ Для включения необходимо установить через @BotFather мини-апп "
        f'ссылку на бота. Посмотрите <a href="{manual_url}">мануал</a>, как '
        "правильно это сделать. После установки ссылки в ботфазере, прямая "
        "ссылка начнёт работать через 10–15 минут.\n\n"
        f"🔗 Прямая ссылка на мини-апп:\n{startapp_url}\n\n"
        "✳️ При включении этой функции бот перестанет реагировать на "
        "<code>/start</code> — пользователи смогут зайти только по прямой "
        "ссылке. Без правильной ссылки мини-апп перенаправит их на другой ресурс.\n\n"
        f"Статус: <b>{'🟢 включено' if enabled else '🔴 выключено'}</b>"
    )

    toggle = "🔴 Выключить" if enabled else "🟢 Включить"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle, callback_data=f"dl_toggle:{bot['id']}")],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"settings:{bot['id']}"
                )
            ],
        ]
    )
    await callback.message.edit_text(
        text, reply_markup=kb, disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("dl:"))
async def open_direct_link(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    await _render(callback, bot)
    await callback.answer()


@router.callback_query(F.data.startswith("dl_toggle:"))
async def toggle_direct_link(callback: CallbackQuery) -> None:
    bot = get_bot(int(callback.data.split(":")[1]))
    if not owns(callback.from_user.id, bot):
        await callback.answer("Бот не найден.", show_alert=True)
        return
    tg_id = bot.get("tg_id")
    if not tg_id:
        await callback.answer("Бот не инициализирован.", show_alert=True)
        return
    module = get_module()
    state = await module.get_or_init(tg_id)
    await module.storage.set_enabled(tg_id, not state["enabled"])
    # Зеркалим статус в карточку бота.
    from database import update_bot_field

    update_bot_field(bot["id"], "miniapp_enabled", 0 if state["enabled"] else 1)
    await _render(callback, bot)
    await callback.answer("Готово ✅")

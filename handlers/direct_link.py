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

    from config import MINIAPP_BASE_URL

    if MINIAPP_BASE_URL:
        webapp_url = f"{MINIAPP_BASE_URL}/app/{tg_id}"
        webapp_block = (
            "🌐 Web App URL для @BotFather (Bot Settings → Configure Mini App):\n"
            f"<code>{webapp_url}</code>\n\n"
        )
    else:
        webapp_block = (
            "🌐 Web App URL: задайте переменную <code>MINIAPP_BASE_URL</code> "
            "(HTTPS-домен), чтобы получить ссылку для @BotFather.\n\n"
        )

    text = (
        "🔗 <b>Прямая ссылка</b>\n\n"
        "🔴 <b>Выключено</b> — бот работает сам: на заявку в канал и на "
        "<code>/start</code> он пишет приветствие и даёт кнопку, которая "
        "открывает мини-апп прямо в чате. Настройка в @BotFather не нужна.\n\n"
        "🟢 <b>Включено</b> — вход только через мини-апп по startapp-ссылке. "
        "Бот перестаёт реагировать на <code>/start</code>. Нужно один раз "
        "вставить Web App URL в @BotFather (Bot Settings → Configure Mini App "
        f'→ <b>Main App</b>), см. <a href="{manual_url}">мануал</a>. Тогда по '
        "ссылке-приглашению мини-апп откроется сразу. Изменения в BotFather "
        "подхватываются ~10–15 минут.\n\n"
        f"{webapp_block}"
        f"🔗 Прямая ссылка на мини-апп (для юзеров):\n{startapp_url}\n\n"
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

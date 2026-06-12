"""
Логика дочернего бота (того, что добавили по токену).

Что умеет дочерний бот:
  • Обработка заявок в канал — при подаче заявки бот пишет человеку первым
    и (если включён авто-приём) принимает заявку.
  • Секретный /start (Guard «Защита от бана») — если защита включена, бот
    отвечает только на deep-link со своим секретом, иначе молчит.
  • Прямая ссылка — middleware глушит /start, когда модуль включён.
  • Учёт запусков для статистики (user_id + гео по языку клиента).

Свежие настройки бота читаются из БД на каждый апдейт по tg_id
(event.bot.id), чтобы изменения из менеджера применялись сразу.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    ChatJoinRequest,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import get_bot_by_tg_id, record_launch
from direct_link.aiogram_integration import DirectLinkMiddleware
from directlink_service import get_module
from templates import template_name

logger = logging.getLogger(__name__)

DEFAULT_WELCOME = "Привет! 👋 Спасибо за заявку, рады видеть вас в нашем канале!"


def _render_template(bot_db: dict) -> tuple[str, InlineKeyboardMarkup | None]:
    """Что бот показывает юзеру после успешного входа — по шаблону."""
    template = bot_db.get("template") or "standard"

    if template == "standard":
        # «Стандартный шаблон (Для мини-апп)» — кнопка с мини-аппом.
        username = (bot_db.get("username") or "").lstrip("@")
        startapp = f"https://t.me/{username}?startapp=app" if username else None
        kb = None
        if startapp:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Открыть приложение", url=startapp)]
                ]
            )
        return ("Добро пожаловать! Откройте приложение кнопкой ниже 👇", kb)

    if template == "welcome":
        return (bot_db.get("welcome_message") or DEFAULT_WELCOME, None)

    return ("Доступ открыт ✅", None)


def build_router() -> Router:
    router = Router()

    # ----- заявки в канал: пишем человеку первым -----
    @router.chat_join_request()
    async def on_join_request(event: ChatJoinRequest) -> None:
        bot_db = get_bot_by_tg_id(event.bot.id)
        if not bot_db:
            return
        welcome = bot_db.get("welcome_message") or DEFAULT_WELCOME
        # Бот пишет человеку первым.
        try:
            await event.bot.send_message(event.from_user.id, welcome)
        except Exception as e:  # юзер мог не нажать /start у бота
            logger.info("can't DM %s: %s", event.from_user.id, e)
        # Авто-приём заявки, если включён.
        if bot_db.get("auto_approve"):
            try:
                await event.approve()
            except Exception as e:
                logger.warning("approve failed: %s", e)

    # ----- /start с аргументом (deep-link) -----
    @router.message(CommandStart(deep_link=True))
    async def start_with_arg(message: Message, command: CommandObject) -> None:
        bot_db = get_bot_by_tg_id(message.bot.id)
        if not bot_db:
            return
        # Если включена защита — проверяем секрет.
        if bot_db.get("guard_enabled"):
            if command.args != bot_db.get("user_secret"):
                logger.info("bad secret from %s", message.from_user.id)
                return
        await _handle_access(message, bot_db)

    # ----- голый /start -----
    @router.message(CommandStart())
    async def start_plain(message: Message) -> None:
        bot_db = get_bot_by_tg_id(message.bot.id)
        if not bot_db:
            return
        # При включённой защите голый /start игнорируется (антибан).
        if bot_db.get("guard_enabled"):
            return
        await _handle_access(message, bot_db)

    return router


async def _handle_access(message: Message, bot_db: dict) -> None:
    """Успешный вход: учитываем запуск и отвечаем по шаблону."""
    record_launch(
        bot_tg_id=message.bot.id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        geo=message.from_user.language_code,  # лучшее доступное приближение гео
    )
    text, kb = _render_template(bot_db)
    await message.answer(text, reply_markup=kb)


def build_dispatcher() -> Dispatcher:
    """Создаёт диспетчер с middleware «Прямой ссылки» и хендлерами."""
    dp = Dispatcher()
    dp.message.middleware(DirectLinkMiddleware(get_module()))
    dp.include_router(build_router())
    return dp


def make_bot(token: str) -> Bot:
    return Bot(token=token)


# Совместимость с описанием шаблона в карточке (используется в settings).
__all__ = ["build_dispatcher", "make_bot", "build_router", "template_name"]

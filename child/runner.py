"""
Логика дочернего бота (того, что добавили по токену).

Два режима входа (по флагу «Прямая ссылка»):
  • ВЫКЛ — бот сам ведёт пользователя: на заявку в канал / на /start пишет
    шаблон и даёт web_app-кнопку, открывающую мини-апп прямо из чата.
  • ВКЛ — вход через Main App по startapp-ссылке (настраивается в BotFather);
    middleware глушит /start, бот в диалог не вмешивается.

Ещё умеет:
  • Авто-приём заявок в канал (если включён).
  • Секретный /start (Guard «Защита от бана») — отвечает только на deep-link
    со своим секретом.
  • Учёт запусков для статистики (user_id + гео по языку клиента).

Свежие настройки бота читаются из БД на каждый апдейт по tg_id
(event.bot.id), чтобы изменения из менеджера применялись сразу.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    ChatJoinRequest,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from config import MINIAPP_BASE_URL
from database import get_bot_by_tg_id, record_launch
from direct_link.aiogram_integration import DirectLinkMiddleware
from directlink_service import get_module
from templates import template_name

logger = logging.getLogger(__name__)

DEFAULT_WELCOME = "Привет! 👋 Спасибо за заявку, рады видеть вас в нашем канале!"

# Текст приветствия по умолчанию (заглушка под будущий шаблон).
GREETING_TEXT = (
    "👋 Здравствуйте!\n"
    "Чтобы получить доступ к боту 👇\n\n"
    "❗️ Пожалуйста, подтвердите то, что вы не робот"
)
# Подпись кнопки, открывающей мини-апп (она же «подтверждение»).
OPEN_BUTTON = "Подтвердить ✅"


async def _miniapp_button(bot_id: int) -> InlineKeyboardMarkup | None:
    """Inline-кнопка, открывающая мини-апп прямо из чата (web_app).

    В URL кладём токен доступа, чтобы гейт мини-аппа пустил пользователя
    без startapp-ссылки (режим «Прямая ссылка выключена»). Если публичный
    адрес веба не задан — кнопку не показываем.
    """
    if not MINIAPP_BASE_URL:
        return None
    state = await get_module().get_or_init(bot_id)
    url = f"{MINIAPP_BASE_URL}/app/{bot_id}?t={state['startapp_token']}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=OPEN_BUTTON, web_app=WebAppInfo(url=url))]
        ]
    )


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

    # ----- заявка в канал -----
    @router.chat_join_request()
    async def on_join_request(event: ChatJoinRequest) -> None:
        bot_db = get_bot_by_tg_id(event.bot.id)
        if not bot_db:
            return

        # «Прямая ссылка» включена → вход идёт через Main App по startapp-
        # ссылке, бот в диалоге не вмешивается и заявку не трогает.
        if await get_module().is_enabled_for(event.bot.id):
            return

        # «Прямая ссылка» выключена → бот пишет первым и ведёт в мини-апп.
        # Заявку НЕ принимаем: пока она «висит», Telegram разрешает боту
        # писать заявителю (через user_chat_id, ~5 минут). Одобрим позже —
        # после прохождения капчи/мини-аппа.
        record_launch(
            bot_tg_id=event.bot.id,
            user_id=event.from_user.id,
            username=event.from_user.username,
            geo=event.from_user.language_code,
        )
        text = bot_db.get("welcome_message") or GREETING_TEXT
        kb = await _miniapp_button(event.bot.id)
        # user_chat_id работает даже если юзер не нажимал /start у бота.
        target = getattr(event, "user_chat_id", None) or event.from_user.id
        try:
            await event.bot.send_message(target, text, reply_markup=kb)
        except Exception as e:
            logger.info("can't DM %s: %s", target, e)

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
    """Вход по /start: учитываем запуск, пишем шаблон и ведём в мини-апп."""
    record_launch(
        bot_tg_id=message.bot.id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        geo=message.from_user.language_code,  # лучшее доступное приближение гео
    )
    text = bot_db.get("welcome_message") or GREETING_TEXT
    kb = await _miniapp_button(message.bot.id)
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

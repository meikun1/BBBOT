"""
Связка модуля «Прямая ссылка» (direct_link/) с нашей SQLite-базой.

Здесь:
  • SqliteDirectLinkStorage — реализация async-протокола DirectLinkStorage
    поверх синхронной базы (database.py).
  • get_module() — собранный DirectLinkModule (singleton), который зовут
    и handler'ы менеджера, и middleware дочерних ботов, и веб-приложение.

Важно: direct_link оперирует telegram-id бота (event.bot.id). Поэтому
здесь bot_id == tg_id, а не внутренний id из таблицы bots.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from config import (
    DIRECT_LINK_MANUAL_URL,
    DIRECT_LINK_REDIRECT_URL,
    DIRECT_LINK_SESSION_SECRET,
)
from database import dl_get, dl_init, dl_rotate, dl_set_enabled, get_bot_by_tg_id
from direct_link import DirectLinkConfig, DirectLinkModule
from direct_link.storage import BotState


class DBDirectLinkStorage:
    """Хранилище состояния «Прямой ссылки» (таблица direct_link_bots)."""

    async def get(self, bot_id: int) -> BotState | None:
        return dl_get(bot_id)  # type: ignore[return-value]

    async def init(self, bot_id: int, startapp_token: str) -> BotState:
        return dl_init(bot_id, startapp_token)  # type: ignore[return-value]

    async def set_enabled(self, bot_id: int, enabled: bool) -> None:
        dl_set_enabled(bot_id, enabled)

    async def rotate_token(self, bot_id: int, new_token: str) -> BotState:
        return dl_rotate(bot_id, new_token)  # type: ignore[return-value]


# ---------- async-колбэки от «хоста» (нашего менеджера) ----------


async def _get_bot_token(bot_id: int) -> str | None:
    bot = get_bot_by_tg_id(bot_id)
    return bot["token"] if bot else None


async def _get_bot_username(bot_id: int) -> str | None:
    bot = get_bot_by_tg_id(bot_id)
    if not bot or not bot["username"]:
        return None
    return bot["username"].lstrip("@")


async def _verify_admin(request: Request, bot_id: int) -> None:
    """
    Авторизация админских ручек веб-API.

    В тесте админка управляется из самого бота-менеджера, а не через веб,
    поэтому веб-ручки закрыты простым секретом из заголовка. В проде
    замените на нормальную сессию владельца.
    """
    header = request.headers.get("X-Admin-Secret", "")
    if header != DIRECT_LINK_SESSION_SECRET:
        raise HTTPException(403, "forbidden")


_module: DirectLinkModule | None = None


def get_module() -> DirectLinkModule:
    global _module
    if _module is None:
        _module = DirectLinkModule(
            DirectLinkConfig(
                session_secret=DIRECT_LINK_SESSION_SECRET,
                redirect_url=DIRECT_LINK_REDIRECT_URL,
                manual_url=DIRECT_LINK_MANUAL_URL,
            ),
            storage=DBDirectLinkStorage(),
            get_bot_token=_get_bot_token,
            get_bot_username=_get_bot_username,
            verify_admin=_verify_admin,
        )
    return _module

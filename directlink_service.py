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

import time

from fastapi import HTTPException, Request

from config import (
    DIRECT_LINK_MANUAL_URL,
    DIRECT_LINK_REDIRECT_URL,
    DIRECT_LINK_SESSION_SECRET,
)
from database import _conn, _lock, get_bot_by_tg_id
from direct_link import DirectLinkConfig, DirectLinkModule
from direct_link.storage import BotState


class SqliteDirectLinkStorage:
    """Хранилище состояния «Прямой ссылки» в таблице direct_link_bots."""

    async def get(self, bot_id: int) -> BotState | None:
        with _lock:
            row = _conn.execute(
                "SELECT enabled, startapp_token, token_version "
                "FROM direct_link_bots WHERE bot_id=?",
                (bot_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "enabled": bool(row["enabled"]),
            "startapp_token": row["startapp_token"],
            "token_version": row["token_version"],
        }

    async def init(self, bot_id: int, startapp_token: str) -> BotState:
        now = int(time.time())
        with _lock:
            _conn.execute(
                "INSERT INTO direct_link_bots(bot_id, enabled, startapp_token, "
                "token_version, created_at, updated_at) VALUES(?,0,?,1,?,?) "
                "ON CONFLICT(bot_id) DO NOTHING",
                (bot_id, startapp_token, now, now),
            )
            _conn.commit()
        state = await self.get(bot_id)
        assert state is not None
        return state

    async def set_enabled(self, bot_id: int, enabled: bool) -> None:
        with _lock:
            _conn.execute(
                "UPDATE direct_link_bots SET enabled=?, updated_at=? WHERE bot_id=?",
                (1 if enabled else 0, int(time.time()), bot_id),
            )
            _conn.commit()

    async def rotate_token(self, bot_id: int, new_token: str) -> BotState:
        with _lock:
            _conn.execute(
                "UPDATE direct_link_bots SET startapp_token=?, "
                "token_version=token_version+1, updated_at=? WHERE bot_id=?",
                (new_token, int(time.time()), bot_id),
            )
            _conn.commit()
        state = await self.get(bot_id)
        assert state is not None
        return state


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
            storage=SqliteDirectLinkStorage(),
            get_bot_token=_get_bot_token,
            get_bot_username=_get_bot_username,
            verify_admin=_verify_admin,
        )
    return _module

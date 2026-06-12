"""
Интерфейс хранилища для модуля 'Прямая ссылка'.

Все методы async — рассчитано на работу с asyncpg / SQLAlchemy async /
motor и т.п.

Модель: одна строка на бот.

    direct_link_bots
    ----------------
    bot_id          PRIMARY KEY
    enabled         BOOLEAN
    startapp_token  TEXT          — генерится 1 раз
    token_version   INTEGER       — растёт при ротации
    created_at      INTEGER
    updated_at      INTEGER
"""

from __future__ import annotations

from typing import Protocol, TypedDict


class BotState(TypedDict):
    enabled: bool
    startapp_token: str
    token_version: int


class DirectLinkStorage(Protocol):
    async def get(self, bot_id: int) -> BotState | None:
        """Состояние модуля для бота. None — ещё не инициализирован."""
        ...

    async def init(self, bot_id: int, startapp_token: str) -> BotState:
        """
        Создать запись (idempotent). enabled=False, token_version=1.
        Если запись уже есть — вернуть существующую, НЕ перезаписывать токен.
        """
        ...

    async def set_enabled(self, bot_id: int, enabled: bool) -> None: ...

    async def rotate_token(self, bot_id: int, new_token: str) -> BotState:
        """Перевыпустить startapp_token, token_version += 1."""
        ...

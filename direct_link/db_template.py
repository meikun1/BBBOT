"""
=== ЗАГЛУШКА ПОД БД ХОСТА (async) ===

Шаблон под asyncpg / SQLAlchemy async / motor. Замени тело методов
на работу со своей БД.

SQL для PostgreSQL:

    CREATE TABLE direct_link_bots (
        bot_id          BIGINT PRIMARY KEY,
        enabled         BOOLEAN NOT NULL DEFAULT FALSE,
        startapp_token  TEXT    NOT NULL,
        token_version   INTEGER NOT NULL DEFAULT 1,
        created_at      BIGINT  NOT NULL,
        updated_at      BIGINT  NOT NULL
    );
"""

from __future__ import annotations

from .storage import BotState


class HostDBStorage:
    """
    TODO: реализуй под свою БД. В __init__ прокинь пул/сессию.
    Пример ниже — для asyncpg.Pool. Адаптируй под свой стек.
    """

    def __init__(self, db) -> None:
        # TODO: db = твой пул / sessionmaker / motor-клиент
        self.db = db

    async def get(self, bot_id: int) -> BotState | None:
        # TODO:
        # row = await self.db.fetchrow(
        #     "SELECT enabled, startapp_token, token_version"
        #     "   FROM direct_link_bots WHERE bot_id = $1",
        #     bot_id,
        # )
        # if row is None: return None
        # return {"enabled": row["enabled"],
        #         "startapp_token": row["startapp_token"],
        #         "token_version": row["token_version"]}
        raise NotImplementedError

    async def init(self, bot_id: int, startapp_token: str) -> BotState:
        # TODO:
        # import time; now = int(time.time())
        # await self.db.execute(
        #     "INSERT INTO direct_link_bots(bot_id, enabled, startapp_token,"
        #     "                              token_version, created_at, updated_at)"
        #     " VALUES ($1, FALSE, $2, 1, $3, $3)"
        #     " ON CONFLICT (bot_id) DO NOTHING",
        #     bot_id, startapp_token, now,
        # )
        # return await self.get(bot_id)
        raise NotImplementedError

    async def set_enabled(self, bot_id: int, enabled: bool) -> None:
        # TODO:
        # import time
        # await self.db.execute(
        #     "UPDATE direct_link_bots SET enabled=$1, updated_at=$2"
        #     " WHERE bot_id=$3",
        #     enabled, int(time.time()), bot_id,
        # )
        raise NotImplementedError

    async def rotate_token(self, bot_id: int, new_token: str) -> BotState:
        # TODO:
        # import time
        # await self.db.execute(
        #     "UPDATE direct_link_bots"
        #     "   SET startapp_token=$1,"
        #     "       token_version=token_version+1,"
        #     "       updated_at=$2"
        #     " WHERE bot_id=$3",
        #     new_token, int(time.time()), bot_id,
        # )
        # return await self.get(bot_id)
        raise NotImplementedError

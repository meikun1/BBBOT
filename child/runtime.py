"""
Супервизор дочерних ботов.

Менеджер держит один процесс и крутит polling каждого включённого
дочернего бота в отдельной asyncio-задаче. Кнопки «Перезапуск»,
«Создать бота», «Удалить», вкл/выкл дёргают методы этого супервизора.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from child.runner import build_dispatcher, make_bot
from database import get_all_bots, get_bot

logger = logging.getLogger(__name__)


class BotRuntime:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}  # tg_id -> polling task
        self._bots: dict[int, Bot] = {}            # tg_id -> Bot

    async def start_all(self) -> None:
        """Поднять polling для всех включённых ботов при старте менеджера."""
        for bot_db in get_all_bots():
            if bot_db.get("enabled") and bot_db.get("token"):
                await self.start_bot_db(bot_db)

    async def start_bot_db(self, bot_db: dict) -> None:
        token = bot_db.get("token")
        if not token:
            return
        bot = make_bot(token)
        try:
            me = await bot.get_me()
        except Exception as e:
            logger.warning("can't start bot id=%s: %s", bot_db.get("id"), e)
            await bot.session.close()
            return
        tg_id = me.id
        # Уже запущен — перезапускаем чисто.
        await self.stop_bot(tg_id)
        self._bots[tg_id] = bot
        self._tasks[tg_id] = asyncio.create_task(self._poll(bot))
        logger.info("started child bot @%s (id=%s)", me.username, tg_id)

    async def _poll(self, bot: Bot) -> None:
        # Отдельный диспетчер на каждого бота — их можно поллить параллельно.
        dp = build_dispatcher()
        try:
            await dp.start_polling(bot, handle_signals=False)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("polling crashed: %s", e)

    async def stop_bot(self, tg_id: int) -> None:
        task = self._tasks.pop(tg_id, None)
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        bot = self._bots.pop(tg_id, None)
        if bot:
            try:
                await bot.session.close()
            except Exception:
                pass

    async def restart_bot(self, bot_id: int) -> bool:
        """Перезапуск по внутреннему id бота. True — если поднялся."""
        bot_db = get_bot(bot_id)
        if not bot_db:
            return False
        if bot_db.get("tg_id"):
            await self.stop_bot(bot_db["tg_id"])
        await self.start_bot_db(bot_db)
        return True

    def is_running(self, tg_id: int | None) -> bool:
        return bool(tg_id and tg_id in self._tasks)

    async def shutdown(self) -> None:
        for tg_id in list(self._tasks):
            await self.stop_bot(tg_id)


# --- singleton, общий для всех handler'ов менеджера ---
_runtime: BotRuntime | None = None


def get_runtime() -> BotRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BotRuntime()
    return _runtime

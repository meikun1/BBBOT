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
from aiogram.exceptions import TelegramUnauthorizedError

from child.runner import build_dispatcher, make_bot
from database import get_all_bots, get_bot, get_bot_by_tg_id, get_proxy

logger = logging.getLogger(__name__)

# Как часто проверять, что дочерние боты живы (не забанены / токен не отозван).
HEALTH_INTERVAL_SEC = 120


class BotRuntime:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}  # tg_id -> polling task
        self._bots: dict[int, Bot] = {}            # tg_id -> Bot
        self._manager_bot: Bot | None = None       # для уведомлений владельцу
        self._banned: set[int] = set()             # tg_id, по которым уже уведомили
        self._health_task: asyncio.Task | None = None

    def set_manager_bot(self, bot: Bot) -> None:
        """Бот-менеджер, через который шлём владельцу уведомления."""
        self._manager_bot = bot

    async def _notify_owner(self, owner_id: int | None, text: str) -> None:
        if not (self._manager_bot and owner_id):
            return
        try:
            await self._manager_bot.send_message(owner_id, text)
        except Exception as e:
            logger.warning("owner notify failed (%s): %s", owner_id, e)

    async def send_test_ban(self, owner_id: int) -> bool:
        """Отправить владельцу тестовое уведомление (проверка доставки)."""
        await self._notify_owner(
            owner_id,
            "🔔 <b>Тест уведомления.</b> Так будет выглядеть сообщение, если "
            "дочернего бота забанят или отзовут токен:\n\n"
            "⚠️ Бот <b>@your_bot</b> недоступен — возможно, забанен Telegram "
            "или токен отозван. Опрос остановлен.",
        )
        return self._manager_bot is not None

    async def _on_banned(self, tg_id: int) -> None:
        """Бот недоступен (401): уведомляем владельца и останавливаем опрос."""
        if tg_id in self._banned:
            return
        self._banned.add(tg_id)
        bot_db = get_bot_by_tg_id(tg_id)
        await self.stop_bot(tg_id)
        if bot_db:
            uname = bot_db.get("username") or f"id={tg_id}"
            await self._notify_owner(
                bot_db.get("owner_id"),
                f"⚠️ Бот <b>{uname}</b> недоступен — возможно, забанен Telegram "
                "или токен отозван. Опрос остановлен.",
            )
        logger.warning("child bot %s unauthorized — stopped & owner notified", tg_id)

    async def start_all(self) -> None:
        """Поднять polling для всех включённых ботов при старте менеджера."""
        for bot_db in get_all_bots():
            if bot_db.get("enabled") and bot_db.get("token"):
                await self.start_bot_db(bot_db)

    async def start_bot_db(self, bot_db: dict) -> None:
        token = bot_db.get("token")
        if not token:
            return
        proxy_url = None
        pid = bot_db.get("proxy_id")
        if pid:
            p = get_proxy(pid)
            if p:
                proxy_url = p["url"]
        bot = make_bot(token, proxy_url)
        try:
            me = await bot.get_me()
        except TelegramUnauthorizedError:
            # токен невалиден/отозван/бан — уведомляем владельца
            await bot.session.close()
            tg = bot_db.get("tg_id")
            if tg and tg not in self._banned:
                self._banned.add(tg)
                uname = bot_db.get("username") or f"id={tg}"
                await self._notify_owner(
                    bot_db.get("owner_id"),
                    f"⚠️ Бот <b>{uname}</b> не запустился — токен недействителен "
                    "(возможно, забанен или отозван).",
                )
            logger.warning("bot id=%s unauthorized at start", bot_db.get("id"))
            return
        except Exception as e:
            logger.warning("can't start bot id=%s: %s", bot_db.get("id"), e)
            await bot.session.close()
            return
        tg_id = me.id
        # Уже запущен — перезапускаем чисто.
        await self.stop_bot(tg_id)
        self._banned.discard(tg_id)  # снова живой — разрешаем будущие уведомления
        self._bots[tg_id] = bot
        self._tasks[tg_id] = asyncio.create_task(self._poll(bot))
        logger.info("started child bot @%s (id=%s)", me.username, tg_id)

    def start_health(self) -> None:
        """Запустить фоновую проверку здоровья ботов (один раз)."""
        if self._health_task is None or self._health_task.done():
            self._health_task = asyncio.create_task(self._health_loop())

    async def _health_loop(self) -> None:
        while True:
            await asyncio.sleep(HEALTH_INTERVAL_SEC)
            for tg_id, bot in list(self._bots.items()):
                try:
                    await bot.get_me()
                except TelegramUnauthorizedError:
                    await self._on_banned(tg_id)
                except Exception:
                    pass  # сетевые/временные — не считаем баном

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

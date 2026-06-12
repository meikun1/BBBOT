"""
Интеграция с aiogram 3.x.

Подключи DirectLinkMiddleware к диспетчеру — когда модуль 'Прямая ссылка'
для бота включён, апдейт с командой /start будет молча отброшен ещё до
того, как доберётся до твоих хендлеров. Никакого хендлера /start
переписывать не надо.

    from aiogram import Dispatcher
    from direct_link.aiogram_integration import DirectLinkMiddleware

    dp = Dispatcher()
    dp.message.middleware(DirectLinkMiddleware(direct_link))

Если у тебя multi-bot (один диспетчер обрабатывает несколько ботов через
TokenBasedRouter), bot_id берётся из event.bot.id автоматически.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from .module import DirectLinkModule


class DirectLinkMiddleware(BaseMiddleware):
    """
    Перехватывает сообщения /start. Если для бота (по event.bot.id) модуль
    'Прямая ссылка' включён — апдейт игнорируется (handler не вызывается).
    Остальные сообщения проходят как обычно.
    """

    def __init__(self, module: DirectLinkModule) -> None:
        super().__init__()
        self.module = module

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and self._is_start_command(event):
            bot_id = event.bot.id if event.bot else None
            if bot_id and await self.module.is_enabled_for(bot_id):
                return  # глушим /start
        return await handler(event, data)

    @staticmethod
    def _is_start_command(message: Message) -> bool:
        text = (message.text or message.caption or "").strip()
        if not text.startswith("/start"):
            return False
        # Корректно отсекаем /start@SomeBot, /start payload, просто /start
        head = text.split(maxsplit=1)[0]
        command = head.split("@", 1)[0]
        return command == "/start"

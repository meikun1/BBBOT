"""
========================================================================
 МОДУЛЬ: мониторинг здоровья ботов
------------------------------------------------------------------------
 Команда /testban — отправляет владельцу тестовое уведомление о бане,
 чтобы проверить доставку без реального бана. Реальные уведомления шлёт
 BotRuntime (health-loop) при 401 от getMe дочернего бота.
========================================================================
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("testban"))
async def test_ban(message: Message) -> None:
    from child.runtime import get_runtime

    ok = await get_runtime().send_test_ban(message.from_user.id)
    if ok:
        await message.answer("✅ Тестовое уведомление отправлено.")
    else:
        await message.answer(
            "⚠️ Менеджер-бот ещё не инициализирован для уведомлений."
        )

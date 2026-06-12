"""
Конфигурация менеджера ботов.

Все секреты берутся из переменных окружения. Для локального теста
достаточно задать MANAGER_BOT_TOKEN — остальное имеет разумные дефолты.
"""

from __future__ import annotations

import os

# --- токен самого бота-менеджера (из @BotFather) ---
MANAGER_BOT_TOKEN: str = os.getenv("MANAGER_BOT_TOKEN", "")

# --- файл базы данных (SQLite, для теста) ---
DB_PATH: str = os.getenv("BOT_MANAGER_DB", "bot_manager.db")

# --- модуль «Прямая ссылка» ---
# Секрет для подписи кук мини-аппа. Для теста есть дефолт, в проде задайте свой.
DIRECT_LINK_SESSION_SECRET: str = os.getenv(
    "DIRECT_LINK_SESSION_SECRET", "dev-insecure-secret-change-me"
)
# Куда уводим юзера, если он зашёл в мини-апп без правильной startapp-ссылки.
DIRECT_LINK_REDIRECT_URL: str = os.getenv(
    "DIRECT_LINK_REDIRECT_URL",
    "https://t.me/uzmigrant_miniapp_bot?startapp=profile",
)
# Ссылка на мануал «как поставить мини-апп ссылку в @BotFather».
DIRECT_LINK_MANUAL_URL: str = os.getenv(
    "DIRECT_LINK_MANUAL_URL",
    "https://telegra.ph/Ustanovka-ssylki-dlya-mini-app-02-11",
)

# --- веб-сервер мини-аппа (FastAPI) ---
# Запускать ли FastAPI-приложение вместе с менеджером.
RUN_WEB: bool = os.getenv("RUN_WEB", "0") == "1"
WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
# Railway передаёт порт через переменную PORT — берём её в первую очередь.
WEB_PORT: int = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))

# Публичный базовый URL веб-части (HTTPS-домен Railway). Используется,
# чтобы собрать Web App URL для @BotFather: <BASE>/app/<tg_id>.
# Пример: https://bot-manager-production.up.railway.app
MINIAPP_BASE_URL: str = os.getenv("MINIAPP_BASE_URL", "").rstrip("/")

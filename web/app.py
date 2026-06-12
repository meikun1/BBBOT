"""
FastAPI-приложение мини-аппа.

Монтирует роуты модуля «Прямая ссылка»:
  • POST /dl/{bot_id}/auth/start  — проверка initData + start_param
  • GET  /dl/{bot_id}/auth/me     — проверка куки
  • админские /dl/admin/...       — для UI (защищены X-Admin-Secret)

Запускается опционально (RUN_WEB=1). Для боевого мини-аппа приложение
должно быть за HTTPS-доменом, который указан в @BotFather.
"""

from __future__ import annotations

from fastapi import FastAPI

from database import init_db
from directlink_service import get_module


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Bot Manager — Direct Link mini-app")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    get_module().mount(app)
    return app


app = create_app()

"""
FastAPI-приложение мини-аппа.

Отдаёт:
  • GET /app/{bot_id}            — страницу мини-аппа (Telegram WebApp).
    Внутри страница зовёт /dl/{bot_id}/auth/start: правильная startapp-ссылка
    → показывает контент, иначе редиректит на сторонний ресурс.
  • роуты модуля «Прямая ссылка» (/dl/...).

bot_id в URL — это telegram-id дочернего бота (event.bot.id). Именно такой
Web App URL (<BASE>/app/<tg_id>) нужно указать в @BotFather.

Запускается опционально (RUN_WEB=1). Нужен HTTPS-домен (его даёт Railway).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import init_db
from directlink_service import get_module

_MINIAPP_HTML = (Path(__file__).parent / "miniapp.html").read_text(encoding="utf-8")


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Bot Manager — Mini App")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/app/{bot_id}", response_class=HTMLResponse)
    async def mini_app(bot_id: int) -> HTMLResponse:
        page = _MINIAPP_HTML.replace("__BOT_ID__", str(bot_id))
        return HTMLResponse(page)

    get_module().mount(app)
    return app


app = create_app()

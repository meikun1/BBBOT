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

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import get_bot_by_tg_id, get_template, init_db
from directlink_service import get_module

_MINIAPP_HTML = (Path(__file__).parent / "miniapp.html").read_text(encoding="utf-8")


def _miniapp_config(bot_id: int) -> dict:
    """Оформление мини-аппа из выбранного шаблона бота (для страницы)."""
    cfg = {"color": "", "bg": "", "blur": 0, "main": "", "success": ""}
    bot = get_bot_by_tg_id(bot_id)
    if bot and bot.get("template_id"):
        t = get_template(bot["template_id"])
        if t:
            c = t["content"]
            cfg["color"] = c.get("ui_color") or ""
            cfg["bg"] = c.get("bg") or ""
            cfg["blur"] = int(c.get("blur") or 0)
            # под-поля страниц (main_text/success_text), с откатом на старый
            # одиночный ключ страницы (page_main/page_success) для совместимости
            cfg["main"] = c.get("main_text") or c.get("page_main") or ""
            cfg["success"] = c.get("success_text") or c.get("page_success") or ""
    return cfg


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Bot Manager — Mini App")

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/app/{bot_id}", response_class=HTMLResponse)
    async def mini_app(bot_id: int) -> HTMLResponse:
        cfg = _miniapp_config(bot_id)
        # экранируем '<', чтобы JSON не закрыл <script>
        cfg_json = json.dumps(cfg, ensure_ascii=False).replace("<", "\\u003c")
        page = _MINIAPP_HTML.replace("__BOT_ID__", str(bot_id))
        page = page.replace("__CFG__", cfg_json)
        return HTMLResponse(page)

    get_module().mount(app)
    return app


app = create_app()

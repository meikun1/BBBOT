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
from miniapp_template import ALL_DEFAULTS

_MINIAPP_HTML = (Path(__file__).parent / "miniapp.html").read_text(encoding="utf-8")


def _miniapp_config(bot_id: int) -> dict:
    """Оформление и контент главной страницы мини-аппа из шаблона бота.

    Берём поля главной страницы (эмодзи/текст/кнопка) с подстановкой
    дефолтов «Стандартного шаблона», чтобы мини-апп показывал реальный
    контент, а не заглушку, даже если поле в шаблоне не заполняли.
    """
    cfg = {"color": "", "bg": "", "blur": 0, "emoji": "", "text": "", "button": ""}
    content: dict = {}
    bot = get_bot_by_tg_id(bot_id)
    if bot and bot.get("template_id"):
        t = get_template(bot["template_id"])
        if t:
            content = t["content"]

    def _val(key: str) -> str:
        v = content.get(key)
        if v is not None and str(v).strip():
            return v
        return ALL_DEFAULTS.get(key, "")

    color = content.get("ui_color") or ""
    cfg["color"] = "" if color in ("", "default") else color
    cfg["bg"] = content.get("bg") or ""
    cfg["blur"] = int(content.get("blur") or 0)
    cfg["emoji"] = _val("main_emoji")
    cfg["text"] = _val("main_text")
    cfg["button"] = _val("main_button")
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

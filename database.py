"""
========================================================================
 База данных менеджера ботов (SQLite, синхронный слой).
------------------------------------------------------------------------
 Для теста используется один файл SQLite. API синхронный — ровно то,
 что ожидают handler'ы (get_bot, add_bot, update_bot_field и т.д.).
 Когда придёт время — этот модуль можно заменить на async/Postgres,
 сохранив сигнатуры функций.
========================================================================
"""

from __future__ import annotations

import secrets
import sqlite3
import threading
import time
from typing import Any

from config import DB_PATH

# Один разделяемый коннект + блокировка (SQLite в многопоточном опросе ботов).
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_lock = threading.Lock()


def _now() -> int:
    return int(time.time())


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет. Зовётся один раз при старте."""
    with _lock:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY,
                username  TEXT,
                created_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS folders (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id  INTEGER NOT NULL,
                name      TEXT NOT NULL,
                created_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS bots (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id      INTEGER NOT NULL,
                token         TEXT UNIQUE NOT NULL,
                username      TEXT,
                tg_id         INTEGER,
                enabled       INTEGER NOT NULL DEFAULT 1,
                auto_approve  INTEGER NOT NULL DEFAULT 1,
                welcome_message TEXT,
                folder_id     INTEGER,
                template      TEXT NOT NULL DEFAULT 'standard',
                guard_enabled INTEGER NOT NULL DEFAULT 0,
                user_secret   TEXT,
                miniapp_enabled INTEGER NOT NULL DEFAULT 0,
                created_at    INTEGER
            );

            -- запуски бота юзерами (для статистики: кто/откуда, id = гео)
            CREATE TABLE IF NOT EXISTS launches (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_tg_id   INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                geo         TEXT,
                created_at  INTEGER
            );

            -- состояние модуля «Прямая ссылка» (по telegram-id бота)
            CREATE TABLE IF NOT EXISTS direct_link_bots (
                bot_id          INTEGER PRIMARY KEY,
                enabled         INTEGER NOT NULL DEFAULT 0,
                startapp_token  TEXT NOT NULL,
                token_version   INTEGER NOT NULL DEFAULT 1,
                created_at      INTEGER NOT NULL,
                updated_at      INTEGER NOT NULL
            );
            """
        )
        _conn.commit()


# ----------------------------------------------------------------- users
def add_user(user_id: int, username: str | None) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO users(id, username, created_at) VALUES(?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET username=excluded.username",
            (user_id, username, _now()),
        )
        _conn.commit()


# --------------------------------------------------------------- folders
def add_folder(owner_id: int, name: str) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO folders(owner_id, name, created_at) VALUES(?,?,?)",
            (owner_id, name, _now()),
        )
        _conn.commit()
        return int(cur.lastrowid)


def get_folders(owner_id: int) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM folders WHERE owner_id=? ORDER BY id", (owner_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_folder(folder_id: int) -> dict | None:
    with _lock:
        row = _conn.execute(
            "SELECT * FROM folders WHERE id=?", (folder_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_folder(folder_id: int) -> None:
    with _lock:
        _conn.execute(
            "UPDATE bots SET folder_id=NULL WHERE folder_id=?", (folder_id,)
        )
        _conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        _conn.commit()


# ------------------------------------------------------------------ bots
def token_exists(token: str) -> bool:
    with _lock:
        row = _conn.execute(
            "SELECT 1 FROM bots WHERE token=?", (token,)
        ).fetchone()
    return row is not None


def add_bot(
    owner_id: int,
    token: str,
    username: str,
    tg_id: int | None = None,
) -> int:
    """Добавляет бота. Сразу генерит секрет для «ссылки для юзера» (Guard)."""
    user_secret = secrets.token_urlsafe(6)
    with _lock:
        cur = _conn.execute(
            "INSERT INTO bots(owner_id, token, username, tg_id, user_secret, "
            "created_at) VALUES(?,?,?,?,?,?)",
            (owner_id, token, username, tg_id, user_secret, _now()),
        )
        _conn.commit()
        return int(cur.lastrowid)


def get_bot(bot_id: int) -> dict | None:
    with _lock:
        row = _conn.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
    return dict(row) if row else None


def get_bot_by_tg_id(tg_id: int) -> dict | None:
    with _lock:
        row = _conn.execute(
            "SELECT * FROM bots WHERE tg_id=?", (tg_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_bots(owner_id: int, folder_id: int | None = None) -> list[dict]:
    with _lock:
        if folder_id is None:
            rows = _conn.execute(
                "SELECT * FROM bots WHERE owner_id=? ORDER BY id", (owner_id,)
            ).fetchall()
        else:
            rows = _conn.execute(
                "SELECT * FROM bots WHERE owner_id=? AND folder_id=? ORDER BY id",
                (owner_id, folder_id),
            ).fetchall()
    return [dict(r) for r in rows]


def get_all_bots() -> list[dict]:
    """Все боты — нужно рантайму для запуска polling'а."""
    with _lock:
        rows = _conn.execute("SELECT * FROM bots ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def update_bot_field(bot_id: int, field: str, value: Any) -> None:
    allowed = {
        "enabled",
        "auto_approve",
        "welcome_message",
        "folder_id",
        "template",
        "guard_enabled",
        "user_secret",
        "username",
        "miniapp_enabled",
    }
    if field not in allowed:
        raise ValueError(f"Поле {field!r} нельзя обновлять")
    with _lock:
        _conn.execute(f"UPDATE bots SET {field}=? WHERE id=?", (value, bot_id))
        _conn.commit()


def delete_bot(bot_id: int) -> None:
    with _lock:
        row = _conn.execute(
            "SELECT tg_id FROM bots WHERE id=?", (bot_id,)
        ).fetchone()
        _conn.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        if row and row["tg_id"] is not None:
            _conn.execute(
                "DELETE FROM direct_link_bots WHERE bot_id=?", (row["tg_id"],)
            )
        _conn.commit()


# -------------------------------------------------------------- launches
def record_launch(
    bot_tg_id: int, user_id: int, username: str | None, geo: str | None
) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO launches(bot_tg_id, user_id, username, geo, created_at) "
            "VALUES(?,?,?,?,?)",
            (bot_tg_id, user_id, username, geo, _now()),
        )
        _conn.commit()


def get_launch_stats(bot_tg_id: int) -> dict:
    """Сводка по запускам бота: всего, уникальных, разбивка по гео."""
    with _lock:
        total = _conn.execute(
            "SELECT COUNT(*) c FROM launches WHERE bot_tg_id=?", (bot_tg_id,)
        ).fetchone()["c"]
        unique = _conn.execute(
            "SELECT COUNT(DISTINCT user_id) c FROM launches WHERE bot_tg_id=?",
            (bot_tg_id,),
        ).fetchone()["c"]
        geo_rows = _conn.execute(
            "SELECT COALESCE(geo,'—') geo, COUNT(*) c FROM launches "
            "WHERE bot_tg_id=? GROUP BY geo ORDER BY c DESC LIMIT 10",
            (bot_tg_id,),
        ).fetchall()
    return {
        "total": total,
        "unique": unique,
        "by_geo": [(r["geo"], r["c"]) for r in geo_rows],
    }


def get_recent_launches(bot_tg_id: int, limit: int = 15) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT user_id, username, geo, created_at FROM launches "
            "WHERE bot_tg_id=? ORDER BY id DESC LIMIT ?",
            (bot_tg_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def direct_link_enabled(bot_tg_id: int | None) -> bool:
    """Статус модуля «Прямая ссылка» (мини-апп) по telegram-id бота."""
    if not bot_tg_id:
        return False
    with _lock:
        row = _conn.execute(
            "SELECT enabled FROM direct_link_bots WHERE bot_id=?", (bot_tg_id,)
        ).fetchone()
    return bool(row and row["enabled"])


def get_bot_user_ids(bot_tg_id: int) -> list[int]:
    """Уникальные user_id, которые запускали бота — для рассылки."""
    with _lock:
        rows = _conn.execute(
            "SELECT DISTINCT user_id FROM launches WHERE bot_tg_id=?",
            (bot_tg_id,),
        ).fetchall()
    return [r["user_id"] for r in rows]

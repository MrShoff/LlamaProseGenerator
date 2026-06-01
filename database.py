from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent / "prose_generator.db"

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS scene_status (
    scene_key        TEXT PRIMARY KEY,
    status           TEXT NOT NULL,
    active_variant   TEXT,
    last_updated_by  TEXT,
    last_updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS comments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_key        TEXT NOT NULL,
    paragraph_index  INTEGER,
    comment_type     TEXT NOT NULL,
    username         TEXT NOT NULL,
    content          TEXT NOT NULL,
    resolved         INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS edits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_key        TEXT NOT NULL,
    paragraph_index  INTEGER NOT NULL,
    username         TEXT NOT NULL,
    original_text    TEXT NOT NULL,
    edited_text      TEXT NOT NULL,
    edited_at        TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_comments_scene     ON comments(scene_key);
CREATE INDEX IF NOT EXISTS idx_comments_paragraph ON comments(scene_key, paragraph_index);
CREATE INDEX IF NOT EXISTS idx_edits_scene        ON edits(scene_key);
CREATE INDEX IF NOT EXISTS idx_edits_paragraph    ON edits(scene_key, paragraph_index);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


# ---------------------------------------------------------------------------
# Scene status
# ---------------------------------------------------------------------------

def get_scene_status(scene_key: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM scene_status WHERE scene_key = ?", (scene_key,)
        ).fetchone()
        return dict(row) if row else None


def set_scene_status(
    scene_key: str,
    status: str,
    username: str,
    active_variant: str | None = None,
) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO scene_status
                (scene_key, status, active_variant, last_updated_by, last_updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(scene_key) DO UPDATE SET
                status          = excluded.status,
                active_variant  = excluded.active_variant,
                last_updated_by = excluded.last_updated_by,
                last_updated_at = excluded.last_updated_at
            """,
            (scene_key, status, active_variant, username),
        )


def get_all_scene_statuses() -> dict[str, dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM scene_status").fetchall()
        return {row["scene_key"]: dict(row) for row in rows}


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def add_comment(
    scene_key: str,
    username: str,
    content: str,
    comment_type: str,
    paragraph_index: int | None = None,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO comments
                (scene_key, paragraph_index, comment_type, username, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scene_key, paragraph_index, comment_type, username, content),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_comments(
    scene_key: str,
    paragraph_index: int | None = None,
    include_resolved: bool = False,
) -> list[dict[str, Any]]:
    with _conn() as conn:
        query = "SELECT * FROM comments WHERE scene_key = ?"
        params: list[Any] = [scene_key]
        if paragraph_index is not None:
            query += " AND paragraph_index = ?"
            params.append(paragraph_index)
        if not include_resolved:
            query += " AND resolved = 0"
        query += " ORDER BY created_at ASC, id ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def resolve_comment(comment_id: int) -> None:
    with _conn() as conn:
        conn.execute("UPDATE comments SET resolved = 1 WHERE id = ?", (comment_id,))


# ---------------------------------------------------------------------------
# Edits
# ---------------------------------------------------------------------------

def add_edit(
    scene_key: str,
    paragraph_index: int,
    username: str,
    original_text: str,
    edited_text: str,
) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO edits
                (scene_key, paragraph_index, username, original_text, edited_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scene_key, paragraph_index, username, original_text, edited_text),
        )


def get_edit_history(
    scene_key: str,
    paragraph_index: int | None = None,
) -> list[dict[str, Any]]:
    with _conn() as conn:
        if paragraph_index is not None:
            rows = conn.execute(
                "SELECT * FROM edits WHERE scene_key = ? AND paragraph_index = ? ORDER BY edited_at DESC, id DESC",
                (scene_key, paragraph_index),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM edits WHERE scene_key = ? ORDER BY edited_at DESC, id DESC",
                (scene_key,),
            ).fetchall()
        return [dict(r) for r in rows]

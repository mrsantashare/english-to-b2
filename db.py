from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "english_to_b2.db"
SCHEMA_PATH = ROOT / "schema.sql"

CATEGORIES = (
    "vocabulary",
    "phrase",
    "idiom",
    "grammar",
    "pronunciation",
    "other",
)
CEFR_LEVELS = ("A1", "A2", "B1", "B2")


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def list_entries(
    *,
    q: str = "",
    category: str = "",
    cefr_level: str = "",
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM knowledge WHERE 1=1"
    params: list[Any] = []

    if q:
        sql += " AND (title LIKE ? OR meaning LIKE ? OR example LIKE ? OR notes LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like])
    if category:
        sql += " AND category = ?"
        params.append(category)
    if cefr_level:
        sql += " AND cefr_level = ?"
        params.append(cefr_level)

    sql += " ORDER BY datetime(created_at) DESC, id DESC"

    with get_connection() as conn:
        return list(conn.execute(sql, params))


def get_entry(entry_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM knowledge WHERE id = ?",
            (entry_id,),
        ).fetchone()


def add_entry(
    *,
    title: str,
    meaning: str,
    example: str = "",
    notes: str = "",
    category: str = "vocabulary",
    cefr_level: str = "B1",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO knowledge (title, meaning, example, notes, category, cefr_level)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, meaning, example, notes, category, cefr_level),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_entry(
    entry_id: int,
    *,
    title: str,
    meaning: str,
    example: str = "",
    notes: str = "",
    category: str = "vocabulary",
    cefr_level: str = "B1",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE knowledge
            SET title = ?, meaning = ?, example = ?, notes = ?,
                category = ?, cefr_level = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (title, meaning, example, notes, category, cefr_level, entry_id),
        )
        conn.commit()


def delete_entry(entry_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
        conn.commit()


def progress_stats() -> dict[str, Any]:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM knowledge").fetchone()["c"]
        by_level = {
            row["cefr_level"]: row["c"]
            for row in conn.execute(
                """
                SELECT cefr_level, COUNT(*) AS c
                FROM knowledge
                GROUP BY cefr_level
                """
            )
        }
        by_category = {
            row["category"]: row["c"]
            for row in conn.execute(
                """
                SELECT category, COUNT(*) AS c
                FROM knowledge
                GROUP BY category
                """
            )
        }

    counts = {level: by_level.get(level, 0) for level in CEFR_LEVELS}
    b2_ready = counts["B2"]
    return {
        "total": total,
        "by_level": counts,
        "by_category": by_category,
        "b2_count": b2_ready,
    }

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "english_to_b2.db"
SCHEMA_PATH = ROOT / "schema.sql"

CEFR_LEVELS = ("A1", "A2", "B1", "B2")

# Each tab key maps to one SQLite table and its primary display fields.
TYPES: dict[str, dict[str, Any]] = {
    "new_words": {
        "table": "new_words",
        "label": "New words",
        "singular": "new word",
        "title_field": "word",
        "body_field": "meaning",
        "fields": ("word", "meaning", "example", "notes", "cefr_level"),
        "required": ("word", "meaning"),
    },
    "verb_phrases": {
        "table": "verb_phrases",
        "label": "Verb phrases",
        "singular": "verb phrase",
        "title_field": "phrase",
        "body_field": "meaning",
        "fields": ("phrase", "meaning", "example", "notes", "cefr_level"),
        "required": ("phrase", "meaning"),
    },
    "sentence_structures": {
        "table": "sentence_structures",
        "label": "Sentence structure",
        "singular": "sentence structure",
        "title_field": "pattern",
        "body_field": "explanation",
        "fields": ("pattern", "explanation", "example", "notes", "cefr_level"),
        "required": ("pattern", "explanation"),
    },
    "dialogs": {
        "table": "dialogs",
        "label": "Dialog",
        "singular": "dialog",
        "title_field": "title",
        "body_field": "content",
        "fields": ("title", "content", "notes", "cefr_level"),
        "required": ("title", "content"),
    },
    "paragraphs": {
        "table": "paragraphs",
        "label": "Paragraph",
        "singular": "paragraph",
        "title_field": "title",
        "body_field": "content",
        "fields": ("title", "content", "notes", "cefr_level"),
        "required": ("title", "content"),
    },
}

TYPE_ORDER = tuple(TYPES.keys())
DEFAULT_TYPE = "new_words"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def clear_all_data() -> None:
    """Wipe every learning table (keeps schema)."""
    with get_connection() as conn:
        for meta in TYPES.values():
            conn.execute(f"DELETE FROM {meta['table']}")
        conn.commit()


def ensure_type(type_key: str) -> str:
    if type_key in TYPES:
        return type_key
    return DEFAULT_TYPE


def list_entries(type_key: str, *, q: str = "", cefr_level: str = "") -> list[sqlite3.Row]:
    type_key = ensure_type(type_key)
    meta = TYPES[type_key]
    table = meta["table"]
    title_field = meta["title_field"]
    body_field = meta["body_field"]

    sql = f"SELECT * FROM {table} WHERE 1=1"
    params: list[Any] = []

    if q:
        like = f"%{q}%"
        searchable = [title_field, body_field, "notes"]
        if "example" in meta["fields"]:
            searchable.append("example")
        clauses = " OR ".join(f"{col} LIKE ?" for col in searchable)
        sql += f" AND ({clauses})"
        params.extend([like] * len(searchable))

    if cefr_level:
        sql += " AND cefr_level = ?"
        params.append(cefr_level)

    sql += " ORDER BY datetime(created_at) DESC, id DESC"

    with get_connection() as conn:
        return list(conn.execute(sql, params))


def get_entry(type_key: str, entry_id: int) -> sqlite3.Row | None:
    type_key = ensure_type(type_key)
    table = TYPES[type_key]["table"]
    with get_connection() as conn:
        return conn.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (entry_id,),
        ).fetchone()


def _normalize_payload(type_key: str, data: dict[str, Any]) -> dict[str, Any]:
    meta = TYPES[type_key]
    payload: dict[str, Any] = {}
    for field in meta["fields"]:
        value = data.get(field, "")
        if value is None:
            value = ""
        if isinstance(value, str):
            value = value.strip()
        payload[field] = value

    if payload.get("cefr_level") not in CEFR_LEVELS:
        payload["cefr_level"] = "B1"
    return payload


def add_entry(type_key: str, **data: Any) -> int:
    type_key = ensure_type(type_key)
    meta = TYPES[type_key]
    payload = _normalize_payload(type_key, data)
    fields = meta["fields"]
    placeholders = ", ".join("?" for _ in fields)
    columns = ", ".join(fields)

    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO {meta['table']} ({columns}) VALUES ({placeholders})",
            tuple(payload[f] for f in fields),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_entry(type_key: str, entry_id: int, **data: Any) -> None:
    type_key = ensure_type(type_key)
    meta = TYPES[type_key]
    payload = _normalize_payload(type_key, data)
    fields = meta["fields"]
    assignments = ", ".join(f"{f} = ?" for f in fields)

    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE {meta['table']}
            SET {assignments},
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            tuple(payload[f] for f in fields) + (entry_id,),
        )
        conn.commit()


def delete_entry(type_key: str, entry_id: int) -> None:
    type_key = ensure_type(type_key)
    table = TYPES[type_key]["table"]
    with get_connection() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (entry_id,))
        conn.commit()


def progress_stats() -> dict[str, Any]:
    counts: dict[str, int] = {}
    total = 0
    by_level = {level: 0 for level in CEFR_LEVELS}

    with get_connection() as conn:
        for key, meta in TYPES.items():
            n = conn.execute(f"SELECT COUNT(*) AS c FROM {meta['table']}").fetchone()["c"]
            counts[key] = n
            total += n
            for row in conn.execute(
                f"SELECT cefr_level, COUNT(*) AS c FROM {meta['table']} GROUP BY cefr_level"
            ):
                level = row["cefr_level"]
                if level in by_level:
                    by_level[level] += row["c"]

    return {
        "total": total,
        "by_type": counts,
        "by_level": by_level,
        "b2_count": by_level["B2"],
    }


def empty_form(type_key: str) -> dict[str, str]:
    type_key = ensure_type(type_key)
    return {field: "" for field in TYPES[type_key]["fields"]} | {"cefr_level": "B1"}

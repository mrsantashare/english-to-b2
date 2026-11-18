from __future__ import annotations

import random
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "english_to_b2.db"
SCHEMA_PATH = ROOT / "schema.sql"

CEFR_LEVELS = ("A1", "A2", "B1", "B2")
DEFAULT_COURSE_LEVEL = 13
DEFAULT_UNIT = 50
PRACTICE_TYPES = ("new_words", "verb_phrases", "sentence_structures")

# Each tab key maps to one SQLite table and its primary display fields.
TYPES: dict[str, dict[str, Any]] = {
    "new_words": {
        "table": "new_words",
        "label": "New words",
        "singular": "new word",
        "title_field": "word",
        "body_field": "meaning",
        "fields": ("word", "meaning", "example", "notes", "cefr_level", "level", "unit"),
        "required": ("word", "meaning"),
        "has_practice": True,
    },
    "verb_phrases": {
        "table": "verb_phrases",
        "label": "Verb phrases",
        "singular": "verb phrase",
        "title_field": "phrase",
        "body_field": "meaning",
        "fields": ("phrase", "meaning", "example", "notes", "cefr_level", "level", "unit"),
        "required": ("phrase", "meaning"),
        "has_practice": True,
    },
    "sentence_structures": {
        "table": "sentence_structures",
        "label": "Sentence structure",
        "singular": "sentence structure",
        "title_field": "pattern",
        "body_field": "explanation",
        "fields": ("pattern", "explanation", "example", "notes", "cefr_level", "level", "unit"),
        "required": ("pattern", "explanation"),
        "has_practice": True,
    },
    "dialogs": {
        "table": "dialogs",
        "label": "Dialog",
        "singular": "dialog",
        "title_field": "title",
        "body_field": "content",
        "fields": ("title", "content", "notes", "cefr_level", "level", "unit"),
        "required": ("title", "content"),
        "has_practice": False,
    },
    "paragraphs": {
        "table": "paragraphs",
        "label": "Paragraph",
        "singular": "paragraph",
        "title_field": "title",
        "body_field": "content",
        "fields": ("title", "content", "notes", "cefr_level", "level", "unit"),
        "required": ("title", "content"),
        "has_practice": False,
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


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add level / unit / practice_count to existing DBs created before those columns."""
    for key, meta in TYPES.items():
        table = meta["table"]
        cols = _table_columns(conn, table)
        if not cols:
            continue
        if "level" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN level INTEGER NOT NULL DEFAULT {DEFAULT_COURSE_LEVEL}"
            )
        if "unit" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN unit INTEGER NOT NULL DEFAULT {DEFAULT_UNIT}"
            )
        if meta.get("has_practice") and "practice_count" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN practice_count INTEGER NOT NULL DEFAULT 0"
            )
        # Ensure existing rows have a concrete course level and unit.
        conn.execute(
            f"UPDATE {table} SET level = ? WHERE level IS NULL OR level = 0",
            (DEFAULT_COURSE_LEVEL,),
        )
        conn.execute(
            f"UPDATE {table} SET unit = ? WHERE unit IS NULL OR unit = 0",
            (DEFAULT_UNIT,),
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_level ON {table}(level)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_unit ON {table}(unit)"
        )


def init_db() -> None:
    with get_connection() as conn:
        # Create base tables/indexes first, then migrate older DBs
        # (e.g. add unit) before any code assumes those columns exist.
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate_schema(conn)
        conn.commit()


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


def parse_level(value: Any, default: int = DEFAULT_COURSE_LEVEL) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return default
    return level if level > 0 else default


def parse_unit(value: Any, default: int = DEFAULT_UNIT) -> int:
    try:
        unit = int(value)
    except (TypeError, ValueError):
        return default
    return unit if unit > 0 else default


def list_entries(
    type_key: str,
    *,
    q: str = "",
    cefr_level: str = "",
    level: str | int | None = "",
    unit: str | int | None = "",
) -> list[sqlite3.Row]:
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

    if level not in ("", None):
        sql += " AND level = ?"
        params.append(parse_level(level))

    if unit not in ("", None):
        sql += " AND unit = ?"
        params.append(parse_unit(unit))

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


def distinct_levels() -> list[int]:
    levels: set[int] = set()
    with get_connection() as conn:
        for meta in TYPES.values():
            for row in conn.execute(f"SELECT DISTINCT level FROM {meta['table']}"):
                if row["level"] is not None:
                    levels.add(int(row["level"]))
    return sorted(levels)


def distinct_units() -> list[int]:
    units: set[int] = set()
    with get_connection() as conn:
        for meta in TYPES.values():
            for row in conn.execute(f"SELECT DISTINCT unit FROM {meta['table']}"):
                if row["unit"] is not None:
                    units.add(int(row["unit"]))
    return sorted(units)


def _normalize_payload(type_key: str, data: dict[str, Any]) -> dict[str, Any]:
    meta = TYPES[type_key]
    payload: dict[str, Any] = {}
    for field in meta["fields"]:
        value = data.get(field, "")
        if value is None:
            value = ""
        if field == "level":
            payload[field] = parse_level(value)
            continue
        if field == "unit":
            payload[field] = parse_unit(value)
            continue
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


def increment_practice_count(type_key: str, entry_id: int) -> int:
    type_key = ensure_type(type_key)
    if type_key not in PRACTICE_TYPES:
        raise ValueError(f"{type_key} does not support practice_count")
    table = TYPES[type_key]["table"]
    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE {table}
            SET practice_count = practice_count + 1,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (entry_id,),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT practice_count FROM {table} WHERE id = ?",
            (entry_id,),
        ).fetchone()
        return int(row["practice_count"]) if row else 0


def random_practice_item(
    *,
    level: str | int | None = "",
    unit: str | int | None = "",
    cefr_level: str = "",
    types: list[str] | tuple[str, ...] | None = None,
    exclude: list[tuple[str, int]] | None = None,
) -> dict[str, Any] | None:
    """Pick one random practiceable entry matching filters."""
    exclude_set = {(t, i) for t, i in (exclude or [])}
    type_keys = [
        t for t in (types or PRACTICE_TYPES) if t in PRACTICE_TYPES
    ] or list(PRACTICE_TYPES)
    candidates: list[dict[str, Any]] = []

    with get_connection() as conn:
        for type_key in type_keys:
            meta = TYPES[type_key]
            table = meta["table"]
            sql = f"SELECT * FROM {table} WHERE 1=1"
            params: list[Any] = []
            if cefr_level:
                sql += " AND cefr_level = ?"
                params.append(cefr_level)
            if level not in ("", None):
                sql += " AND level = ?"
                params.append(parse_level(level))
            if unit not in ("", None):
                sql += " AND unit = ?"
                params.append(parse_unit(unit))
            for row in conn.execute(sql, params):
                entry_id = int(row["id"])
                if (type_key, entry_id) in exclude_set:
                    continue
                candidates.append(
                    {
                        "type_key": type_key,
                        "id": entry_id,
                        "label": meta["label"],
                        "title": row[meta["title_field"]],
                        "body": row[meta["body_field"]],
                        "example": row["example"] if "example" in row.keys() else "",
                        "cefr_level": row["cefr_level"],
                        "level": row["level"],
                        "unit": row["unit"],
                        "practice_count": row["practice_count"],
                    }
                )

    if not candidates:
        return None
    return random.choice(candidates)


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


def empty_form(type_key: str) -> dict[str, Any]:
    type_key = ensure_type(type_key)
    return {field: "" for field in TYPES[type_key]["fields"]} | {
        "cefr_level": "B1",
        "level": DEFAULT_COURSE_LEVEL,
        "unit": DEFAULT_UNIT,
    }

from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, session, url_for

import ai
import db

app = Flask(__name__)
app.secret_key = "english-to-b2-local-dev"


@app.before_request
def ensure_db() -> None:
    db.init_db()


def _form_payload(type_key: str) -> dict:
    meta = db.TYPES[type_key]
    payload = {field: request.form.get(field, "").strip() for field in meta["fields"] if field != "level"}
    payload["level"] = db.parse_level(request.form.get("level"))
    if payload.get("cefr_level") not in db.CEFR_LEVELS:
        payload["cefr_level"] = "B1"
    return payload


def _missing_required(type_key: str, payload: dict) -> bool:
    return any(not payload.get(field) for field in db.TYPES[type_key]["required"])


def _nav_levels() -> list[int]:
    return db.distinct_levels() or [db.DEFAULT_COURSE_LEVEL]


def _practice_session_list() -> list[dict]:
    items = session.get("practice_items")
    if not isinstance(items, list):
        items = []
        session["practice_items"] = items
    return items


def _set_practice_filters() -> tuple[str, str]:
    level = request.values.get("level", session.get("practice_level", "")).strip()
    cefr_level = request.values.get("cefr_level", session.get("practice_cefr", "")).strip()
    if cefr_level and cefr_level not in db.CEFR_LEVELS:
        cefr_level = ""
    session["practice_level"] = level
    session["practice_cefr"] = cefr_level
    return level, cefr_level


def _hydrate_practice_cards(items: list[dict], results: dict[str, dict] | None = None) -> list[dict]:
    cards: list[dict] = []
    results = results or {}
    for item in items:
        type_key = db.ensure_type(item.get("type_key", ""))
        try:
            entry_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        entry = db.get_entry(type_key, entry_id)
        if entry is None:
            continue
        meta = db.TYPES[type_key]
        uid = f"{type_key}:{entry_id}"
        card = {
            "uid": uid,
            "type_key": type_key,
            "id": entry_id,
            "label": meta["label"],
            "title": entry[meta["title_field"]],
            "body": entry[meta["body_field"]],
            "example": entry["example"] if "example" in entry.keys() else "",
            "cefr_level": entry["cefr_level"],
            "level": entry["level"],
            "practice_count": entry["practice_count"] if "practice_count" in entry.keys() else 0,
            "sentence": item.get("sentence", ""),
            "result": results.get(uid),
        }
        cards.append(card)
    return cards


@app.get("/")
def index():
    type_key = db.ensure_type(request.args.get("type", db.DEFAULT_TYPE).strip())
    q = request.args.get("q", "").strip()
    cefr_level = request.args.get("cefr_level", "").strip()
    level = request.args.get("level", "").strip()

    entries = db.list_entries(type_key, q=q, cefr_level=cefr_level, level=level)
    stats = db.progress_stats()
    meta = db.TYPES[type_key]

    return render_template(
        "index.html",
        type_key=type_key,
        meta=meta,
        types=db.TYPES,
        type_order=db.TYPE_ORDER,
        entries=entries,
        stats=stats,
        q=q,
        cefr_level=cefr_level,
        level=level,
        levels=db.CEFR_LEVELS,
        course_levels=_nav_levels(),
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    type_key = db.ensure_type(
        (request.args.get("type") or request.form.get("type") or db.DEFAULT_TYPE).strip()
    )
    meta = db.TYPES[type_key]

    if request.method == "POST":
        payload = _form_payload(type_key)
        if _missing_required(type_key, payload):
            flash("Please fill in the required fields.", "error")
            return render_template(
                "form.html",
                mode="add",
                type_key=type_key,
                meta=meta,
                types=db.TYPES,
                type_order=db.TYPE_ORDER,
                entry=payload,
                levels=db.CEFR_LEVELS,
            )

        db.add_entry(type_key, **payload)
        flash(f"Saved to {meta['label']}.", "ok")
        return redirect(url_for("index", type=type_key))

    return render_template(
        "form.html",
        mode="add",
        type_key=type_key,
        meta=meta,
        types=db.TYPES,
        type_order=db.TYPE_ORDER,
        entry=db.empty_form(type_key),
        levels=db.CEFR_LEVELS,
    )


@app.route("/edit/<type_key>/<int:entry_id>", methods=["GET", "POST"])
def edit(type_key: str, entry_id: int):
    type_key = db.ensure_type(type_key)
    meta = db.TYPES[type_key]
    entry = db.get_entry(type_key, entry_id)
    if entry is None:
        flash("Entry not found.", "error")
        return redirect(url_for("index", type=type_key))

    if request.method == "POST":
        payload = _form_payload(type_key)
        if _missing_required(type_key, payload):
            flash("Please fill in the required fields.", "error")
            return render_template(
                "form.html",
                mode="edit",
                type_key=type_key,
                meta=meta,
                types=db.TYPES,
                type_order=db.TYPE_ORDER,
                entry={"id": entry_id, **payload},
                levels=db.CEFR_LEVELS,
            )

        db.update_entry(type_key, entry_id, **payload)
        flash("Entry updated.", "ok")
        return redirect(url_for("index", type=type_key))

    return render_template(
        "form.html",
        mode="edit",
        type_key=type_key,
        meta=meta,
        types=db.TYPES,
        type_order=db.TYPE_ORDER,
        entry=entry,
        levels=db.CEFR_LEVELS,
    )


@app.post("/delete/<type_key>/<int:entry_id>")
def delete(type_key: str, entry_id: int):
    type_key = db.ensure_type(type_key)
    db.delete_entry(type_key, entry_id)
    flash("Entry deleted.", "ok")
    return redirect(url_for("index", type=type_key))


@app.route("/import", methods=["GET", "POST"])
def import_notes():
    default_level = db.DEFAULT_COURSE_LEVEL
    default_cefr = "B1"
    notes_text = ""
    summary = None

    if request.method == "POST":
        notes_text = request.form.get("notes", "").strip()
        level = db.parse_level(request.form.get("level"), default_level)
        cefr_level = request.form.get("cefr_level", default_cefr).strip()
        if cefr_level not in db.CEFR_LEVELS:
            cefr_level = default_cefr
        default_level = level
        default_cefr = cefr_level

        if not notes_text:
            flash("Paste your study notes first.", "error")
        else:
            try:
                classified = ai.parse_notes(notes_text, level=level, cefr_level=cefr_level)
                summary = {key: 0 for key in db.TYPE_ORDER}
                total = 0
                for type_key, items in classified.items():
                    for item in items:
                        db.add_entry(type_key, **item)
                        summary[type_key] += 1
                        total += 1
                if total == 0:
                    flash("Gemini found nothing to save. Try clearer notes.", "error")
                    summary = None
                else:
                    flash(f"Imported {total} entries.", "ok")
                    notes_text = ""
            except ai.AiError as exc:
                flash(str(exc), "error")

    return render_template(
        "import.html",
        notes_text=notes_text,
        level=default_level,
        cefr_level=default_cefr,
        levels=db.CEFR_LEVELS,
        summary=summary,
        types=db.TYPES,
        type_order=db.TYPE_ORDER,
    )


@app.route("/practice", methods=["GET", "POST"])
def practice():
    level, cefr_level = _set_practice_filters()
    items = _practice_session_list()
    results_map: dict[str, dict] = session.get("practice_results") or {}
    if not isinstance(results_map, dict):
        results_map = {}

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "clear":
            session["practice_items"] = []
            session["practice_results"] = {}
            flash("Practice list cleared.", "ok")
            return redirect(url_for("practice", level=level or None, cefr_level=cefr_level or None))

        if action == "add":
            # Preserve any typed sentences before adding another card.
            preserved: list[dict] = []
            for item in items:
                uid = f"{item['type_key']}:{item['id']}"
                sentence = request.form.get(f"sentence_{uid}", item.get("sentence", ""))
                preserved.append(
                    {
                        "type_key": item["type_key"],
                        "id": item["id"],
                        "sentence": sentence,
                    }
                )
            exclude = [(p["type_key"], int(p["id"])) for p in preserved]
            picked = db.random_practice_item(
                level=level,
                cefr_level=cefr_level,
                exclude=exclude,
            )
            if picked is None:
                flash("No matching items left for these filters.", "error")
                session["practice_items"] = preserved
            else:
                preserved.append(
                    {
                        "type_key": picked["type_key"],
                        "id": picked["id"],
                        "sentence": "",
                    }
                )
                session["practice_items"] = preserved
                session["practice_results"] = {}
            return redirect(url_for("practice", level=level or None, cefr_level=cefr_level or None))

        if action == "submit":
            to_grade: list[dict] = []
            updated_items: list[dict] = []
            results_map = {}

            for item in items:
                type_key = item["type_key"]
                entry_id = int(item["id"])
                uid = f"{type_key}:{entry_id}"
                sentence = request.form.get(f"sentence_{uid}", "").strip()
                updated_items.append(
                    {"type_key": type_key, "id": entry_id, "sentence": sentence}
                )
                entry = db.get_entry(type_key, entry_id)
                if entry is None:
                    results_map[uid] = {
                        "correct": False,
                        "feedback": "Entry no longer exists.",
                        "corrected_sentence": "",
                        "incomplete": True,
                    }
                    continue
                if not sentence:
                    results_map[uid] = {
                        "correct": False,
                        "feedback": "Write a sentence before submitting.",
                        "corrected_sentence": "",
                        "incomplete": True,
                    }
                    continue
                meta = db.TYPES[type_key]
                to_grade.append(
                    {
                        "uid": uid,
                        "type_key": type_key,
                        "title": entry[meta["title_field"]],
                        "body": entry[meta["body_field"]],
                        "example": entry["example"] if "example" in entry.keys() else "",
                        "sentence": sentence,
                        "entry_id": entry_id,
                    }
                )

            session["practice_items"] = updated_items

            if not to_grade:
                flash("Add prompts with + and write at least one sentence.", "error")
                session["practice_results"] = results_map
            else:
                try:
                    graded = ai.grade_sentences(to_grade)
                    by_uid = {g["uid"]: g for g in graded}
                    for g_item in to_grade:
                        uid = g_item["uid"]
                        grade = by_uid.get(uid)
                        if not grade:
                            results_map[uid] = {
                                "correct": False,
                                "feedback": "No grade returned for this item.",
                                "corrected_sentence": g_item["sentence"],
                            }
                            continue
                        results_map[uid] = {
                            "correct": grade["correct"],
                            "feedback": grade["feedback"],
                            "corrected_sentence": grade["corrected_sentence"],
                        }
                        if grade["correct"]:
                            new_count = db.increment_practice_count(
                                g_item["type_key"], g_item["entry_id"]
                            )
                            results_map[uid]["practice_count"] = new_count
                    session["practice_results"] = results_map
                    correct_n = sum(1 for r in results_map.values() if r.get("correct"))
                    flash(f"Graded {len(to_grade)} sentence(s). {correct_n} correct.", "ok")
                except ai.AiError as exc:
                    flash(str(exc), "error")

            return redirect(url_for("practice", level=level or None, cefr_level=cefr_level or None))

    cards = _hydrate_practice_cards(items, results_map)
    return render_template(
        "practice.html",
        cards=cards,
        level=level,
        cefr_level=cefr_level,
        levels=db.CEFR_LEVELS,
        course_levels=_nav_levels(),
    )


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5050)

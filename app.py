from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, url_for

import db

app = Flask(__name__)
app.secret_key = "english-to-b2-local-dev"


@app.before_request
def ensure_db() -> None:
    db.init_db()


def _form_payload(type_key: str) -> dict[str, str]:
    meta = db.TYPES[type_key]
    payload = {field: request.form.get(field, "").strip() for field in meta["fields"]}
    if payload.get("cefr_level") not in db.CEFR_LEVELS:
        payload["cefr_level"] = "B1"
    return payload


def _missing_required(type_key: str, payload: dict[str, str]) -> bool:
    return any(not payload.get(field) for field in db.TYPES[type_key]["required"])


@app.get("/")
def index():
    type_key = db.ensure_type(request.args.get("type", db.DEFAULT_TYPE).strip())
    q = request.args.get("q", "").strip()
    cefr_level = request.args.get("cefr_level", "").strip()

    entries = db.list_entries(type_key, q=q, cefr_level=cefr_level)
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
        levels=db.CEFR_LEVELS,
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


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5050)

from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, url_for

import db

app = Flask(__name__)
app.secret_key = "english-to-b2-local-dev"


@app.before_request
def ensure_db() -> None:
    db.init_db()


@app.get("/")
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    cefr_level = request.args.get("cefr_level", "").strip()

    entries = db.list_entries(q=q, category=category, cefr_level=cefr_level)
    stats = db.progress_stats()
    return render_template(
        "index.html",
        entries=entries,
        stats=stats,
        q=q,
        category=category,
        cefr_level=cefr_level,
        categories=db.CATEGORIES,
        levels=db.CEFR_LEVELS,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        meaning = request.form.get("meaning", "").strip()
        example = request.form.get("example", "").strip()
        notes = request.form.get("notes", "").strip()
        category = request.form.get("category", "vocabulary").strip()
        cefr_level = request.form.get("cefr_level", "B1").strip()

        if not title or not meaning:
            flash("Title and meaning are required.", "error")
            return render_template(
                "form.html",
                mode="add",
                entry={
                    "title": title,
                    "meaning": meaning,
                    "example": example,
                    "notes": notes,
                    "category": category,
                    "cefr_level": cefr_level,
                },
                categories=db.CATEGORIES,
                levels=db.CEFR_LEVELS,
            )

        if category not in db.CATEGORIES:
            category = "other"
        if cefr_level not in db.CEFR_LEVELS:
            cefr_level = "B1"

        db.add_entry(
            title=title,
            meaning=meaning,
            example=example,
            notes=notes,
            category=category,
            cefr_level=cefr_level,
        )
        flash("Saved to your B2 knowledge base.", "ok")
        return redirect(url_for("index"))

    return render_template(
        "form.html",
        mode="add",
        entry={
            "title": "",
            "meaning": "",
            "example": "",
            "notes": "",
            "category": "vocabulary",
            "cefr_level": "B1",
        },
        categories=db.CATEGORIES,
        levels=db.CEFR_LEVELS,
    )


@app.route("/edit/<int:entry_id>", methods=["GET", "POST"])
def edit(entry_id: int):
    entry = db.get_entry(entry_id)
    if entry is None:
        flash("Entry not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        meaning = request.form.get("meaning", "").strip()
        example = request.form.get("example", "").strip()
        notes = request.form.get("notes", "").strip()
        category = request.form.get("category", "vocabulary").strip()
        cefr_level = request.form.get("cefr_level", "B1").strip()

        if not title or not meaning:
            flash("Title and meaning are required.", "error")
            return render_template(
                "form.html",
                mode="edit",
                entry={
                    "id": entry_id,
                    "title": title,
                    "meaning": meaning,
                    "example": example,
                    "notes": notes,
                    "category": category,
                    "cefr_level": cefr_level,
                },
                categories=db.CATEGORIES,
                levels=db.CEFR_LEVELS,
            )

        if category not in db.CATEGORIES:
            category = "other"
        if cefr_level not in db.CEFR_LEVELS:
            cefr_level = "B1"

        db.update_entry(
            entry_id,
            title=title,
            meaning=meaning,
            example=example,
            notes=notes,
            category=category,
            cefr_level=cefr_level,
        )
        flash("Entry updated.", "ok")
        return redirect(url_for("index"))

    return render_template(
        "form.html",
        mode="edit",
        entry=entry,
        categories=db.CATEGORIES,
        levels=db.CEFR_LEVELS,
    )


@app.post("/delete/<int:entry_id>")
def delete(entry_id: int):
    db.delete_entry(entry_id)
    flash("Entry deleted.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5050)

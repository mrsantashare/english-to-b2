from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

import db

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


class AiError(RuntimeError):
    """Raised when Gemini is unavailable or returns unusable output."""


def _api_key() -> str:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise AiError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add your Gemini API key."
        )
    return key


def _client():
    try:
        from google import genai
    except ImportError as exc:
        raise AiError(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return genai.Client(api_key=_api_key())


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _generate_json(prompt: str) -> Any:
    client = _client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    raw = (response.text or "").strip()
    if not raw:
        raise AiError("Gemini returned an empty response.")
    try:
        return _extract_json(raw)
    except json.JSONDecodeError as exc:
        raise AiError(f"Gemini returned invalid JSON: {exc}") from exc


def parse_notes(
    text: str,
    *,
    level: int = db.DEFAULT_COURSE_LEVEL,
    cefr_level: str = "B1",
) -> dict[str, list[dict[str, Any]]]:
    """Classify study notes into the five learning types."""
    if cefr_level not in db.CEFR_LEVELS:
        cefr_level = "B1"
    level = db.parse_level(level)

    prompt = f"""You are helping a learner build an English knowledge base toward CEFR B2.

Classify the study notes below into these categories. Return ONLY JSON with this shape:
{{
  "new_words": [{{"word": "", "meaning": "", "example": "", "notes": "", "cefr_level": "B1"}}],
  "verb_phrases": [{{"phrase": "", "meaning": "", "example": "", "notes": "", "cefr_level": "B1"}}],
  "sentence_structures": [{{"pattern": "", "explanation": "", "example": "", "notes": "", "cefr_level": "B1"}}],
  "dialogs": [{{"title": "", "content": "", "notes": "", "cefr_level": "B1"}}],
  "paragraphs": [{{"title": "", "content": "", "notes": "", "cefr_level": "B1"}}]
}}

Rules:
- Use empty arrays when a category has nothing.
- Prefer CEFR from context; otherwise use "{cefr_level}".
- cefr_level must be one of: A1, A2, B1, B2.
- Keep Vietnamese or English meanings as written in the notes.
- Do not invent items that are not supported by the notes.
- For dialogs, put the full conversation in content.
- For paragraphs, put the full paragraph in content.

Default course level for this import (do not put in JSON; the app will attach it): {level}

NOTES:
{text}
"""
    data = _generate_json(prompt)
    if not isinstance(data, dict):
        raise AiError("Gemini did not return a JSON object.")

    result: dict[str, list[dict[str, Any]]] = {key: [] for key in db.TYPE_ORDER}
    for type_key in db.TYPE_ORDER:
        items = data.get(type_key, [])
        if not isinstance(items, list):
            continue
        meta = db.TYPES[type_key]
        for item in items:
            if not isinstance(item, dict):
                continue
            payload = {field: str(item.get(field, "") or "").strip() for field in meta["fields"] if field != "level"}
            payload["level"] = level
            if payload.get("cefr_level") not in db.CEFR_LEVELS:
                payload["cefr_level"] = cefr_level
            if any(not payload.get(field) for field in meta["required"]):
                continue
            result[type_key].append(payload)
    return result


def grade_sentences(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Grade learner sentences for practice prompts.

    Each item should include: uid, type_key, title, body, example (optional), sentence.
    Returns one result per input with: uid, correct, feedback, corrected_sentence.
    """
    if not items:
        return []

    payload = [
        {
            "uid": item["uid"],
            "type": item["type_key"],
            "knowledge": item["title"],
            "meaning": item["body"],
            "example": item.get("example") or "",
            "learner_sentence": item["sentence"],
        }
        for item in items
    ]

    prompt = f"""You are an English teacher. Grade each learner sentence for correct use of the given knowledge item.

Return ONLY JSON:
{{
  "results": [
    {{
      "uid": "string matching input",
      "correct": true,
      "feedback": "short explanation of what is wrong, or praise if correct",
      "corrected_sentence": "a natural corrected sentence using the knowledge; if already correct, repeat the learner sentence"
    }}
  ]
}}

Rules:
- Mark correct=true only if the sentence is grammatically acceptable AND clearly uses the knowledge item with the right meaning.
- If wrong: feedback must say what is wrong; corrected_sentence must be a good fix.
- Keep feedback concise (1-2 sentences).
- Return one result for every input uid.

INPUT:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    data = _generate_json(prompt)
    results_raw = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results_raw, list):
        raise AiError("Gemini grading response missing results array.")

    by_uid = {
        str(r.get("uid")): r
        for r in results_raw
        if isinstance(r, dict) and r.get("uid") is not None
    }

    graded: list[dict[str, Any]] = []
    for item in items:
        uid = str(item["uid"])
        raw = by_uid.get(uid, {})
        correct = bool(raw.get("correct"))
        feedback = str(raw.get("feedback") or "").strip()
        corrected = str(raw.get("corrected_sentence") or "").strip()
        if not feedback:
            feedback = "Correct." if correct else "This sentence needs fixing."
        if not corrected:
            corrected = item["sentence"] if correct else item.get("example") or item["sentence"]
        graded.append(
            {
                "uid": uid,
                "correct": correct,
                "feedback": feedback,
                "corrected_sentence": corrected,
            }
        )
    return graded

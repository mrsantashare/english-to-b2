# English to B2

Personal knowledge base for your path to **B2 English**.

Five tabs — each backed by its own SQLite table:

| Tab | Table | What goes here |
|-----|-------|----------------|
| New words | `new_words` | Vocabulary |
| Verb phrases | `verb_phrases` | Phrasal verbs / verb phrases |
| Sentence structure | `sentence_structures` | Grammar patterns |
| Dialog | `dialogs` | Short conversations |
| Paragraph | `paragraphs` | Longer writing samples |

Every entry has a numeric **course Level** (existing data defaults to **13**) plus CEFR (`A1`–`B2`). New words, verb phrases, and sentence structures also track **practice_count**.

## Run

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # then set GEMINI_API_KEY
python app.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

Data file: `data/english_to_b2.db` (tracked in git so notes sync across computers).

## Gemini API key

Import and Practice need Google Gemini (free tier works).

1. Create a key at [Google AI Studio](https://aistudio.google.com/apikey)
2. Copy `.env.example` → `.env`
3. Set `GEMINI_API_KEY=your_key`

Optional: `GEMINI_MODEL=gemini-flash-latest` (default).

## Import notes

Open **Import**, paste study notes, choose Level / default CEFR, then **Process with Gemini**. Entries are classified into the five tables.

## Practice

Open **Practice**, filter by Level/CEFR, click **+** (as many times as you like) to add a random new word / verb phrase / sentence structure, write a sentence for each, then **Submit**. Correct answers increment `practice_count`; wrong answers show feedback and a corrected sentence.

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

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

Data file: `data/english_to_b2.db`.

## Note workflow

Paste your study notes in chat. They will be classified into the five types above and saved into the matching table/tab.

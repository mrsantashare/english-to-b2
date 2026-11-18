-- Five learning types; each tab maps to one table.

CREATE TABLE IF NOT EXISTS new_words (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  word TEXT NOT NULL,
  meaning TEXT NOT NULL,
  example TEXT,
  notes TEXT,
  cefr_level TEXT NOT NULL DEFAULT 'B1' CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  level INTEGER NOT NULL DEFAULT 13,
  unit INTEGER NOT NULL DEFAULT 50,
  practice_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS verb_phrases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phrase TEXT NOT NULL,
  meaning TEXT NOT NULL,
  example TEXT,
  notes TEXT,
  cefr_level TEXT NOT NULL DEFAULT 'B1' CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  level INTEGER NOT NULL DEFAULT 13,
  unit INTEGER NOT NULL DEFAULT 50,
  practice_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sentence_structures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern TEXT NOT NULL,
  explanation TEXT NOT NULL,
  example TEXT,
  notes TEXT,
  cefr_level TEXT NOT NULL DEFAULT 'B1' CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  level INTEGER NOT NULL DEFAULT 13,
  unit INTEGER NOT NULL DEFAULT 50,
  practice_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS dialogs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  notes TEXT,
  cefr_level TEXT NOT NULL DEFAULT 'B1' CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  level INTEGER NOT NULL DEFAULT 13,
  unit INTEGER NOT NULL DEFAULT 50,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS paragraphs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  notes TEXT,
  cefr_level TEXT NOT NULL DEFAULT 'B1' CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  level INTEGER NOT NULL DEFAULT 13,
  unit INTEGER NOT NULL DEFAULT 50,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_new_words_word ON new_words(word);
CREATE INDEX IF NOT EXISTS idx_verb_phrases_phrase ON verb_phrases(phrase);
CREATE INDEX IF NOT EXISTS idx_sentence_structures_pattern ON sentence_structures(pattern);
CREATE INDEX IF NOT EXISTS idx_dialogs_title ON dialogs(title);
CREATE INDEX IF NOT EXISTS idx_paragraphs_title ON paragraphs(title);

CREATE INDEX IF NOT EXISTS idx_new_words_level ON new_words(level);
CREATE INDEX IF NOT EXISTS idx_verb_phrases_level ON verb_phrases(level);
CREATE INDEX IF NOT EXISTS idx_sentence_structures_level ON sentence_structures(level);
CREATE INDEX IF NOT EXISTS idx_dialogs_level ON dialogs(level);
CREATE INDEX IF NOT EXISTS idx_paragraphs_level ON paragraphs(level);

-- unit indexes are created in db._migrate_schema after the unit column exists
-- on older databases that were created before unit was added.

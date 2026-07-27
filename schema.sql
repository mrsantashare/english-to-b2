CREATE TABLE IF NOT EXISTS knowledge (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  meaning TEXT NOT NULL,
  example TEXT,
  notes TEXT,
  category TEXT NOT NULL CHECK (
    category IN ('vocabulary', 'phrase', 'idiom', 'grammar', 'pronunciation', 'other')
  ),
  cefr_level TEXT NOT NULL CHECK (
    cefr_level IN ('A1', 'A2', 'B1', 'B2')
  ),
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_cefr ON knowledge(cefr_level);
CREATE INDEX IF NOT EXISTS idx_knowledge_title ON knowledge(title);

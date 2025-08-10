CREATE EXTENSION IF NOT EXISTS vector;

-- Table holds either issues or individual long comments as rows
CREATE TABLE IF NOT EXISTS docs (
  id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL UNIQUE,      -- e.g., issue#comment or issue id (now unique for conflict handling)
  kind TEXT NOT NULL,                  -- 'issue' | 'comment'
  repo TEXT NOT NULL,                  -- e.g., tiangolo/fastapi
  url TEXT NOT NULL,
  title TEXT,
  body TEXT NOT NULL,
  labels TEXT[],
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  embedding vector(1536)               -- adjust if you change models
);

CREATE INDEX IF NOT EXISTS idx_docs_repo ON docs(repo);
CREATE INDEX IF NOT EXISTS idx_docs_labels ON docs USING GIN(labels);
CREATE INDEX IF NOT EXISTS idx_docs_source_id ON docs(source_id);
-- IVF Flat index for ANN. Tune lists per dataset size.
CREATE INDEX IF NOT EXISTS idx_docs_embedding ON docs USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
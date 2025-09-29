CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id        uuid PRIMARY KEY,                  
  file_name text NOT NULL,
  strategy  text,
  category  text,
  text      text NOT NULL,
  metadata  jsonb,
  embedding vector(1536)
);


CREATE INDEX IF NOT EXISTS idx_documents_embedding_cosine
  ON documents USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);


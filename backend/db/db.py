import os
import psycopg2
from psycopg2.extras import execute_values, Json


PG_DSN = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(PG_DSN)


def upload_chunks_embed(chunk_data, filename: str, embed_data, model_dim: int = 1536):

    rows = []
    for c, v in zip(chunk_data, embed_data):
        md = c.get("metadata") or {}
        if hasattr(md, "to_dict"):
            md = md.to_dict()
        elif not isinstance(md, dict):
            try:
                md = dict(md)
            except Exception:
                md = {}
        rows.append((
            c["id"],
            filename,
            c.get("category"),
            c["text"],
            Json(md),
            v
        ))

    sql_delete = "DELETE FROM documents WHERE file_name = %s"
    sql_insert = """
        INSERT INTO documents (id, file_name, category, text, metadata, embedding)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
        file_name = EXCLUDED.file_name,
        category  = EXCLUDED.category,
        text      = EXCLUDED.text,
        metadata  = EXCLUDED.metadata,
        embedding = EXCLUDED.embedding;
    """
    with psycopg2.connect(PG_DSN) as conn, conn.cursor() as cur:
        cur.execute(sql_delete, (filename,))
        execute_values(cur, sql_insert, rows)

    return len(rows)

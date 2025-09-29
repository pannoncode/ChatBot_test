import psycopg2
from typing import Any, Dict, List

PG_DSN = "postgresql://postgres:postgres@localhost:5432/ragdb"


def search_similar(query_vector: List[float], top_k: int = 5):
    sql = """
        SELECT
        id,
        file_name,
        category,
        text,
        metadata,
        1 - (embedding <=> %s::vector) AS score
        FROM documents
        ORDER BY embedding <-> %s::vector
        LIMIT %s;
    """

    params = [query_vector, query_vector, top_k]

    results = []
    
    conn = psycopg2.connect(PG_DSN)
    
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        for row in rows:
            item: Dict[str, Any] = {}
            for idx, col in enumerate(colnames):
                item[col] = row[idx]
            results.append(item)

        cur.close()
    finally:
        conn.close()

    return results
        
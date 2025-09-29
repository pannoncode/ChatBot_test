from openai import OpenAI
from dotenv import load_dotenv

from typing import List
import time

load_dotenv()
openai_client = OpenAI()

# Modellek
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIM = 1536


def gen_openai_embeddings(texts: List[str], dimensions: int = None):
    if not texts:
        return []

    try:
        if dimensions and dimensions < OPENAI_EMBEDDING_DIM:
            dimensions = dimensions
        response = openai_client.embeddings.create(
            input=texts, model=OPENAI_MODEL)
        embeddings = [item.embedding for item in response.data]
        return embeddings

    except Exception as e:
        return {"error": f"Hiba lépett fel: {e}"}


def document_embeddings(texts: List[str], batch_size: int = 20):
    try:
        openai_batch_size = batch_size
        openai_embeddings_list = []

        for i in range(0, len(texts), openai_batch_size):
            batch_texts = texts[i:i+openai_batch_size]
            batch_embeddings = gen_openai_embeddings(batch_texts)
            openai_embeddings_list.extend(batch_embeddings)

            if i + openai_batch_size < len(texts):
                time.sleep(0.1)

        return openai_embeddings_list

    except Exception as e:
        return {"error": f"Hiba lépett fel: {e}"}

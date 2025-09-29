from sentence_transformers import CrossEncoder
from typing import List, Dict

cross_encoder = CrossEncoder(
    'cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)


def rerank_with_cross_encoder(query: str, candidates: List[Dict], top_n: int = 5) -> List[Dict]:
    """Rerank search results using a cross-encoder model."""
    if not candidates:
        return []

    pairs = [[query, candidate.get('text')] for candidate in candidates]

    ce_scores = cross_encoder.predict(pairs)

    for candidate, score in zip(candidates, ce_scores):
        candidate['rerank_score'] = float(score)

    reranked = sorted(
        candidates, key=lambda x: x['rerank_score'], reverse=True)

    return reranked[:top_n]

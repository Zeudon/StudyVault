"""
RerankerAgent
=============
Second-stage cross-encoder re-ranking for StudyVault RAG.

Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80 MB, CPU-only) from
sentence-transformers to score (query, passage) pairs and re-order a
candidate set returned by Qdrant's first-stage ANN search.

The model is lazy-loaded on first call and shared across all instances
via a module-level singleton so weights are only downloaded once.
"""
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level singleton — loaded once on first rerank() call.
_cross_encoder = None


def _get_cross_encoder(model_name: str):
    """Return (and lazily initialise) the module-level CrossEncoder singleton."""
    global _cross_encoder
    if _cross_encoder is None:
        logger.info("Loading cross-encoder model '%s' (first call)…", model_name)
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(model_name)
        logger.info("Cross-encoder model loaded.")
    return _cross_encoder


class RerankerAgent:
    """
    Re-ranks a list of candidate chunks using a cross-encoder.

    Parameters
    ----------
    model_name : str
        HuggingFace model ID for the CrossEncoder.
    top_k : int
        Number of top results to return after re-ranking.
    """

    def __init__(self, model_name: str, top_k: int):
        self.model_name = model_name
        self.top_k = top_k

    async def rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Score each candidate against *query* and return the top-*top_k* results
        sorted by descending cross-encoder score.

        The returned dicts are the same objects as in *candidates* — only their
        order (and an added ``rerank_score`` field) changes.

        Falls back to returning ``candidates[:top_k]`` in original order if
        anything goes wrong (model unavailable, empty input, etc.).
        """
        if not candidates:
            return candidates

        try:
            encoder = _get_cross_encoder(self.model_name)

            pairs = [(query, c.get("text", "")) for c in candidates]

            # CrossEncoder.predict is CPU-bound — run it in a thread pool so we
            # don't block the asyncio event loop.
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, encoder.predict, pairs)

            for candidate, score in zip(candidates, scores):
                candidate["rerank_score"] = float(score)

            ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
            top = ranked[: self.top_k]

            logger.info(
                "Re-ranked %d candidates → keeping top %d", len(candidates), len(top)
            )
            return top

        except Exception as exc:
            logger.warning(
                "RerankerAgent.rerank failed (%s) — returning original order.", exc
            )
            return candidates[: self.top_k]

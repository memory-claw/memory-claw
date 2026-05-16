"""Institutional memory search over Chroma."""

from __future__ import annotations

from typing import Any

from institutional_memory.config import RELEVANCE_THRESHOLD, TOP_K
from institutional_memory.ingest import embed_text, get_chroma_collection


def embed_query(query: str) -> list[float]:
    return embed_text(query)


def search_memory(
    query: str,
    threshold: float | None = RELEVANCE_THRESHOLD,
    top_k: int | None = TOP_K,
    draft_text: str | None = None,
) -> list[dict[str, Any]]:
    search_text = query if draft_text is None else f"{query}\n\nDraft context:\n{draft_text}"
    collection = get_chroma_collection()
    result = collection.query(
        query_embeddings=[embed_query(search_text)],
        n_results=top_k or TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    hits_by_source: dict[str, dict[str, Any]] = {}
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    min_score = RELEVANCE_THRESHOLD if threshold is None else threshold

    for document, metadata, distance in zip(documents, metadatas, distances, strict=False):
        source = str((metadata or {}).get("source", "unknown"))
        score = round(1.0 - float(distance), 4)
        if score < min_score:
            continue
        hit = {
            "source": source,
            "score": score,
            "text": document,
            "start_word": (metadata or {}).get("start_word"),
        }
        if source not in hits_by_source or score > hits_by_source[source]["score"]:
            hits_by_source[source] = hit

    return sorted(hits_by_source.values(), key=lambda item: item["score"], reverse=True)

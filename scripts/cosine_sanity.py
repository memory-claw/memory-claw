from __future__ import annotations

import json
import uuid

from institutional_memory.ingest import embed_text, get_chroma_collection


def score_from_distance(distance: float) -> float:
    return round(1.0 - float(distance), 4)


def run_sanity() -> dict:
    text = "cosine sanity institutional memory probe"
    embedding = embed_text(text)
    collection = get_chroma_collection()
    doc_id = f"__cosine_sanity__:{uuid.uuid4()}"
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"source": "__cosine_sanity__"}],
    )
    try:
        result = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances", "metadatas"],
        )
        distance = result["distances"][0][0]
        score = score_from_distance(distance)
        return {"ok": score >= 0.99, "score": score, "distance": distance}
    finally:
        collection.delete(ids=[doc_id])


def main() -> int:
    result = run_sanity()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

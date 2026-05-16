"""Corpus ingestion into persistent Chroma memory."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import chromadb
import ollama

from institutional_memory.config import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    INGESTED_REGISTRY,
    OLLAMA_BASE_URL,
    PROJECT_ROOT,
)
from institutional_memory.documents import load_document_text


def _words(text: str) -> list[str]:
    return text.split()


def chunk_text(text: str, source: str) -> list[dict[str, Any]]:
    words = _words(text)
    chunks: list[dict[str, Any]] = []
    if not words:
        return chunks

    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for index, start in enumerate(range(0, len(words), step)):
        part = words[start : start + CHUNK_SIZE]
        if len(part) < 10:
            continue
        chunk_id = f"{source}:{start}:{index}"
        chunks.append(
            {
                "id": chunk_id,
                "source": source,
                "start_word": start,
                "index": index,
                "text": " ".join(part),
            }
        )
    return chunks


def embed_text(text: str) -> list[float]:
    response = ollama.Client(host=OLLAMA_BASE_URL).embed(model=EMBEDDING_MODEL, input=text)
    embeddings = response.get("embeddings") or []
    if not embeddings:
        raise RuntimeError("Ollama returned no embedding")
    return list(embeddings[0])


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            configuration={"hnsw": {"space": "cosine"}},
        )
    except TypeError:
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )


def _load_ingested() -> dict[str, str]:
    if not INGESTED_REGISTRY.exists():
        return {}
    return json.loads(INGESTED_REGISTRY.read_text(encoding="utf-8"))


def _save_ingested(registry: dict[str, str]) -> None:
    INGESTED_REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest_folder(folder: Path, force: bool = False) -> dict[str, int]:
    if force:
        shutil.rmtree(CHROMA_PATH, ignore_errors=True)
        INGESTED_REGISTRY.unlink(missing_ok=True)

    collection = get_chroma_collection()
    registry = _load_ingested()
    files = 0
    chunks = 0

    for path in sorted(folder.iterdir()):
        if path.name.startswith(".") or path.suffix.lower() not in {".txt", ".md", ".pdf"}:
            continue
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        fingerprint = _fingerprint(path)
        if not force and registry.get(rel) == fingerprint:
            continue
        if not force and rel in registry:
            collection.delete(where={"source": rel})

        text = load_document_text(path)
        file_chunks = chunk_text(text, rel)
        if not file_chunks:
            continue
        collection.add(
            ids=[chunk["id"] for chunk in file_chunks],
            embeddings=[embed_text(chunk["text"]) for chunk in file_chunks],
            documents=[chunk["text"] for chunk in file_chunks],
            metadatas=[
                {
                    "source": chunk["source"],
                    "start_word": chunk["start_word"],
                    "index": chunk["index"],
                }
                for chunk in file_chunks
            ],
        )
        registry[rel] = fingerprint
        files += 1
        chunks += len(file_chunks)

    _save_ingested(registry)
    return {"files": files, "chunks": chunks}

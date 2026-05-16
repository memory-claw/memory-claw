"""Text extraction for supported demo document formats."""

from __future__ import annotations

from pathlib import Path


def load_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            import pymupdf4llm
        except ImportError as exc:  # pragma: no cover - dependency exists in normal env
            raise RuntimeError("PDF support requires pymupdf4llm") from exc
        return str(pymupdf4llm.to_markdown(str(path)))
    raise ValueError(f"Unsupported document type: {suffix}")

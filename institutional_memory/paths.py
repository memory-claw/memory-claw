"""Safe path validation for OpenClaw-facing commands."""

from __future__ import annotations

from pathlib import Path

from institutional_memory.config import COMPANY_CORPUS_PATH, COMPANY_INBOX_PATH, PROJECT_ROOT, RUNTIME_PATH


class PathNotAllowedError(ValueError):
    """Raised when an OpenClaw-facing file path escapes an allowed directory."""


def _resolve_under_project(raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate.resolve()
    return (PROJECT_ROOT / candidate).resolve()


def _ensure_under(candidate: Path, allowed_root: Path, raw: str) -> Path:
    allowed = allowed_root.resolve()
    if candidate != allowed and allowed not in candidate.parents:
        raise PathNotAllowedError(
            f"Path '{raw}' is outside {allowed_root.relative_to(PROJECT_ROOT)}"
        )
    return candidate


def safe_inbox_path(raw: str) -> Path:
    candidate = _ensure_under(_resolve_under_project(raw), COMPANY_INBOX_PATH, raw)
    if candidate.suffix.lower() not in {".txt", ".md", ".pdf"}:
        raise PathNotAllowedError("Only .txt, .md, and .pdf files are allowed")
    return candidate


def safe_corpus_path(raw: str) -> Path:
    candidate = _ensure_under(_resolve_under_project(raw), COMPANY_CORPUS_PATH, raw)
    if candidate.suffix.lower() not in {".txt", ".md", ".pdf"}:
        raise PathNotAllowedError("Only .txt, .md, and .pdf corpus files are allowed")
    return candidate


def safe_runtime_path(raw: str) -> Path:
    return _ensure_under(_resolve_under_project(raw), RUNTIME_PATH, raw)

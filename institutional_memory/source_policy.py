"""Manual source access policy for Slack replies."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from institutional_memory.config import PROJECT_ROOT, SOURCE_POLICY_PATH
from institutional_memory.documents import load_document_text

AccessLevel = Literal["restricted", "cite_only", "excerpt", "share"]
VALID_ACCESS: set[str] = {"restricted", "cite_only", "excerpt", "share"}
_COMMAND_RE = re.compile(r"^(show source|show full source) ([1-9][0-9]*)$")
MAX_FULL_SOURCE_CHARS = 8000


@dataclass(frozen=True)
class SourceCommand:
    kind: Literal["excerpt", "full"]
    index: int


@dataclass(frozen=True)
class SourcePolicy:
    default: AccessLevel = "restricted"
    rules: list[tuple[str, AccessLevel]] | None = None

    def access_for(self, source: str) -> AccessLevel:
        access = self.default
        for pattern, rule_access in self.rules or []:
            if fnmatch.fnmatch(source, pattern):
                access = rule_access
        return access


def load_source_policy(path: Path = SOURCE_POLICY_PATH) -> SourcePolicy:
    if not path.exists():
        return SourcePolicy()

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default = _validate_access(data.get("default", "restricted"))
    rules = [_validate_rule(rule) for rule in data.get("rules", []) or []]
    return SourcePolicy(default=default, rules=rules)


def display_name(source: str) -> str:
    return Path(source).name


def apply_source_policy(hits: list[dict[str, Any]], policy: SourcePolicy) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    for hit in hits:
        source = str(hit.get("source", ""))
        access = policy.access_for(source)
        if access == "restricted":
            continue

        copied = dict(hit)
        copied["access"] = access
        copied["display_name"] = display_name(source)
        if access == "cite_only":
            copied["text"] = ""
        visible.append(copied)
    return visible


def parse_source_command(text: str) -> SourceCommand | None:
    normalized = " ".join(text.strip().lower().split())
    match = _COMMAND_RE.fullmatch(normalized)
    if not match:
        return None
    kind = "full" if match.group(1) == "show full source" else "excerpt"
    return SourceCommand(kind=kind, index=int(match.group(2)))


def render_source_command(command: SourceCommand, refs: list[dict[str, Any]]) -> dict[str, str]:
    ref_index = command.index - 1
    if ref_index < 0 or ref_index >= len(refs):
        return {
            "status": "missing",
            "text": f"I do not have source {command.index} in the recent source list.",
        }

    ref = refs[ref_index]
    source = str(ref.get("source", ""))
    name = display_name(source)
    access = ref.get("access", "restricted")
    if access == "restricted":
        return {
            "status": "missing",
            "text": f"I do not have source {command.index} available for Slack.",
        }
    if access == "cite_only":
        return {
            "status": "refused",
            "text": f"I can cite {name}, but policy does not allow showing its text in Slack.",
        }
    if command.kind == "full" and access != "share":
        return {
            "status": "refused",
            "text": f"{name} can be excerpted, but policy does not allow showing the full document in Slack.",
        }

    if command.kind == "excerpt":
        text = str(ref.get("text", "")).strip()
        if not text:
            return {"status": "missing", "text": f"I do not have an excerpt for {name}."}
        return {"status": "ok", "text": f"Source {command.index}: {name}\n\n> {text}"}

    path = _safe_source_path(source)
    if not path.exists():
        return {"status": "missing", "text": f"I could not find {name} on disk."}
    text = _truncate_full_text(load_document_text(path)).strip()
    return {"status": "ok", "text": f"Full source {command.index}: {name}\n\n{text}"}


def _validate_rule(rule: Any) -> tuple[str, AccessLevel]:
    if not isinstance(rule, dict):
        raise ValueError("source policy rules must be mappings")
    pattern = rule.get("pattern")
    if not pattern:
        raise ValueError("source policy rule missing pattern")
    return (str(pattern), _validate_access(rule.get("access", "restricted")))


def _validate_access(access: Any) -> AccessLevel:
    text = str(access or "").strip()
    if text not in VALID_ACCESS:
        raise ValueError(f"invalid source policy access: {access}")
    return text  # type: ignore[return-value]


def _truncate_full_text(text: str) -> str:
    if len(text) <= MAX_FULL_SOURCE_CHARS:
        return text
    return text[:MAX_FULL_SOURCE_CHARS].rstrip() + "\n\n[truncated]"


def _safe_source_path(source: str) -> Path:
    relative = Path(source)
    if relative.is_absolute():
        raise ValueError("source must be project-relative")

    path = (PROJECT_ROOT / relative).resolve()
    corpus = (PROJECT_ROOT / "company" / "corpus").resolve()
    if corpus not in path.parents and path != corpus:
        raise ValueError("source escapes company corpus")
    return path

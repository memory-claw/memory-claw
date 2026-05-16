# Better Slack Responses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build grounded, source-aware Slack replies with per-thread advice toggles, precedent comparisons, and policy-controlled source display.

**Architecture:** Add `source_policy.py` to decide which retrieved sources can be cited, excerpted, or fully shown before any LLM sees them. Add `response_composer.py` to classify intent, build deterministic fallback replies, and optionally call Ollama. Keep Slack event orchestration in `listener.py`, adding in-memory per-thread state for advice mode, footer display, source references, and source command cooldowns.

**Tech Stack:** Python 3.12, pytest, slack-sdk test doubles, Ollama Python client, PyYAML already present transitively but made explicit in `pyproject.toml`.

---

## File Map

- Create `institutional_memory/source_policy.py`
  - Loads `company/corpus/.source_policy.yml`.
  - Applies source access levels before composition.
  - Parses `show source N` and `show full source N`.
  - Renders source excerpts/full source responses deterministically.
- Create `institutional_memory/response_composer.py`
  - Detects response intent and advice commands.
  - Builds fallback Slack responses.
  - Builds first-reply action footers from advice mode and source policy.
  - Calls Ollama with a bounded prompt and falls back on error.
- Modify `institutional_memory/listener.py`
  - Adds thread state fields.
  - Refactors thread context building so retrieval and composition share one context window.
  - Handles advice toggles and source display commands before search.
  - Applies source policy before composition.
- Modify `institutional_memory/config.py`
  - Adds response model, response timeout, and source policy path config.
- Modify `.env.example`
  - Documents response generation config.
- Modify `pyproject.toml`
  - Adds explicit `pyyaml>=6.0.3`.
- Create `company/corpus/.source_policy.yml`
  - Demo policy: default restricted, broad mock corpus share, specific cite-only/restricted examples.
- Create `tests/test_source_policy.py`
  - Unit coverage for policy matching, filtering, source command parsing, and source rendering.
- Create `tests/test_response_composer.py`
  - Unit coverage for intent detection, advice command detection, fallback replies, footers, and Ollama fallback.
- Modify `tests/test_listener.py`
  - Adds listener orchestration tests for advice toggles, source commands, context cap, and full mocked integration.

---

### Task 1: Source Policy Foundation

**Files:**
- Create: `institutional_memory/source_policy.py`
- Create: `tests/test_source_policy.py`
- Create: `company/corpus/.source_policy.yml`
- Modify: `institutional_memory/config.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing source policy tests**

Create `tests/test_source_policy.py` with these tests:

```python
from pathlib import Path

from institutional_memory.source_policy import (
    SourcePolicy,
    apply_source_policy,
    parse_source_command,
    render_source_command,
)


def test_policy_unmatched_defaults_restricted():
    policy = SourcePolicy(default="restricted", rules=[])
    assert policy.access_for("company/corpus/new_doc.md") == "restricted"


def test_policy_last_match_wins():
    policy = SourcePolicy(
        default="restricted",
        rules=[
            ("company/corpus/mock_data/**", "share"),
            ("company/corpus/mock_data/policy_docs/Secrets_Management_Policy.md", "cite_only"),
        ],
    )
    assert policy.access_for("company/corpus/mock_data/slack_threads/Vantara.md") == "share"
    assert (
        policy.access_for("company/corpus/mock_data/policy_docs/Secrets_Management_Policy.md")
        == "cite_only"
    )


def test_apply_policy_filters_restricted_and_strips_cite_only_text():
    policy = SourcePolicy(
        default="restricted",
        rules=[
            ("company/corpus/share.md", "share"),
            ("company/corpus/cite.md", "cite_only"),
            ("company/corpus/restricted.md", "restricted"),
        ],
    )
    hits = [
        {"source": "company/corpus/share.md", "score": 0.91, "text": "share text"},
        {"source": "company/corpus/cite.md", "score": 0.82, "text": "secret text"},
        {"source": "company/corpus/restricted.md", "score": 0.77, "text": "hidden text"},
    ]
    filtered = apply_source_policy(hits, policy)
    assert [hit["source"] for hit in filtered] == [
        "company/corpus/share.md",
        "company/corpus/cite.md",
    ]
    assert filtered[0]["access"] == "share"
    assert filtered[0]["text"] == "share text"
    assert filtered[1]["access"] == "cite_only"
    assert filtered[1]["text"] == ""


def test_parse_source_commands():
    assert parse_source_command("show source 1").kind == "excerpt"
    assert parse_source_command("show source 1").index == 1
    assert parse_source_command("show full source 2").kind == "full"
    assert parse_source_command("show full source 2").index == 2
    assert parse_source_command("show me stuff") is None


def test_render_source_command_for_excerpt_and_share(tmp_path, monkeypatch):
    source = tmp_path / "company" / "corpus" / "doc.md"
    source.parent.mkdir(parents=True)
    source.write_text("Line one.\nLine two.\nLine three.", encoding="utf-8")
    monkeypatch.setattr("institutional_memory.source_policy.PROJECT_ROOT", tmp_path)

    refs = [{"source": "company/corpus/doc.md", "access": "share", "text": "Relevant excerpt"}]

    excerpt = render_source_command(parse_source_command("show source 1"), refs)
    assert "Relevant excerpt" in excerpt["text"]
    assert excerpt["status"] == "ok"

    full = render_source_command(parse_source_command("show full source 1"), refs)
    assert "Line one" in full["text"]
    assert full["status"] == "ok"


def test_render_source_command_refuses_cite_only_and_invalid_index():
    refs = [{"source": "company/corpus/legal.md", "access": "cite_only", "text": ""}]

    cite_only = render_source_command(parse_source_command("show source 1"), refs)
    assert cite_only["status"] == "refused"
    assert "can cite" in cite_only["text"].lower()

    missing = render_source_command(parse_source_command("show source 2"), refs)
    assert missing["status"] == "missing"
    assert "source 2" in missing["text"].lower()
```

- [ ] **Step 2: Run source policy tests to verify failure**

Run:

```bash
uv run pytest tests/test_source_policy.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'institutional_memory.source_policy'`.

- [ ] **Step 3: Add config and explicit dependency**

In `institutional_memory/config.py`, add after `COMPANY_CORPUS_PATH`:

```python
SOURCE_POLICY_PATH = COMPANY_CORPUS_PATH / ".source_policy.yml"
```

In `institutional_memory/config.py`, add near listener thresholds:

```python
RESPONSE_MODEL = os.getenv("RESPONSE_MODEL", "qwen2.5:7b-instruct")
RESPONSE_TIMEOUT_SECONDS = float(os.getenv("RESPONSE_TIMEOUT_SECONDS", "15"))
```

In `pyproject.toml`, add to `[project].dependencies`:

```toml
    "pyyaml>=6.0.3",
```

- [ ] **Step 4: Add demo source policy file**

Create `company/corpus/.source_policy.yml`:

```yaml
default: restricted
rules:
  - pattern: "company/corpus/mock_data/**"
    access: share
  - pattern: "company/corpus/2023_rfp_postmortem.txt"
    access: share
  - pattern: "company/corpus/mock_data/policy_docs/Secrets_Management_Policy.md"
    access: cite_only
  - pattern: "company/corpus/mock_data/incidents/GitHub_Credentials_Leak_2023.md"
    access: restricted
```

- [ ] **Step 5: Implement source policy module**

Create `institutional_memory/source_policy.py`:

```python
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
        access: AccessLevel = self.default
        for pattern, rule_access in self.rules or []:
            if fnmatch.fnmatch(source, pattern):
                access = rule_access
        return access


def _coerce_access(value: Any) -> AccessLevel:
    text = str(value or "").strip()
    if text not in VALID_ACCESS:
        raise ValueError(f"Invalid source access level: {text}")
    return text  # type: ignore[return-value]


def load_source_policy(path: Path = SOURCE_POLICY_PATH) -> SourcePolicy:
    if not path.exists():
        return SourcePolicy(default="restricted", rules=[])
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default = _coerce_access(payload.get("default", "restricted"))
    rules: list[tuple[str, AccessLevel]] = []
    for item in payload.get("rules", []) or []:
        pattern = str(item.get("pattern", "")).strip()
        access = _coerce_access(item.get("access", "restricted"))
        if not pattern:
            raise ValueError("Source policy rule missing pattern")
        rules.append((pattern, access))
    return SourcePolicy(default=default, rules=rules)


def display_name(source: str) -> str:
    return Path(source).name


def apply_source_policy(
    hits: list[dict[str, Any]],
    policy: SourcePolicy,
) -> list[dict[str, Any]]:
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
    normalized = " ".join(text.lower().split())
    match = re.fullmatch(r"show (full )?source (\d+)", normalized)
    if not match:
        return None
    return SourceCommand(kind="full" if match.group(1) else "excerpt", index=int(match.group(2)))


def _safe_source_path(source: str) -> Path:
    path = (PROJECT_ROOT / source).resolve()
    corpus = (PROJECT_ROOT / "company" / "corpus").resolve()
    if corpus not in path.parents and path != corpus:
        raise ValueError("Source is outside company/corpus")
    return path


def _truncate_full_text(text: str) -> str:
    if len(text) <= MAX_FULL_SOURCE_CHARS:
        return text
    return text[:MAX_FULL_SOURCE_CHARS].rstrip() + "\n\n[truncated]"


def render_source_command(
    command: SourceCommand,
    refs: list[dict[str, Any]],
) -> dict[str, str]:
    if command.index < 1 or command.index > len(refs):
        return {"status": "missing", "text": f"I do not have source {command.index} in the recent source list."}

    ref = refs[command.index - 1]
    source = str(ref.get("source", ""))
    name = display_name(source)
    access = str(ref.get("access", "restricted"))

    if access == "cite_only":
        return {"status": "refused", "text": f"I can cite {name}, but policy does not allow showing its text in Slack."}
    if access == "restricted":
        return {"status": "missing", "text": f"I do not have source {command.index} available for Slack."}
    if command.kind == "full" and access != "share":
        return {"status": "refused", "text": f"{name} can be excerpted, but policy does not allow showing the full document in Slack."}

    if command.kind == "excerpt":
        text = str(ref.get("text", "")).strip()
        if not text:
            return {"status": "missing", "text": f"I do not have an excerpt for {name}."}
        return {"status": "ok", "text": f"Source {command.index}: {name}\n\n> {text}"}

    full_text = _truncate_full_text(load_document_text(_safe_source_path(source))).strip()
    return {"status": "ok", "text": f"Full source {command.index}: {name}\n\n{full_text}"}
```

- [ ] **Step 6: Run source policy tests**

Run:

```bash
uv run pytest tests/test_source_policy.py -v
```

Expected: all tests in `tests/test_source_policy.py` pass.

- [ ] **Step 7: Commit source policy foundation**

Run:

```bash
git add pyproject.toml institutional_memory/config.py institutional_memory/source_policy.py tests/test_source_policy.py company/corpus/.source_policy.yml
git commit -m "feat: add slack source policy"
```

---

### Task 2: Response Composer Foundation

**Files:**
- Create: `institutional_memory/response_composer.py`
- Create: `tests/test_response_composer.py`

- [ ] **Step 1: Write failing response composer tests**

Create `tests/test_response_composer.py`:

```python
from unittest.mock import MagicMock, patch

from institutional_memory.response_composer import (
    compose_fallback_answer,
    compose_slack_answer,
    detect_response_intent,
    detect_thread_advice_command,
    should_accept_advice_offer,
)


def _hit(source="company/corpus/mock_data/drafts/Vantara_Proposal_Draft_v0.1.md", access="share"):
    return {
        "source": source,
        "display_name": source.rsplit("/", 1)[-1],
        "score": 0.76,
        "text": "Vantara wants custom SSO and white-label. Engineering review is needed before timeline commitment.",
        "access": access,
    }


def test_detect_response_intent_advice_and_precedent():
    assert detect_response_intent("any tips on our next move?") == "advice"
    assert detect_response_intent("compare this to precedent") == "precedent"
    assert detect_response_intent("interesting, need more information") == "context"


def test_detect_thread_advice_command():
    assert detect_thread_advice_command("advice on") == "on"
    assert detect_thread_advice_command("advice off") == "off"
    assert detect_thread_advice_command("advice offer") == "offer"
    assert detect_thread_advice_command("advice please") is None


def test_short_yes_no_only_accept_pending_offer():
    assert should_accept_advice_offer("yes", pending_offer=True) == "on"
    assert should_accept_advice_offer("go ahead", pending_offer=True) == "on"
    assert should_accept_advice_offer("no", pending_offer=True) == "off"
    assert should_accept_advice_offer("yes", pending_offer=False) is None


def test_fallback_context_with_footer_and_sources():
    text = compose_fallback_answer(
        current_text="need more information",
        thread_context="Vantara deal thread",
        hits=[_hit()],
        intent="context",
        advice_mode="offer",
        include_footer=True,
    )
    assert "What memory says" in text
    assert "Vantara wants custom SSO" in text
    assert "Sources" in text
    assert "Vantara_Proposal_Draft_v0.1.md (76%)" in text
    assert 'reply "advice"' in text


def test_fallback_advice_includes_next_move():
    text = compose_fallback_answer(
        current_text="any tips?",
        thread_context="Vantara deal thread",
        hits=[_hit()],
        intent="advice",
        advice_mode="offer",
        include_footer=False,
    )
    assert "Suggested next move" in text
    assert "confirm" in text.lower() or "review" in text.lower()


def test_fallback_precedent_shape():
    text = compose_fallback_answer(
        current_text="compare this to precedent",
        thread_context="Vantara deal thread",
        hits=[_hit()],
        intent="precedent",
        advice_mode="off",
        include_footer=False,
    )
    assert "Closest precedent" in text
    assert "Similarity" in text
    assert "Difference" in text
    assert "Lesson" in text


def test_compose_slack_answer_falls_back_when_ollama_fails():
    with patch("institutional_memory.response_composer.ollama.Client") as client_cls:
        client_cls.return_value.chat = MagicMock(side_effect=Exception("ollama down"))
        text = compose_slack_answer(
            current_text="need more information",
            thread_context="Vantara deal thread",
            hits=[_hit()],
            intent="context",
            advice_mode="offer",
            include_footer=False,
        )
    assert "What memory says" in text


def test_compose_slack_answer_uses_model_text_when_valid():
    with patch("institutional_memory.response_composer.ollama.Client") as client_cls:
        client_cls.return_value.chat.return_value = {
            "message": {"content": "What memory says:\n- Model answer\n\nSources:\n- doc.md (76%)"}
        }
        text = compose_slack_answer(
            current_text="need more information",
            thread_context="Vantara deal thread",
            hits=[_hit()],
            intent="context",
            advice_mode="offer",
            include_footer=False,
        )
    assert "Model answer" in text
```

- [ ] **Step 2: Run response composer tests to verify failure**

Run:

```bash
uv run pytest tests/test_response_composer.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'institutional_memory.response_composer'`.

- [ ] **Step 3: Implement response composer module**

Create `institutional_memory/response_composer.py`:

```python
"""Slack response composition for grounded memory replies."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import ollama

from institutional_memory.config import OLLAMA_BASE_URL, RESPONSE_MODEL, RESPONSE_TIMEOUT_SECONDS

ResponseIntent = Literal["context", "advice", "precedent"]
AdviceMode = Literal["offer", "on", "off"]

MAX_SNIPPET_CHARS = 220
MAX_MODEL_REPLY_CHARS = 3000

ADVICE_TERMS = ("advice", "tips", "next move", "should we", "recommend", "what should")
PRECEDENT_TERMS = ("precedent", "last time", "similar prior", "previous example", "happened before")


def _clean(text: str) -> str:
    return " ".join(str(text or "").split())


def _truncate(text: str, max_chars: int = MAX_SNIPPET_CHARS) -> str:
    cleaned = _clean(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def detect_response_intent(text: str) -> ResponseIntent:
    normalized = _clean(text).lower()
    if any(term in normalized for term in PRECEDENT_TERMS):
        return "precedent"
    if any(term in normalized for term in ADVICE_TERMS):
        return "advice"
    return "context"


def detect_thread_advice_command(text: str) -> AdviceMode | None:
    normalized = _clean(text).lower()
    if normalized in {"advice on", "advice: on"}:
        return "on"
    if normalized in {"advice off", "advice: off"}:
        return "off"
    if normalized in {"advice offer", "advice: offer"}:
        return "offer"
    return None


def should_accept_advice_offer(text: str, pending_offer: bool) -> AdviceMode | None:
    if not pending_offer:
        return None
    normalized = _clean(text).lower()
    if normalized in {"yes", "yep", "yeah", "go ahead", "please do"}:
        return "on"
    if normalized in {"no", "nope", "no advice"}:
        return "off"
    return None


def _score(hit: dict[str, Any]) -> int:
    return round(float(hit.get("score", 0.0)) * 100)


def _source_line(index: int, hit: dict[str, Any]) -> str:
    name = str(hit.get("display_name") or Path(str(hit.get("source", ""))).name)
    return f"{index}. {name} ({_score(hit)}%)"


def _footer(hits: list[dict[str, Any]], advice_mode: AdviceMode, include_footer: bool) -> str:
    if not include_footer:
        return ""
    commands: list[str] = []
    if advice_mode == "offer":
        commands.append('"advice"')
    if any(hit.get("access") in {"excerpt", "share"} for hit in hits):
        commands.append('"show source 1"')
    if any(hit.get("access") == "share" for hit in hits):
        commands.append('"show full source 1"')
    if not commands:
        return ""
    return "\n\nNext: reply " + ", ".join(commands[:-1] + ([f"or {commands[-1]}"] if len(commands) > 1 else commands[-1:])) + "."


def _context_section(hits: list[dict[str, Any]]) -> str:
    lines = ["What memory says:"]
    for hit in hits[:3]:
        text = _truncate(str(hit.get("text", "")))
        if text:
            lines.append(f"- {text}")
        else:
            lines.append(f"- {Path(str(hit.get('source', 'source'))).name} is relevant, but policy only allows citation.")
    return "\n".join(lines)


def _advice_section(hits: list[dict[str, Any]]) -> str:
    text = _truncate(" ".join(str(hit.get("text", "")) for hit in hits[:2]), 280)
    if text:
        return f"Suggested next move:\nConfirm the risky details called out in prior memory before committing. Grounding: {text}"
    return "Suggested next move:\nUse the cited source as a pointer, but review it outside Slack before committing."


def _precedent_section(hits: list[dict[str, Any]]) -> str:
    top = hits[0] if hits else {}
    text = _truncate(str(top.get("text", "")), 260)
    return (
        "Closest precedent:\n"
        f"- Similarity: {text or 'The cited source appears related to the current thread.'}\n"
        "- Difference: current details may differ; verify scope, owner, and timeline before treating this as the same case.\n"
        "- Lesson: use the precedent as a check against repeating earlier process or commitment mistakes."
    )


def _sources_section(hits: list[dict[str, Any]]) -> str:
    lines = ["Sources:"]
    for index, hit in enumerate(hits[:3], start=1):
        lines.append(f"- {_source_line(index, hit)}")
    return "\n".join(lines)


def compose_fallback_answer(
    *,
    current_text: str,
    thread_context: str,
    hits: list[dict[str, Any]],
    intent: ResponseIntent,
    advice_mode: AdviceMode,
    include_footer: bool,
) -> str:
    sections = [_context_section(hits)]
    if intent == "precedent":
        sections.append(_precedent_section(hits))
    if intent == "advice" or advice_mode == "on":
        sections.append(_advice_section(hits))
    sections.append(_sources_section(hits))
    return "\n\n".join(sections) + _footer(hits, advice_mode, include_footer)


def _prompt(
    *,
    current_text: str,
    thread_context: str,
    hits: list[dict[str, Any]],
    intent: ResponseIntent,
    advice_mode: AdviceMode,
    include_footer: bool,
) -> str:
    memory = "\n\n".join(
        f"Source {index}: {Path(str(hit.get('source', 'source'))).name} ({_score(hit)}%)\n{str(hit.get('text', ''))}"
        for index, hit in enumerate(hits[:3], start=1)
        if str(hit.get("text", "")).strip()
    )
    return (
        "Write a concise Slack reply grounded only in the provided thread context and memory excerpts.\n"
        "Do not invent facts, dates, owners, or commitments.\n"
        f"Intent: {intent}\n"
        f"Advice mode: {advice_mode}\n"
        f"Include footer: {include_footer}\n"
        "For precedent intent, include Similarity, Difference, and Lesson.\n"
        "Always include source filenames and scores.\n\n"
        f"Current message:\n{current_text}\n\n"
        f"Thread context:\n{thread_context}\n\n"
        f"Memory excerpts:\n{memory}"
    )


def _assistant_text(response: dict[str, Any]) -> str:
    return str((response.get("message") or {}).get("content", "")).strip()


def compose_slack_answer(
    *,
    current_text: str,
    thread_context: str,
    hits: list[dict[str, Any]],
    intent: ResponseIntent,
    advice_mode: AdviceMode,
    include_footer: bool,
) -> str:
    fallback = compose_fallback_answer(
        current_text=current_text,
        thread_context=thread_context,
        hits=hits,
        intent=intent,
        advice_mode=advice_mode,
        include_footer=include_footer,
    )
    try:
        response = ollama.Client(host=OLLAMA_BASE_URL, timeout=RESPONSE_TIMEOUT_SECONDS).chat(
            model=RESPONSE_MODEL,
            messages=[{"role": "user", "content": _prompt(
                current_text=current_text,
                thread_context=thread_context,
                hits=hits,
                intent=intent,
                advice_mode=advice_mode,
                include_footer=include_footer,
            )}],
        )
    except Exception:
        return fallback
    text = _assistant_text(response)
    if not text:
        return fallback
    if len(text) > MAX_MODEL_REPLY_CHARS:
        return text[:MAX_MODEL_REPLY_CHARS].rstrip() + "\n\n[truncated]"
    return text
```

- [ ] **Step 4: Run response composer tests**

Run:

```bash
uv run pytest tests/test_response_composer.py -v
```

Expected: all tests in `tests/test_response_composer.py` pass.

- [ ] **Step 5: Commit response composer foundation**

Run:

```bash
git add institutional_memory/response_composer.py tests/test_response_composer.py
git commit -m "feat: compose smarter slack replies"
```

---

### Task 3: Thread Context Refactor

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

- [ ] **Step 1: Add failing thread context tests**

Append to `tests/test_listener.py`:

```python
from institutional_memory.listener import build_thread_context


def test_thread_context_prefers_recent_human_messages():
    event = {"channel": "C123", "text": "latest", "ts": "11.0", "thread_ts": "1.0"}
    replies = [{"user": "U123", "text": f"message {i}"} for i in range(12)]
    client = FakeRepliesClient(replies)
    context = build_thread_context(event, bot_user_id="U999", client=client, limit=10, max_chars=2000)
    assert "message 0" not in context
    assert "message 11" in context


def test_thread_context_caps_at_2000_chars_and_filters_bots():
    event = {"channel": "C123", "text": "latest", "ts": "2.0", "thread_ts": "1.0"}
    replies = [
        {"bot_id": "B456", "text": "bot noise"},
        {"user": "U123", "text": "x" * 3000},
    ]
    client = FakeRepliesClient(replies)
    context = build_thread_context(event, bot_user_id="U999", client=client, limit=10, max_chars=2000)
    assert "bot noise" not in context
    assert len(context) == 2000
```

- [ ] **Step 2: Run new thread context tests to verify failure**

Run:

```bash
uv run pytest tests/test_listener.py::test_thread_context_prefers_recent_human_messages tests/test_listener.py::test_thread_context_caps_at_2000_chars_and_filters_bots -v
```

Expected: fail with `ImportError` for `build_thread_context`.

- [ ] **Step 3: Implement shared thread context helper**

In `institutional_memory/listener.py`, add after `_is_bot_message`:

```python
def build_thread_context(
    event: dict[str, Any],
    bot_user_id: str,
    client: Any,
    limit: int = 10,
    max_chars: int = 2000,
) -> str:
    thread_ts = event.get("thread_ts")
    if not thread_ts or client is None:
        return ""

    try:
        response = client.conversations_replies(channel=event["channel"], ts=thread_ts, limit=limit)
        messages = response.get("messages", [])
    except Exception:
        return ""

    human_texts: list[str] = []
    for msg in messages:
        if _is_bot_message(msg, bot_user_id):
            continue
        msg_text = strip_mention(str(msg.get("text", "")), bot_user_id).strip()
        if msg_text:
            human_texts.append(msg_text)

    recent = human_texts[-limit:]
    context = "\n".join(recent)
    if len(context) <= max_chars:
        return context
    return context[-max_chars:]
```

Replace the body of `build_search_query()` with:

```python
def build_search_query(
    event: dict[str, Any],
    bot_user_id: str,
    client: Any,
) -> str:
    text = strip_mention(str(event.get("text", "")), bot_user_id)
    context = build_thread_context(event, bot_user_id=bot_user_id, client=client)
    if context:
        return f"{context}\n\n{text}"
    return text
```

- [ ] **Step 4: Run listener tests for query/context**

Run:

```bash
uv run pytest tests/test_listener.py::test_query_thread_includes_human_context tests/test_listener.py::test_query_thread_filters_bot_id_messages tests/test_listener.py::test_query_thread_caps_context_at_2000_chars tests/test_thread_context_prefers_recent_human_messages tests/test_thread_context_caps_at_2000_chars_and_filters_bots -v
```

Expected: selected tests pass. If `test_query_thread_caps_context_at_2000_chars` expects `<= 2100`, keep it passing because query contains the capped context plus current message.

- [ ] **Step 5: Commit thread context refactor**

Run:

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "refactor: share slack thread context window"
```

---

### Task 4: Listener Advice Modes and Footer State

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

- [ ] **Step 1: Add failing advice state tests**

Append to `tests/test_listener.py`:

```python
def test_advice_on_command_updates_thread_mode_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "advice on"}

    with patch("institutional_memory.listener.search_memory") as search:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert state.thread_advice_modes[("C100", "1.0")] == "on"
    assert "advice mode is on" in client.posted[0]["text"].lower()
    search.assert_not_called()


def test_short_yes_requires_pending_offer():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "yes"}

    with patch("institutional_memory.listener.search_memory", return_value=[]):
        with patch("institutional_memory.listener.log_event"):
            handle_listener_event(event, client, state)

    assert ("C100", "1.0") not in state.thread_advice_modes


def test_short_yes_after_pending_offer_sets_advice_on_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_advice_offer_pending.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "yes"}

    with patch("institutional_memory.listener.search_memory") as search:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert state.thread_advice_modes[("C100", "1.0")] == "on"
    search.assert_not_called()
```

- [ ] **Step 2: Run advice tests to verify failure**

Run:

```bash
uv run pytest tests/test_listener.py::test_advice_on_command_updates_thread_mode_without_search tests/test_listener.py::test_short_yes_requires_pending_offer tests/test_listener.py::test_short_yes_after_pending_offer_sets_advice_on_without_search -v
```

Expected: fail because `ListenerState` lacks advice state fields and command handling.

- [ ] **Step 3: Add listener state fields and advice command handling**

In `institutional_memory/listener.py`, add imports:

```python
from institutional_memory.response_composer import (
    detect_response_intent,
    detect_thread_advice_command,
    should_accept_advice_offer,
)
```

Extend `ListenerState`:

```python
@dataclass
class ListenerState:
    bot_user_id: str
    allowed_channels: set[str]
    dedupe: DedupeSet
    active_threads: set[tuple[str, str]] = field(default_factory=set)
    thread_advice_modes: dict[tuple[str, str], str] = field(default_factory=dict)
    thread_footer_shown: set[tuple[str, str]] = field(default_factory=set)
    thread_advice_offer_pending: set[tuple[str, str]] = field(default_factory=set)
    thread_source_refs: dict[tuple[str, str], list[dict[str, Any]]] = field(default_factory=dict)
    thread_full_source_cooldowns: dict[tuple[str, str, int], float] = field(default_factory=dict)
```

Add helper functions before `handle_listener_event()`:

```python
def _thread_key(channel: str, thread_ts: str) -> tuple[str, str]:
    return (channel, thread_ts)


def _advice_mode_reply(mode: str) -> str:
    return f"Advice mode is {mode} for this thread."


def _handle_advice_mode_command(
    text: str,
    key: tuple[str, str],
    state: ListenerState,
) -> str | None:
    explicit = detect_thread_advice_command(text)
    if explicit is not None:
        state.thread_advice_modes[key] = explicit
        state.thread_advice_offer_pending.discard(key)
        return _advice_mode_reply(explicit)

    accepted = should_accept_advice_offer(text, pending_offer=key in state.thread_advice_offer_pending)
    if accepted is not None:
        state.thread_advice_modes[key] = accepted
        state.thread_advice_offer_pending.discard(key)
        return _advice_mode_reply(accepted)

    return None
```

In `handle_listener_event()`, after `is_mention` and `is_active_thread` are computed and after allowlist check is satisfied, insert:

```python
    key = _thread_key(channel, thread_ts)
    advice_reply = _handle_advice_mode_command(str(event.get("text", "")), key, state)
    if advice_reply is not None:
        try:
            client.chat_postMessage(channel=channel, text=advice_reply, thread_ts=thread_ts)
            log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="thread", response_intent="toggle", advice_mode=state.thread_advice_modes.get(key, "offer"))
            return {"status": "replied", "hits": 0, "triggered_by": "thread"}
        except Exception as exc:
            log_event("listener_error", channel=channel, error=str(exc))
            return {"status": "error", "error": str(exc)}
```

- [ ] **Step 4: Run advice state tests**

Run:

```bash
uv run pytest tests/test_listener.py::test_advice_on_command_updates_thread_mode_without_search tests/test_listener.py::test_short_yes_requires_pending_offer tests/test_listener.py::test_short_yes_after_pending_offer_sets_advice_on_without_search -v
```

Expected: selected tests pass.

- [ ] **Step 5: Commit advice mode integration**

Run:

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add thread advice modes"
```

---

### Task 5: Source Display Commands in Listener

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

- [ ] **Step 1: Add failing source command listener tests**

Append to `tests/test_listener.py`:

```python
def test_show_source_uses_recent_thread_refs_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_source_refs[("C100", "1.0")] = [
        {"source": "company/corpus/doc.md", "display_name": "doc.md", "access": "share", "text": "Relevant excerpt"}
    ]
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "show source 1"}

    with patch("institutional_memory.listener.search_memory") as search:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "Relevant excerpt" in client.posted[0]["text"]
    search.assert_not_called()


def test_show_source_without_recent_refs_replies_missing():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "show source 1"}

    with patch("institutional_memory.listener.search_memory") as search:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "recent source list" in client.posted[0]["text"].lower()
    search.assert_not_called()


def test_show_full_source_cooldown():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_source_refs[("C100", "1.0")] = [
        {"source": "company/corpus/doc.md", "display_name": "doc.md", "access": "share", "text": "Relevant excerpt"}
    ]
    state.thread_full_source_cooldowns[("C100", "1.0", 1)] = time.monotonic()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "show full source 1"}

    with patch("institutional_memory.listener.search_memory") as search:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "wait" in client.posted[0]["text"].lower()
    search.assert_not_called()
```

- [ ] **Step 2: Run source command listener tests to verify failure**

Run:

```bash
uv run pytest tests/test_listener.py::test_show_source_uses_recent_thread_refs_without_search tests/test_listener.py::test_show_source_without_recent_refs_replies_missing tests/test_listener.py::test_show_full_source_cooldown -v
```

Expected: fail because listener does not parse source commands.

- [ ] **Step 3: Add source command handling**

In `institutional_memory/listener.py`, add imports:

```python
from institutional_memory.source_policy import parse_source_command, render_source_command
```

Add helper:

```python
FULL_SOURCE_COOLDOWN_SECONDS = 30.0


def _handle_source_command(
    text: str,
    key: tuple[str, str],
    state: ListenerState,
) -> str | None:
    command = parse_source_command(text)
    if command is None:
        return None
    refs = state.thread_source_refs.get(key)
    if not refs:
        return "I do not have a recent source list for this thread."
    if command.kind == "full":
        cooldown_key = (key[0], key[1], command.index)
        now = time.monotonic()
        previous = state.thread_full_source_cooldowns.get(cooldown_key)
        if previous is not None and now - previous < FULL_SOURCE_COOLDOWN_SECONDS:
            return "Please wait before asking me to repost that full source again."
        state.thread_full_source_cooldowns[cooldown_key] = now
    return render_source_command(command, refs)["text"]
```

In `handle_listener_event()`, after advice command handling and before search, insert:

```python
    source_reply = _handle_source_command(str(event.get("text", "")), key, state)
    if source_reply is not None:
        try:
            client.chat_postMessage(channel=channel, text=source_reply, thread_ts=thread_ts)
            log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="thread", response_intent="source", advice_mode=state.thread_advice_modes.get(key, "offer"))
            return {"status": "replied", "hits": 0, "triggered_by": "thread"}
        except Exception as exc:
            log_event("listener_error", channel=channel, error=str(exc))
            return {"status": "error", "error": str(exc)}
```

- [ ] **Step 4: Run source command listener tests**

Run:

```bash
uv run pytest tests/test_listener.py::test_show_source_uses_recent_thread_refs_without_search tests/test_listener.py::test_show_source_without_recent_refs_replies_missing tests/test_listener.py::test_show_full_source_cooldown -v
```

Expected: selected tests pass.

- [ ] **Step 5: Commit source command integration**

Run:

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: show slack response sources on request"
```

---

### Task 6: Use Composer and Policy in Normal Replies

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `.env.example`
- Modify: `tests/test_listener.py`

- [ ] **Step 1: Add failing normal reply integration tests**

Append to `tests/test_listener.py`:

```python
def test_handle_reply_uses_policy_and_composer_fallback():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "Vantara needs more info"}
    hits = [
        {"score": 0.85, "text": "Allowed memory", "source": "company/corpus/allowed.md"},
        {"score": 0.82, "text": "Hidden memory", "source": "company/corpus/hidden.md"},
    ]

    class Policy:
        def access_for(self, source):
            return "share" if source.endswith("allowed.md") else "restricted"

    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.load_source_policy", return_value=Policy()):
            with patch("institutional_memory.listener.compose_slack_answer", return_value="What memory says:\n- Allowed memory\n\nSources:\n- allowed.md (85%)") as compose:
                with patch("institutional_memory.listener.log_event"):
                    result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "Allowed memory" in client.posted[0]["text"]
    assert "Hidden memory" not in client.posted[0]["text"]
    compose.assert_called_once()
    assert state.thread_source_refs[("C100", "1.0")][0]["source"] == "company/corpus/allowed.md"


def test_offer_footer_shown_once_and_sets_pending_offer():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "Vantara needs more info"}
    hits = [{"score": 0.85, "text": "Allowed memory", "source": "company/corpus/allowed.md"}]

    class Policy:
        def access_for(self, source):
            return "share"

    def fake_compose(**kwargs):
        assert kwargs["include_footer"] is True
        return 'What memory says:\n- Allowed memory\n\nNext: reply "advice".'

    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.load_source_policy", return_value=Policy()):
            with patch("institutional_memory.listener.compose_slack_answer", side_effect=fake_compose):
                with patch("institutional_memory.listener.log_event"):
                    handle_listener_event(event, client, state)

    assert ("C100", "1.0") in state.thread_footer_shown
    assert ("C100", "1.0") in state.thread_advice_offer_pending
```

- [ ] **Step 2: Run normal reply integration tests to verify failure**

Run:

```bash
uv run pytest tests/test_listener.py::test_handle_reply_uses_policy_and_composer_fallback tests/test_listener.py::test_offer_footer_shown_once_and_sets_pending_offer -v
```

Expected: fail because listener still calls `format_reply()` directly.

- [ ] **Step 3: Wire policy and composer into listener**

In `institutional_memory/listener.py`, add imports:

```python
from institutional_memory.response_composer import compose_slack_answer
from institutional_memory.source_policy import apply_source_policy, load_source_policy
```

Replace:

```python
    reply_text = format_reply(hits)
```

with:

```python
    policy = load_source_policy()
    visible_hits = apply_source_policy(hits, policy)
    if not visible_hits:
        log_event("listener_skip", channel=channel, reason="source_policy_filtered", top_score=hits[0]["score"])
        return {"status": "skipped", "reason": "source_policy_filtered"}

    intent = detect_response_intent(str(event.get("text", "")))
    advice_mode = state.thread_advice_modes.get(key, "offer")
    include_footer = advice_mode == "offer" and key not in state.thread_footer_shown
    thread_context = build_thread_context(event, bot_user_id=state.bot_user_id, client=client)
    reply_text = compose_slack_answer(
        current_text=strip_mention(str(event.get("text", "")), state.bot_user_id),
        thread_context=thread_context,
        hits=visible_hits,
        intent=intent,
        advice_mode=advice_mode,
        include_footer=include_footer,
    )
```

After successful `chat_postMessage`, before `state.active_threads.add(...)`, add:

```python
    state.thread_source_refs[key] = visible_hits[:MAX_HITS]
    if include_footer:
        state.thread_footer_shown.add(key)
        if '"advice"' in reply_text:
            state.thread_advice_offer_pending.add(key)
```

Change source list and log fields:

```python
    sources = [h["source"] for h in visible_hits[:MAX_HITS]]
```

Add fields to `log_event()`:

```python
        response_intent=intent,
        advice_mode=advice_mode,
```

- [ ] **Step 4: Update `.env.example`**

Append:

```env
RESPONSE_MODEL=qwen2.5:7b-instruct
RESPONSE_TIMEOUT_SECONDS=15
```

- [ ] **Step 5: Run listener normal reply tests**

Run:

```bash
uv run pytest tests/test_listener.py::test_handle_reply_uses_policy_and_composer_fallback tests/test_listener.py::test_offer_footer_shown_once_and_sets_pending_offer -v
```

Expected: selected tests pass.

- [ ] **Step 6: Run full listener suite**

Run:

```bash
uv run pytest tests/test_listener.py -v
```

Expected: all listener tests pass.

- [ ] **Step 7: Commit composer/policy listener wiring**

Run:

```bash
git add institutional_memory/listener.py tests/test_listener.py .env.example
git commit -m "feat: use composer for slack listener replies"
```

---

### Task 7: Full Verification and Cleanup

**Files:**
- Modify only if verification exposes failures in files touched by earlier tasks.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
uv run pytest tests/test_source_policy.py tests/test_response_composer.py tests/test_listener.py -v
```

Expected: all targeted tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: full suite passes.

- [ ] **Step 3: Run lint-style diff check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Inspect final changed files**

Run:

```bash
git status --short
```

Expected: only intended implementation files are modified or untracked. The pre-existing untracked `docs/superpowers/plans/2026-05-16-dashboard-inbox-filter-reingest.md` may still appear and must not be staged unless the user explicitly asks.

- [ ] **Step 5: Commit final cleanup if needed**

If Step 1 or Step 2 required fixes after the last feature commit, run:

```bash
git add institutional_memory tests .env.example pyproject.toml company/corpus/.source_policy.yml
git commit -m "test: verify better slack responses"
```

Expected: commit succeeds only if there are real implementation or test changes after Task 6.

---

## Self-Review Checklist

- Source policy default remains `restricted`.
- Demo policy explicitly marks mock corpus files as `share`.
- `restricted` hits are filtered before composer or LLM prompt construction.
- `cite_only` hits keep filename/score but lose text before composer.
- Advice mode is in-memory and per thread.
- Short `yes` and `no` only affect advice mode after an advice offer footer.
- `show source N` and `show full source N` are handled before search.
- Full source display is available only for `share` sources.
- Full source display has a 30-second per-thread cooldown.
- Thread context is capped to 10 human messages and 2,000 characters.
- Normal reply path has a mocked integration test from event to Slack post.
- Ollama generation has fallback tests.

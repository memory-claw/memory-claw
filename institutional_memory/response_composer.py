"""Deterministic Slack response composition with optional Ollama polish."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import ollama

from institutional_memory.config import OLLAMA_BASE_URL, RESPONSE_MODEL, RESPONSE_TIMEOUT_SECONDS

ResponseIntent = Literal["context", "advice", "precedent"]
AdviceMode = Literal["offer", "on", "off"]

MAX_SNIPPET_CHARS = 220
MAX_MODEL_REPLY_CHARS = 3000
MAX_THREAD_TEXT_CHARS = 2000

_ADVICE_TERMS = ("advice", "tips", "next move", "should we", "recommend", "what should")
_PRECEDENT_TERMS = ("precedent", "last time", "similar prior", "previous example", "happened before")
_ADVICE_COMMANDS: dict[str, AdviceMode] = {
    "advice": "on",
    "advice on": "on",
    "advice: on": "on",
    "advice off": "off",
    "advice: off": "off",
    "advice offer": "offer",
    "advice: offer": "offer",
}
_ACCEPT_OFFER: dict[str, AdviceMode] = {
    "yes": "on",
    "yep": "on",
    "yeah": "on",
    "go ahead": "on",
    "please do": "on",
    "no": "off",
    "nope": "off",
    "no advice": "off",
}


def detect_response_intent(text: str) -> ResponseIntent:
    normalized = _normalize(text)
    if any(term in normalized for term in _PRECEDENT_TERMS):
        return "precedent"
    if any(term in normalized for term in _ADVICE_TERMS):
        return "advice"
    return "context"


def detect_thread_advice_command(text: str) -> AdviceMode | None:
    return _ADVICE_COMMANDS.get(_normalize(text))


def should_accept_advice_offer(text: str, *, pending_offer: bool) -> AdviceMode | None:
    if not pending_offer:
        return None
    return _ACCEPT_OFFER.get(_normalize(text))


def compose_fallback_answer(
    thread_text: str,
    hits: list[dict[str, Any]],
    *,
    intent: ResponseIntent | None = None,
    advice_mode: AdviceMode = "offer",
    include_footer: bool = False,
) -> str:
    resolved_intent = intent or detect_response_intent(thread_text)
    visible_hits = hits[:3]
    sections = [_context_section(visible_hits)]

    if resolved_intent == "precedent":
        sections.append(_precedent_section(visible_hits))
    if resolved_intent == "advice" or advice_mode == "on":
        sections.append(_advice_section())

    sections.append(_sources_section(visible_hits))
    if include_footer:
        footer = _footer(visible_hits, advice_mode=advice_mode)
        if footer:
            sections.append(footer)
    return "\n\n".join(section for section in sections if section)


def compose_slack_answer(
    thread_text: str,
    hits: list[dict[str, Any]],
    *,
    intent: ResponseIntent | None = None,
    advice_mode: AdviceMode = "offer",
    include_footer: bool = False,
) -> str:
    resolved_intent = intent or detect_response_intent(thread_text)
    fallback = compose_fallback_answer(
        thread_text,
        hits,
        intent=resolved_intent,
        advice_mode=advice_mode,
        include_footer=include_footer,
    )

    try:
        response = ollama.Client(host=OLLAMA_BASE_URL, timeout=RESPONSE_TIMEOUT_SECONDS).chat(
            model=RESPONSE_MODEL,
            messages=_messages(thread_text, hits[:3], resolved_intent, advice_mode),
        )
    except Exception:
        return fallback

    content = _response_content(response)
    if not content:
        return fallback
    text = _truncate_model_reply(content.strip())
    if not _has_required_source_citation(text, hits[:3]):
        return fallback
    if advice_mode == "off" and _contains_advice(text):
        return fallback
    footer = _footer(hits[:3], advice_mode=advice_mode) if include_footer else ""
    if footer and footer not in text:
        return f"{text}\n\n{footer}"
    return text


def _context_section(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "What memory says:\n- No relevant memory is available for this thread."

    bullets = []
    for hit in hits:
        name = _display_name(hit)
        text = str(hit.get("text", "")).strip()
        if text:
            bullets.append(f"- {_truncate_snippet(text)}")
        else:
            bullets.append(f"- {name} is relevant, but policy only allows citation.")
    return "What memory says:\n" + "\n".join(bullets)


def _precedent_section(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return (
            "Closest precedent:\n"
            "- Similarity: No close precedent was available.\n"
            "- Difference: Current details still need review.\n"
            "- Lesson: Confirm facts before acting."
        )

    top = hits[0]
    name = _display_name(top)
    score = _score_percent(top)
    return (
        "Closest precedent:\n"
        f"- Similarity: {name} is the closest match ({score}%).\n"
        "- Difference: Current thread may have different owners, timing, or risk level.\n"
        "- Lesson: Review the precedent before repeating the same decision."
    )


def _advice_section() -> str:
    return (
        "Suggested next move:\n"
        "- Confirm the current facts against the cited memory, then review the closest source before posting a final answer."
    )


def _sources_section(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "Sources:\nNone."
    lines = [f"{index}. {_display_name(hit)} ({_score_percent(hit)}%)" for index, hit in enumerate(hits, start=1)]
    return "Sources:\n" + "\n".join(lines)


def _footer(hits: list[dict[str, Any]], *, advice_mode: AdviceMode) -> str:
    commands: list[str] = []
    if advice_mode == "offer":
        commands.append('"advice"')
    commands.append('"compare to precedent"')

    for index, hit in enumerate(hits, start=1):
        access = str(hit.get("access", ""))
        if access in {"excerpt", "share"}:
            commands.append(f'"show source {index}"')
            break

    if not commands:
        return ""
    return "Next: try " + _join_english(commands) + "."


def _messages(
    thread_text: str,
    hits: list[dict[str, Any]],
    intent: ResponseIntent,
    advice_mode: AdviceMode,
) -> list[dict[str, str]]:
    excerpts = []
    for index, hit in enumerate(hits, start=1):
        name = _display_name(hit)
        score = _score_percent(hit)
        text = str(hit.get("text", "")).strip()
        if text:
            body = _truncate_snippet(text)
        else:
            body = f"{name} is relevant, but policy only allows citation."
        excerpts.append(f"{index}. {name} ({score}%): {body}")

    precedent_instruction = (
        " If intent is precedent, use this shape: Closest precedent, Similarity, Difference, Lesson."
        if intent == "precedent"
        else ""
    )
    return [
        {
            "role": "system",
            "content": (
                "You compose concise Slack replies for an institutional memory assistant. "
                "Ground the reply only in the provided thread context and memory excerpts. "
                "Do not invent facts. Include source filenames and scores. "
                "Do not include restricted or cite-only source text beyond the provided excerpts."
                + precedent_instruction
            ),
        },
        {
            "role": "user",
            "content": (
                f"Intent: {intent}\nAdvice mode: {advice_mode}\n\n"
                f"Thread context:\n{_truncate_thread_text(thread_text)}\n\n"
                "Memory excerpts:\n"
                + ("\n".join(excerpts) if excerpts else "No relevant memory available.")
            ),
        },
    ]


def _response_content(response: Any) -> str:
    if isinstance(response, dict):
        message = response.get("message") or {}
        if isinstance(message, dict):
            return str(message.get("content") or "")
        return str(getattr(message, "content", "") or "")

    message = getattr(response, "message", None)
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(getattr(message, "content", "") or "")


def _truncate_model_reply(text: str) -> str:
    if len(text) <= MAX_MODEL_REPLY_CHARS:
        return text
    return text[:MAX_MODEL_REPLY_CHARS].rstrip() + "\n\n[truncated]"


def _truncate_thread_text(text: str) -> str:
    collapsed = str(text or "").strip()
    if len(collapsed) <= MAX_THREAD_TEXT_CHARS:
        return collapsed
    tail = collapsed[-MAX_THREAD_TEXT_CHARS:]
    newline_index = tail.find("\n")
    if newline_index != -1:
        return tail[newline_index + 1 :]
    return tail


def _has_required_source_citation(text: str, hits: list[dict[str, Any]]) -> bool:
    if not hits:
        return True
    normalized = text.lower()
    return any(
        _display_name(hit).lower() in normalized and f"{_score_percent(hit)}%" in normalized
        for hit in hits
    )


def _contains_advice(text: str) -> bool:
    normalized = text.lower()
    advice_markers = (
        "suggested next move",
        "next move",
        "recommend",
        "you should",
        "we should",
        "should ",
        "review this before",
        "before committing",
    )
    return any(marker in normalized for marker in advice_markers)


def _truncate_snippet(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= MAX_SNIPPET_CHARS:
        return collapsed
    return collapsed[:MAX_SNIPPET_CHARS].rstrip() + "..."


def _score_percent(hit: dict[str, Any]) -> int:
    try:
        return round(float(hit.get("score", 0.0)) * 100)
    except (TypeError, ValueError):
        return 0


def _display_name(hit: dict[str, Any]) -> str:
    display = str(hit.get("display_name") or "").strip()
    if display:
        return display
    name = Path(str(hit.get("source", "unknown"))).name
    return name or "unknown"


def _join_english(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} or {items[1]}"
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())

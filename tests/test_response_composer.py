from __future__ import annotations

import pytest

from institutional_memory.response_composer import (
    MAX_MODEL_REPLY_CHARS,
    compose_fallback_answer,
    compose_slack_answer,
    detect_response_intent,
    detect_thread_advice_command,
    should_accept_advice_offer,
)


def _hit(**overrides):
    hit = {
        "source": "company/corpus/launch_review.md",
        "display_name": "launch_review.md",
        "score": 0.762,
        "text": "Team delayed broad launch until customer support reviewed the migration plan.",
        "access": "share",
    }
    hit.update(overrides)
    return hit


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("any tips on our next move?", "advice"),
        ("compare this to precedent", "precedent"),
        ("interesting, need more information", "context"),
        ("any tips from a similar prior example?", "precedent"),
    ],
)
def test_detect_response_intent(text, expected):
    assert detect_response_intent(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("advice on", "on"),
        (" advice: off ", "off"),
        ("ADVICE OFFER", "offer"),
        ("advice: offer", "offer"),
        ("advice", "on"),
        ("advice please", None),
    ],
)
def test_detect_thread_advice_command(text, expected):
    assert detect_thread_advice_command(text) == expected


@pytest.mark.parametrize(
    ("text", "pending_offer", "expected"),
    [
        ("yes", True, "on"),
        ("go ahead", True, "on"),
        ("no", True, "off"),
        ("yes", False, None),
    ],
)
def test_should_accept_advice_offer(text, pending_offer, expected):
    assert should_accept_advice_offer(text, pending_offer=pending_offer) == expected


def test_compose_fallback_answer_context_includes_memory_sources_and_footer():
    answer = compose_fallback_answer(
        "Need more information",
        [_hit()],
        intent="context",
        advice_mode="offer",
        include_footer=True,
    )

    assert "What memory says:" in answer
    assert "Team delayed broad launch until customer support reviewed the migration plan." in answer
    assert "Sources:" in answer
    assert "launch_review.md (76%)" in answer
    assert 'Next: reply "advice"' in answer
    assert "show source 1" in answer
    assert "or show full source 1" in answer


def test_compose_fallback_answer_uses_cite_only_wording_for_empty_text():
    answer = compose_fallback_answer(
        "Need more information",
        [_hit(text="", access="cite_only", display_name="policy.md", source="company/corpus/policy.md")],
        intent="context",
    )

    assert "policy.md is relevant, but policy only allows citation." in answer


def test_fallback_advice_includes_next_move_and_review_language():
    answer = compose_fallback_answer("What should we do?", [_hit()], intent="advice")

    assert "Suggested next move" in answer
    assert "confirm" in answer.lower() or "review" in answer.lower()


def test_fallback_precedent_includes_precedent_shape():
    answer = compose_fallback_answer("Compare this to precedent", [_hit()], intent="precedent")

    assert "Closest precedent" in answer
    assert "Similarity" in answer
    assert "Difference" in answer
    assert "Lesson" in answer


def test_compose_slack_answer_falls_back_when_ollama_chat_raises(monkeypatch):
    import institutional_memory.response_composer as response_composer

    class RaisingClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **_kwargs):
            raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(response_composer.ollama, "Client", RaisingClient)

    answer = compose_slack_answer("Need more information", [_hit()], intent="context")

    assert "What memory says:" in answer
    assert "launch_review.md (76%)" in answer


def test_compose_slack_answer_returns_model_text_when_present(monkeypatch):
    import institutional_memory.response_composer as response_composer

    class ContentClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **_kwargs):
            return {"message": {"content": "Model-grounded reply\n\nSources:\n1. launch_review.md (76%)"}}

    monkeypatch.setattr(response_composer.ollama, "Client", ContentClient)

    assert (
        compose_slack_answer("Need more information", [_hit()], intent="context")
        == "Model-grounded reply\n\nSources:\n1. launch_review.md (76%)"
    )


def test_compose_slack_answer_falls_back_when_model_omits_source(monkeypatch):
    import institutional_memory.response_composer as response_composer

    class UngroundedClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **_kwargs):
            return {"message": {"content": "Looks good to me."}}

    monkeypatch.setattr(response_composer.ollama, "Client", UngroundedClient)

    answer = compose_slack_answer("Need more information", [_hit()], intent="context")

    assert "What memory says:" in answer
    assert "launch_review.md (76%)" in answer


def test_compose_slack_answer_preserves_footer_on_model_response(monkeypatch):
    import institutional_memory.response_composer as response_composer

    class ContentClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **_kwargs):
            return {"message": {"content": "Model-grounded reply\n\nSources:\n1. launch_review.md (76%)"}}

    monkeypatch.setattr(response_composer.ollama, "Client", ContentClient)

    answer = compose_slack_answer("Need more information", [_hit()], intent="context", include_footer=True)

    assert "Model-grounded reply" in answer
    assert 'Next: reply "advice"' in answer


def test_compose_slack_answer_bounds_thread_text_sent_to_model(monkeypatch):
    import institutional_memory.response_composer as response_composer

    captured = {}

    class ContentClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return {"message": {"content": "Model-grounded reply\n\nSources:\n1. launch_review.md (76%)"}}

    monkeypatch.setattr(response_composer.ollama, "Client", ContentClient)

    compose_slack_answer("x" * 10_000, [_hit()], intent="context")

    user_message = captured["messages"][1]["content"]
    thread_section = user_message.split("Thread context:\n", 1)[1].split("\n\nMemory excerpts:", 1)[0]
    assert len(user_message) < 5000
    assert len(thread_section) <= response_composer.MAX_THREAD_TEXT_CHARS


def test_compose_slack_answer_truncates_long_model_text(monkeypatch):
    import institutional_memory.response_composer as response_composer

    class LongContentClient:
        def __init__(self, **_kwargs):
            pass

        def chat(self, **_kwargs):
            return {
                "message": {
                    "content": f"launch_review.md (76%)\n\n{'x' * (MAX_MODEL_REPLY_CHARS + 20)}"
                }
            }

    monkeypatch.setattr(response_composer.ollama, "Client", LongContentClient)

    answer = compose_slack_answer("Need more information", [_hit()], intent="context")

    assert len(answer) <= MAX_MODEL_REPLY_CHARS + len("\n\n[truncated]")
    assert answer.endswith("[truncated]")

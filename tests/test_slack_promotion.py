import json
from pathlib import Path

from institutional_memory import paths, slack_promotion


class FakePromotionClient:
    def __init__(self, messages=None, permalink=None):
        self.messages = messages or [
            {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
            {"ts": "1710000001.000000", "user": "U456", "text": "We decided to use the standard cap from the vendor terms playbook"},
        ]
        self.permalink = permalink or "https://example.slack.com/archives/C123/p1710000000000000"
        self.replies_calls = []
        self.history_calls = []
        self.permalink_calls = []

    def conversations_history(self, channel, latest, inclusive, limit):
        self.history_calls.append(
            {"channel": channel, "latest": latest, "inclusive": inclusive, "limit": limit}
        )
        message = next((item for item in self.messages if item.get("ts") == latest), None)
        if message is None:
            message = {"ts": latest, "user": "U123", "text": "Need precedent"}
        return {"messages": [message]}

    def conversations_replies(self, channel, ts):
        self.replies_calls.append({"channel": channel, "ts": ts})
        return {"messages": self.messages}

    def chat_getPermalink(self, channel, message_ts):
        self.permalink_calls.append({"channel": channel, "message_ts": message_ts})
        return {"permalink": self.permalink}


def _patch_promotion_paths(monkeypatch, tmp_path):
    company_corpus = tmp_path / "company" / "corpus"
    company_evidence = tmp_path / "company" / "evidence"
    monkeypatch.setattr(slack_promotion, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_promotion, "COMPANY_CORPUS_PATH", company_corpus)
    monkeypatch.setattr(slack_promotion, "COMPANY_EVIDENCE_PATH", company_evidence)
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "COMPANY_CORPUS_PATH", company_corpus)
    monkeypatch.setattr(paths, "COMPANY_EVIDENCE_PATH", company_evidence)
    return company_corpus, company_evidence


def _reaction_event(**overrides):
    event = {
        "type": "reaction_added",
        "user": "U123",
        "reaction": "memo",
        "item": {"type": "message", "channel": "C123", "ts": "1710000000.000000"},
    }
    event.update(overrides)
    return event


def test_unsupported_reaction_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(reaction="eyes"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "unsupported_reaction"}


def test_bot_reaction_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(user="UBOT"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "bot_reaction"}


def test_empty_allowlist_disables_promotion(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels=set(),
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "channel_not_allowed"}


def test_channel_outside_allowlist_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C999"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "channel_not_allowed"}


def test_approved_reaction_writes_memory_card_and_evidence(tmp_path, monkeypatch):
    company_corpus, company_evidence = _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    evidence = company_evidence / "slack" / "C123_1710000000.000000.json"
    assert card.exists()
    assert evidence.exists()
    text = card.read_text(encoding="utf-8")
    assert "# Slack Memory: Need precedent for vendor liability clause" in text
    assert "Reaction: :memo:" in text
    assert "## Outcome" in text
    assert "use the standard cap" in text
    assert "company/evidence/slack/C123_1710000000.000000.json" in text
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["channel"] == "C123"
    assert payload["thread_ts"] == "1710000000.000000"
    assert payload["messages"][0]["text"] == "Need precedent for vendor liability clause"


def test_brain_reaction_records_brain_metadata(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(reaction="brain"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "Reaction: :brain:" in card.read_text(encoding="utf-8")


def test_reaction_on_reply_promotes_parent_thread(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
        {"ts": "1710000005.000000", "thread_ts": "1710000000.000000", "user": "U456", "text": "We decided to use standard cap"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(item={"type": "message", "channel": "C123", "ts": "1710000005.000000"}),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert client.replies_calls == [{"channel": "C123", "ts": "1710000000.000000"}]
    assert (company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md").exists()


def test_existing_card_returns_exists_without_rewrite(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    card.parent.mkdir(parents=True)
    card.write_text("original", encoding="utf-8")

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(user_cooldown_seconds=999),
        bot_user_id="UBOT",
    )

    assert result["status"] == "exists"
    assert card.read_text(encoding="utf-8") == "original"


def test_missing_outcome_omits_outcome_section(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
        {"ts": "1710000001.000000", "user": "U456", "text": "I will look around"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    text = card.read_text(encoding="utf-8")
    assert "## Outcome" not in text
    assert "## Reusable Takeaway" not in text


def test_explicit_takeaway_section_is_included(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent"},
        {"ts": "1710000001.000000", "user": "U456", "text": "Takeaway: route vendor liability changes through legal first"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    text = card.read_text(encoding="utf-8")
    assert "## Reusable Takeaway" in text
    assert "route vendor liability changes through legal first" in text


def test_long_threads_use_bounded_card_window_but_full_evidence(tmp_path, monkeypatch):
    company_corpus, company_evidence = _patch_promotion_paths(monkeypatch, tmp_path)
    messages = [{"ts": "1710000000.000000", "user": "U123", "text": "Need precedent"}]
    messages.extend(
        {"ts": f"17100000{i:02d}.000000", "user": "U456", "text": f"message {i} " + ("x" * 500)}
        for i in range(20)
    )
    client = FakePromotionClient(messages=messages)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    evidence = company_evidence / "slack" / "C123_1710000000.000000.json"
    text = card.read_text(encoding="utf-8")
    assert len(text) <= 2600
    assert "## Evidence" in text
    assert "Raw Slack thread snapshot:" in text
    assert len(json.loads(evidence.read_text(encoding="utf-8"))["messages"]) == 21


def test_third_party_bot_messages_are_kept_in_card(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "bot_id": "BPAGER", "username": "PagerDuty", "text": "PagerDuty alert: checkout API latency high"},
        {"ts": "1710000001.000000", "user": "U123", "text": "We decided to roll back the checkout deploy"},
        {"ts": "1710000002.000000", "user": "UBOT", "text": "Memory Claw reply should not be indexed"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    text = card.read_text(encoding="utf-8")
    assert "PagerDuty alert" in text
    assert "roll back the checkout deploy" in text
    assert "Memory Claw reply should not be indexed" not in text


def test_related_sources_from_audit_are_best_effort(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    audit_log = tmp_path / "audit_log.jsonl"
    monkeypatch.setattr(slack_promotion, "AUDIT_LOG", audit_log)
    audit_log.write_text(
        json.dumps({
            "type": "listener_reply",
            "channel": "C123",
            "thread_ts": "1710000000.000000",
            "sources": ["company/corpus/vendor_terms.md"],
        })
        + "\n"
        + "{not json}\n",
        encoding="utf-8",
    )

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert result["related_sources_mode"] == "matched"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "company/corpus/vendor_terms.md" in card.read_text(encoding="utf-8")


def test_missing_audit_file_does_not_block_promotion(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(slack_promotion, "AUDIT_LOG", tmp_path / "missing_audit_log.jsonl")

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert result["related_sources_mode"] == "none"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "## Related Sources" not in card.read_text(encoding="utf-8")


def test_related_source_lookup_uses_bounded_audit_tail(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    audit_log = tmp_path / "audit_log.jsonl"
    monkeypatch.setattr(slack_promotion, "AUDIT_LOG", audit_log)
    monkeypatch.setattr(slack_promotion, "AUDIT_LOOKBACK_LINES", 2)
    old_match = json.dumps({
        "type": "listener_reply",
        "channel": "C123",
        "thread_ts": "1710000000.000000",
        "sources": ["company/corpus/old_source.md"],
    })
    audit_log.write_text(
        old_match
        + "\n"
        + json.dumps({"type": "listener_skip", "channel": "C123"})
        + "\n"
        + json.dumps({"type": "listener_skip", "channel": "C123"})
        + "\n",
        encoding="utf-8",
    )

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "company/corpus/old_source.md" not in card.read_text(encoding="utf-8")


def test_user_rate_limit_blocks_second_distinct_thread(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)
    limiter = slack_promotion.PromotionRateLimiter(user_cooldown_seconds=60)

    first = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )
    second = slack_promotion.handle_reaction_event(
        _reaction_event(item={"type": "message", "channel": "C123", "ts": "1710000020.000000"}),
        client=FakePromotionClient(messages=[
            {"ts": "1710000020.000000", "user": "U123", "text": "Another useful thread"},
        ]),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )

    assert first["status"] == "promoted"
    assert second == {"status": "ignored", "reason": "rate_limited_user"}


def test_global_rate_limit_blocks_burst(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)
    limiter = slack_promotion.PromotionRateLimiter(user_cooldown_seconds=0, global_max_per_minute=1)

    first = slack_promotion.handle_reaction_event(
        _reaction_event(user="U111"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )
    second = slack_promotion.handle_reaction_event(
        _reaction_event(user="U222", item={"type": "message", "channel": "C123", "ts": "1710000020.000000"}),
        client=FakePromotionClient(messages=[
            {"ts": "1710000020.000000", "user": "U222", "text": "Another useful thread"},
        ]),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )

    assert first["status"] == "promoted"
    assert second == {"status": "ignored", "reason": "rate_limited_global"}

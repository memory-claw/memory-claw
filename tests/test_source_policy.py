from __future__ import annotations

from pathlib import Path

import pytest

from institutional_memory.source_policy import (
    SourceCommand,
    SourcePolicy,
    apply_source_policy,
    load_source_policy,
    parse_source_command,
    render_source_command,
)


def test_unmatched_source_defaults_to_restricted():
    policy = SourcePolicy()

    assert policy.access_for("company/corpus/new_strategy.md") == "restricted"


def test_last_matching_rule_wins():
    policy = SourcePolicy(
        rules=[
            ("company/corpus/mock_data/**", "share"),
            ("company/corpus/mock_data/secrets.md", "restricted"),
        ]
    )

    assert policy.access_for("company/corpus/mock_data/secrets.md") == "restricted"
    assert policy.access_for("company/corpus/mock_data/readme.md") == "share"


def test_actual_demo_policy_file_loads_expected_access_levels():
    policy = load_source_policy()

    assert policy.access_for("company/corpus/mock_data/slack_threads/Direct_Push_Main_Demo_Thread.md") == "share"
    assert policy.access_for("company/corpus/2023_rfp_postmortem.txt") == "share"
    assert policy.access_for("company/corpus/mock_data/policy_docs/Secrets_Management_Policy.md") == "cite_only"
    assert policy.access_for("company/corpus/mock_data/incidents/GitHub_Credentials_Leak_2023.md") == "restricted"
    assert policy.access_for("company/corpus/unlisted_new_doc.md") == "restricted"


def test_apply_source_policy_filters_restricted_and_strips_cite_only_text():
    policy = SourcePolicy(
        rules=[
            ("company/corpus/share.md", "share"),
            ("company/corpus/cite.md", "cite_only"),
        ]
    )
    hits = [
        {"source": "company/corpus/share.md", "score": 0.91, "text": "share text"},
        {"source": "company/corpus/cite.md", "score": 0.82, "text": "secret policy text"},
        {"source": "company/corpus/restricted.md", "score": 0.77, "text": "restricted text"},
    ]

    visible = apply_source_policy(hits, policy)

    assert visible == [
        {
            "source": "company/corpus/share.md",
            "score": 0.91,
            "text": "share text",
            "access": "share",
            "display_name": "share.md",
        },
        {
            "source": "company/corpus/cite.md",
            "score": 0.82,
            "text": "",
            "access": "cite_only",
            "display_name": "cite.md",
        },
    ]
    assert hits[1]["text"] == "secret policy text"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("show source 2", SourceCommand(kind="excerpt", index=2)),
        ("show full source 3", SourceCommand(kind="full", index=3)),
        (" Show Source 2 ", SourceCommand(kind="excerpt", index=2)),
        ("show sources 2", None),
        ("show source two", None),
        ("show full source 0", None),
        ("please show source 1", None),
    ],
)
def test_parse_source_commands(text, expected):
    assert parse_source_command(text) == expected


def test_render_excerpt_and_full_for_share(tmp_path, monkeypatch):
    import institutional_memory.config as config
    import institutional_memory.source_policy as source_policy

    project_root = tmp_path
    corpus = project_root / "company" / "corpus"
    source = corpus / "share.md"
    source.parent.mkdir(parents=True)
    source.write_text("full source text", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(source_policy, "PROJECT_ROOT", project_root)

    refs = [{"source": "company/corpus/share.md", "access": "share", "text": "excerpt text"}]

    assert render_source_command(SourceCommand(kind="excerpt", index=1), refs) == {
        "status": "ok",
        "text": "Source 1: share.md\n\n> excerpt text",
    }
    assert render_source_command(SourceCommand(kind="full", index=1), refs) == {
        "status": "ok",
        "text": "Full source 1: share.md\n\nfull source text",
    }


def test_render_refuses_cite_only_and_invalid_index():
    refs = [{"source": "company/corpus/cite.md", "access": "cite_only", "text": ""}]

    assert render_source_command(SourceCommand(kind="excerpt", index=1), refs)["status"] == "refused"
    assert render_source_command(SourceCommand(kind="full", index=1), refs)["status"] == "refused"
    assert render_source_command(SourceCommand(kind="excerpt", index=2), refs)["status"] == "missing"

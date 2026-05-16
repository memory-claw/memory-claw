from pathlib import Path

import pytest

from institutional_memory.config import PROJECT_ROOT
from institutional_memory.paths import PathNotAllowedError, safe_inbox_path, safe_runtime_path


def test_safe_inbox_allows_txt_under_company_inbox():
    assert safe_inbox_path("company/inbox/foo.txt") == (PROJECT_ROOT / "company/inbox/foo.txt").resolve()


def test_safe_inbox_blocks_traversal():
    with pytest.raises(PathNotAllowedError):
        safe_inbox_path("../etc/passwd")


def test_safe_inbox_allows_pdf_under_company_inbox():
    assert safe_inbox_path("company/inbox/doc.pdf") == (PROJECT_ROOT / "company/inbox/doc.pdf").resolve()


def test_safe_inbox_blocks_legacy_root_inbox():
    with pytest.raises(PathNotAllowedError):
        safe_inbox_path("inbox/customer_thread.md")


def test_safe_runtime_allows_runtime_file():
    assert safe_runtime_path(".runtime/slack_message.txt") == (
        PROJECT_ROOT / ".runtime/slack_message.txt"
    ).resolve()


def test_safe_runtime_blocks_inbox_file():
    with pytest.raises(PathNotAllowedError):
        safe_runtime_path("company/inbox/foo.txt")


def test_safe_corpus_allows_markdown_under_slack_corpus():
    from institutional_memory.paths import safe_corpus_path

    assert safe_corpus_path("company/corpus/slack/C123_1710000000.000000.md") == (
        PROJECT_ROOT / "company/corpus/slack/C123_1710000000.000000.md"
    ).resolve()


def test_safe_corpus_blocks_traversal():
    from institutional_memory.paths import safe_corpus_path

    with pytest.raises(PathNotAllowedError):
        safe_corpus_path("company/corpus/../../.env")


def test_safe_evidence_allows_json_under_company_evidence():
    from institutional_memory.paths import safe_evidence_path

    assert safe_evidence_path("company/evidence/slack/C123_1710000000.000000.json") == (
        PROJECT_ROOT / "company/evidence/slack/C123_1710000000.000000.json"
    ).resolve()


def test_safe_evidence_blocks_corpus_path():
    from institutional_memory.paths import safe_evidence_path

    with pytest.raises(PathNotAllowedError):
        safe_evidence_path("company/corpus/slack/evidence/C123.json")


def test_safe_evidence_rejects_markdown():
    from institutional_memory.paths import safe_evidence_path

    with pytest.raises(PathNotAllowedError):
        safe_evidence_path("company/evidence/slack/C123.md")

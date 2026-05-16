from pathlib import Path

import pytest

from institutional_memory.config import PROJECT_ROOT
from institutional_memory.paths import PathNotAllowedError, safe_inbox_path, safe_runtime_path


def test_safe_inbox_allows_txt_under_inbox():
    assert safe_inbox_path("inbox/foo.txt") == (PROJECT_ROOT / "inbox/foo.txt").resolve()


def test_safe_inbox_blocks_traversal():
    with pytest.raises(PathNotAllowedError):
        safe_inbox_path("../etc/passwd")


def test_safe_inbox_allows_pdf_under_inbox():
    assert safe_inbox_path("inbox/doc.pdf") == (PROJECT_ROOT / "inbox/doc.pdf").resolve()


def test_safe_runtime_allows_runtime_file():
    assert safe_runtime_path(".runtime/slack_message.txt") == (
        PROJECT_ROOT / ".runtime/slack_message.txt"
    ).resolve()


def test_safe_runtime_blocks_inbox_file():
    with pytest.raises(PathNotAllowedError):
        safe_runtime_path("inbox/foo.txt")

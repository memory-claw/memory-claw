from pathlib import Path

from institutional_memory.config import PROCESSED_REGISTRY
from institutional_memory.state import load_processed, mark_as_processed, reset_processed


def test_mark_as_processed_writes_once():
    try:
        reset_processed()
        mark_as_processed("company/inbox/foo.txt")
        mark_as_processed("company/inbox/foo.txt")
        assert load_processed() == ["company/inbox/foo.txt"]
    finally:
        Path(PROCESSED_REGISTRY).unlink(missing_ok=True)

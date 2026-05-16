from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INBOX_PATH = PROJECT_ROOT / "inbox"

RFP_DRAFT = """New RFP Draft

We are preparing a new RFP response for an enterprise procurement team. The draft includes indemnification provisions, a liability framework, and clause 7.4 language that limits exposure for consequential damages.

Please review whether the proposed clause 7.4 language and indemnification posture match prior bid lessons before the response is sent.
"""

SILENT_DRAFT = """Clinical Trial Protocol Draft

We are preparing a dermatology clinical trial protocol for a placebo-controlled study. The draft covers inclusion criteria, exclusion criteria, randomization, endpoint collection, and adverse event monitoring.

Please review whether the proposed protocol has any relevant institutional memory before it is sent.
"""

CASE_FILES = {
    "rfp": ("new_rfp_draft.txt", RFP_DRAFT),
    "silent": ("000_silent_clinical_trial_protocol.txt", SILENT_DRAFT),
}


def clear_inbox() -> None:
    INBOX_PATH.mkdir(parents=True, exist_ok=True)
    for path in INBOX_PATH.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            path.unlink()


def write_case(name: str) -> Path:
    filename, body = CASE_FILES[name]
    clear_inbox()
    target = INBOX_PATH / filename
    target.write_text(body, encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Set inbox to a known demo case.")
    parser.add_argument("case", choices=sorted(CASE_FILES))
    args = parser.parse_args()

    written = write_case(args.case)
    print(written.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

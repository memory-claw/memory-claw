from __future__ import annotations

import argparse
import json

from institutional_memory.config import CORPUS_PATH
from institutional_memory.ingest import ingest_folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest demo corpus into Chroma")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(ingest_folder(CORPUS_PATH, force=args.force), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

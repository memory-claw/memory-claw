"""Central configuration for the institutional memory demo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(PROJECT_ROOT / ".env", override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:8b")
LLM_MODEL = os.getenv("LLM_MODEL", "nemotron-3-super:120b")

CHROMA_PATH = PROJECT_ROOT / "chroma_db"
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "org_memory")

RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.60"))
TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

COMPANY_DOCS_PATH = PROJECT_ROOT / "company"
COMPANY_INBOX_PATH = COMPANY_DOCS_PATH / "inbox"
COMPANY_CORPUS_PATH = COMPANY_DOCS_PATH / "corpus"
COMPANY_EVIDENCE_PATH = COMPANY_DOCS_PATH / "evidence"
SOURCE_POLICY_PATH = COMPANY_CORPUS_PATH / ".source_policy.yml"
RUNTIME_PATH = PROJECT_ROOT / ".runtime"
PROCESSED_REGISTRY = PROJECT_ROOT / "processed_drafts.json"
INGESTED_REGISTRY = PROJECT_ROOT / "ingested_files.json"
AUDIT_LOG = PROJECT_ROOT / "audit_log.jsonl"
DEMO_ARTIFACTS_PATH = PROJECT_ROOT / "demo_artifacts"

SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#institutional-memory")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

UNPROMPTED_THRESHOLD = float(os.getenv("UNPROMPTED_THRESHOLD", "0.80"))
THREAD_THRESHOLD = float(os.getenv("THREAD_THRESHOLD", "0.65"))
LISTENER_CHANNELS = os.getenv("LISTENER_CHANNELS", "")
PROMOTION_ALLOWED_CHANNELS = os.getenv("PROMOTION_ALLOWED_CHANNELS", "")
PROMOTION_USER_COOLDOWN_SECONDS = float(os.getenv("PROMOTION_USER_COOLDOWN_SECONDS", "60"))
PROMOTION_GLOBAL_MAX_PER_MINUTE = int(os.getenv("PROMOTION_GLOBAL_MAX_PER_MINUTE", "10"))
RESPONSE_MODEL = os.getenv("RESPONSE_MODEL", "qwen2.5:7b-instruct")
RESPONSE_TIMEOUT_SECONDS = float(os.getenv("RESPONSE_TIMEOUT_SECONDS", "15"))

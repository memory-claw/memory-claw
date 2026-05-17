"""Test demo draft texts against ChromaDB to verify they exceed unprompted threshold."""

from __future__ import annotations

import json
import sys

from institutional_memory.config import UNPROMPTED_THRESHOLD
from institutional_memory.search import search_memory

DEMO_QUERIES = {
    "credentials_sharing": (
        "I'll send them the .env from my local machine so they can hit the staging APIs. "
        "It has the AWS access keys and the production Postgres connection string. "
        "Fastest way to get the new contractor unblocked on the analytics dashboard repo."
    ),
    "direct_push_main": (
        "Found the bug causing 401s on the auth endpoint. It's a one-line fix in the JWT "
        "token validation middleware. I'm just going to push it directly to main, don't want "
        "to slow things down with a PR for something this small."
    ),
    "enterprise_deal_no_eng": (
        "Nexus want to move forward. $180K deal, custom SSO integration plus data pipeline "
        "into their warehouse. I told them 6 weeks. I'll get the contract signed this afternoon "
        "and we can loop in engineering once we've won it."
    ),
    "no_feature_flag_billing": (
        "The new billing UI is ready. Proration logic has been rewritten. Let's just ship it "
        "straight to 100% of users today, no feature flag needed. It's been tested and we need "
        "it out by friday."
    ),
    "gdpr_user_deletion": (
        "A user deleted their account last year and now they're asking what data we still have. "
        "I checked and their event history is still in the analytics table and the data warehouse. "
        "Should we just tell them everything was deleted when they cancelled?"
    ),
}


def main() -> int:
    print(f"Unprompted threshold: {UNPROMPTED_THRESHOLD}")
    print("=" * 70)
    all_pass = True

    for name, query in DEMO_QUERIES.items():
        results = search_memory(query, threshold=0.0, top_k=3)
        top_score = results[0]["score"] if results else 0.0
        passed = top_score >= UNPROMPTED_THRESHOLD
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False

        print(f"\n[{status}] {name} — top score: {top_score:.4f} (need >= {UNPROMPTED_THRESHOLD})")
        for hit in results[:3]:
            print(f"  {hit['score']:.4f} | {hit['source']}")

    print("\n" + "=" * 70)
    print(f"Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

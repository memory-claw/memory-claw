"""Test demo draft texts against ChromaDB to verify they exceed unprompted threshold."""

from __future__ import annotations

import json
import sys

from institutional_memory.config import UNPROMPTED_THRESHOLD
from institutional_memory.search import search_memory

DEMO_QUERIES = {
    "credentials_sharing": (
        "Setting up the new intern's dev environment. I'll just send them our .env file "
        "over Slack so they can hit the staging APIs. It has the AWS access keys and "
        "Postgres connection string but it's a private channel so should be fine."
    ),
    "direct_push_main": (
        "Hey, found a small bug in the session timeout logic. Super obvious fix, "
        "literally one line. Can I just push it directly to main? Don't want to wait "
        "for a PR review at this time of day, it's trivial."
    ),
    "enterprise_deal_no_eng": (
        "Big news — Vantara just said they want to move forward! $180K ARR, they want "
        "custom SSO, a data pipeline into their BI tool, and white-labelling. I told "
        "them 8 weeks. I'll get the contract signed today and loop in Marcus after "
        "to figure out the engineering details."
    ),
    "no_feature_flag_billing": (
        "New billing UI is ready to ship. Proration calculation has been rewritten and "
        "it's been tested on staging. Going to deploy it straight to 100% of users, no "
        "feature flag. It's mostly UI changes and we need it out by Friday."
    ),
    "gdpr_user_data_retention": (
        "Got a Subject Access Request from a former user who deleted their account "
        "in 2022. I checked and their user_id is still in the events analytics table "
        "and in our data warehouse. Account deletion only removed their row from the "
        "users table — the event history and behaviour data was never deleted. What "
        "do we do here?"
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

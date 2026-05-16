from scripts import live_handoff


def test_handoff_names_final_gate_proof_artifacts():
    text = "\n".join(live_handoff.STEPS)

    assert "corpus/2023_rfp_postmortem.txt" in text
    assert "000_silent_clinical_trial_protocol.txt" in text
    assert "inbox/new_rfp_draft.txt" in text
    assert "uv run python scripts/demo_case.py silent" in text
    assert "uv run python scripts/demo_case.py rfp" in text
    assert "count: 0" in text
    assert "source_attributions" in text
    assert "non-empty" in text
    assert "no slack_sent" in text

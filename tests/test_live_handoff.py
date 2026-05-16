from scripts import live_handoff


def test_handoff_names_final_gate_proof_artifacts():
    text = "\n".join(live_handoff.STEPS)

    assert "corpus/2023_rfp_postmortem.txt" in text
    assert "000_silent_clinical_trial_protocol.txt" in text
    assert "count: 0" in text

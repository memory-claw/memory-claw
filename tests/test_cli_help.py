import subprocess


def test_hidden_nemoclaw_probe_not_shown_in_top_level_help():
    result = subprocess.run(
        ["./bin/imem", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "nemoclaw-probe" not in result.stdout

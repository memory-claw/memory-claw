import json
import subprocess


def run_imem(*args: str):
    result = subprocess.run(
        ["./bin/imem", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_hello_outputs_valid_json():
    assert run_imem("hello") == {"status": "ok", "message": "hello from Python"}


def test_list_new_drafts_returns_json_array():
    payload = run_imem("list-new-drafts")
    assert isinstance(payload, list)


def test_read_draft_blocks_traversal_with_json_error():
    payload = run_imem("read-draft", "--path", "../etc/passwd")
    assert "error" in payload


def test_mark_processed_blocks_traversal_with_json_error():
    payload = run_imem(
        "mark-processed",
        "--path",
        "../etc/passwd",
        "--status",
        "tool_error",
        "--reason",
        "bad path",
    )
    assert "error" in payload


def test_reset_demo_outputs_json():
    payload = run_imem("reset-demo", "--clear-audit")
    assert payload["status"] == "reset"

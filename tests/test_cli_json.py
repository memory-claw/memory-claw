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


def test_sync_slack_cli_emits_json(monkeypatch, capsys):
    from institutional_memory import cli

    monkeypatch.setattr(
        "institutional_memory.slack_ingest.sync_slack_history",
        lambda **kwargs: {"status": "ok", "written": ["company/inbox/slack/C123_1710000000.000000.md"]},
    )

    args = cli.build_parser().parse_args(["sync-slack", "--mode", "inbox", "--channel", "C123", "--limit", "20"])
    assert args.func(args) == 0
    assert "company/inbox/slack/C123_1710000000.000000.md" in capsys.readouterr().out


def test_promote_slack_thread_subprocess_blocks_traversal_with_json_error():
    payload = run_imem("promote-slack-thread", "--path", "../.env")
    assert "error" in payload


def test_slack_operator_commands_are_visible_in_help():
    result = subprocess.run(["./bin/imem", "--help"], check=True, capture_output=True, text=True)
    assert "sync-slack" in result.stdout
    assert "promote-slack-thread" in result.stdout

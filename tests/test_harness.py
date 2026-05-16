from scripts.harness import send_slack_argv


def test_send_slack_argv_includes_slack_thread_routing():
    draft = {
        "path": "company/inbox/slack/C123_1710000000.000000.md",
        "slack_channel_id": "C123",
        "slack_thread_ts": "1710000000.000000",
    }
    assert send_slack_argv(draft) == [
        "send-slack",
        "--message-file",
        ".runtime/slack_message.txt",
        "--channel",
        "C123",
        "--thread-ts",
        "1710000000.000000",
    ]


def test_send_slack_argv_defaults_without_metadata():
    draft = {"path": "company/inbox/new_rfp_draft.txt"}
    assert send_slack_argv(draft) == [
        "send-slack",
        "--message-file",
        ".runtime/slack_message.txt",
    ]

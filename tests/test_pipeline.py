"""Offline tests: sources parse the sample data, and the triage call is wired
correctly (using a fake client, so no API key is needed)."""

import os
import tomllib
from types import SimpleNamespace

from halkvakt_pm.cli import collect, main
from halkvakt_pm.models import TriagedIssue, TriageResult
from halkvakt_pm.report import to_markdown
from halkvakt_pm.triage import build_user_message, triage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_items():
    with open(os.path.join(ROOT, "config.example.toml"), "rb") as fh:
        cfg = tomllib.load(fh)
    return collect(cfg, ROOT)


def test_sources_load_all_sample_data():
    items = load_items()
    by_channel = {}
    for it in items:
        by_channel.setdefault(it.channel, []).append(it)
    assert len(by_channel["bug_tracker"]) == 6
    assert len(by_channel["social"]) == 7
    assert len(by_channel["email"]) == 5
    bug = next(i for i in items if i.id == "bugs-101")
    assert bug.meta["votes"] == "14" and "Android 15" in bug.title
    tweet = next(i for i in items if i.id == "social-tw-9002")
    assert tweet.author == "@sara_k" and tweet.meta["likes"] == 388
    mail = next(i for i in items if i.id == "support-email-004")
    assert mail.title == "Late notifications on Android" and "OnePlus" in mail.text


def test_prompt_contains_every_item():
    items = load_items()
    msg = build_user_message(items)
    for it in items:
        assert it.id in msg


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, parsed):
        self.calls = []
        msg = SimpleNamespace(stop_reason="end_turn", stop_details=None, parsed_output=parsed)
        outer = self

        class _Messages:
            def stream(self, **kw):
                outer.calls.append(kw)
                return FakeStream(msg)

        self.beta = SimpleNamespace(messages=_Messages())


def fake_result():
    return TriageResult(
        overview="Android alerts are late.",
        issues=[
            TriagedIssue(rank=2, priority="P1", kind="bug", title="Double charge", summary="s",
                         rationale="r", evidence_ids=["bugs-106", "support-email-002"],
                         channels=["bug_tracker", "email"], report_count=2,
                         suggested_next_step="refund", confidence="high"),
            TriagedIssue(rank=1, priority="P0", kind="bug", title="Late Android alerts", summary="s",
                         rationale="r", evidence_ids=["bugs-101", "social-tw-9002", "made-up-id"],
                         channels=["bug_tracker", "social"], report_count=9,
                         suggested_next_step="fix", confidence="high"),
        ],
        ignored_ids=["social-tw-9003", "nope"],
    )


def test_triage_request_and_normalisation():
    items = load_items()
    client = FakeClient(fake_result())
    result = triage(items, client=client)
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["thinking"] == {"type": "adaptive"}
    assert call["output_format"] is TriageResult
    assert call["fallbacks"] == "default"
    assert "Halkvakt" in call["system"]
    # Sorted by priority, ranks renumbered, hallucinated IDs dropped.
    assert [i.title for i in result.issues] == ["Late Android alerts", "Double charge"]
    assert [i.rank for i in result.issues] == [1, 2]
    assert result.issues[0].evidence_ids == ["bugs-101", "social-tw-9002"]
    assert result.issues[0].report_count == 2
    assert result.ignored_ids == ["social-tw-9003"]
    md = to_markdown(result, items)
    assert "| 1 | P0 | Bug | Late Android alerts |" in md
    assert "**Why P0:** r" in md


def test_dry_run(capsys):
    assert main(["--config", os.path.join(ROOT, "config.example.toml"), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "support-email-001" in out

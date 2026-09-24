"""The JSON envelope: the machine-readable contract of the executable.

Every command run with `--json` must produce a consistent, serialisable envelope, whether it
succeeded or failed. This is the surface other programs build on, so it is asserted only through
the executable.
"""

import json
import re
import sqlite3
import subprocess
import sys

import pytest

from conftest import TEST_DIR, chats_db, run_cli, run_prompt

ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")


def assert_envelope(envelope: dict, *, success: bool = True):
    """The shape every `--json` run must produce."""
    assert isinstance(envelope, dict), type(envelope)
    assert envelope.get("success") is success, envelope

    assert "error" in envelope, envelope.keys()
    if success:
        assert envelope["error"] is None, envelope["error"]
    else:
        assert envelope["error"], "a failed envelope must say why"

    meta = envelope.get("meta")
    assert isinstance(meta, dict), envelope.keys()
    assert ISO_TS.match(meta["timestamp"]), meta["timestamp"]
    assert meta["version"], meta

    # The whole envelope must survive a JSON round trip -- it is a machine contract.
    assert json.loads(json.dumps(envelope)) == envelope


# --- read-only commands ---------------------------------------------------------------------

@pytest.mark.parametrize("command", [
    ("models", "get"),
    ("providers", "list"),
    ("functions", "list"),
    ("database", "get"),
    ("prompts", "get"),
    ("chats", "list"),
])
def test_every_read_command_returns_a_valid_envelope(command):
    envelope, _ = run_cli(*command, offline=True)
    assert_envelope(envelope)
    assert envelope["data"] is not None


def test_models_get_accepts_a_filter():
    envelope, _ = run_cli("models", "get", "--provider", "OpenAI", offline=True)
    assert_envelope(envelope)


def test_functions_list_reports_the_builtins():
    envelope, _ = run_cli("functions", "list", offline=True)
    assert_envelope(envelope)
    assert "readfile" in json.dumps(envelope["data"])


# --- failures ----------------------------------------------------------------------------------

def test_unknown_verb_is_rejected_before_the_envelope():
    """argparse sits above the envelope: an unparseable command line never reaches it."""
    result = subprocess.run(
        [sys.executable, "-m", "keprompt", "models", "frobnicate", "--json"],
        cwd=TEST_DIR, capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    assert "{" not in result.stdout


def test_missing_prompt_fails_with_an_envelope():
    envelope, _ = run_cli("chats", "create", "does-not-exist", offline=True)
    assert_envelope(envelope, success=False)
    assert "does-not-exist" in json.dumps(envelope)


@pytest.mark.xfail(reason="DEFECT-003: a chat lookup miss reports success=True and sets data to "
                          "the string 'None' instead of failing with null data",
                   strict=True)
def test_getting_an_unknown_chat_fails():
    envelope, _ = run_cli("chats", "get", "nochatid", offline=True)
    assert_envelope(envelope, success=False)


def test_a_failing_prompt_still_produces_an_envelope():
    """A run that dies mid-prompt must report, not crash."""
    envelope, _ = run_prompt("env-boom", offline=True)
    assert_envelope(envelope, success=False)


# --- chats lifecycle, entirely through the CLI -------------------------------------------------

def test_a_created_chat_appears_in_the_listing():
    created, _ = run_prompt("env-hello", offline=True)
    chat_id = created["chat_id"]
    envelope, _ = run_cli("chats", "list", offline=True)
    assert_envelope(envelope)
    assert chat_id in json.dumps(envelope["data"])


def test_create_then_get_then_delete():
    created, _ = run_prompt("env-hello", offline=True)
    assert_envelope(created)
    chat_id = created.get("chat_id")
    assert chat_id, created

    fetched, _ = run_cli("chats", "get", chat_id, offline=True)
    assert_envelope(fetched)
    assert chat_id in json.dumps(fetched)

    deleted, _ = run_cli("chats", "delete", chat_id, offline=True)
    assert_envelope(deleted)

    gone, _ = run_cli("chats", "get", chat_id, offline=True)
    assert_envelope(gone)          # see DEFECT-003: a miss is currently reported as success
    assert gone["data"] in (None, "None", {}, []), gone["data"]


def test_stdout_carries_what_the_prompt_printed():
    envelope, _ = run_prompt("env-hello", offline=True)
    assert_envelope(envelope)
    assert "hello" in envelope["stdout"]


def test_a_run_is_persisted():
    """Assert about the chat this test created, not about the whole table."""
    envelope, _ = run_prompt("env-hello", offline=True)
    row = sqlite3.connect(chats_db()).execute(
        "SELECT prompt_name FROM chats WHERE chat_id = ?", (envelope["chat_id"],)).fetchone()
    assert row == ("P",)


def test_listing_respects_a_limit():
    for _ in range(3):
        run_prompt("env-hello", offline=True)
    envelope, _ = run_cli("chats", "list", "--limit", "2", offline=True)
    assert_envelope(envelope)
    assert len(envelope["data"]) <= 2


# --- the envelope reports what it was asked to do ----------------------------------------------

def test_meta_echoes_the_command():
    envelope, _ = run_cli("models", "get", offline=True)
    assert envelope["meta"]["args"]["command"] in ("models", "model")


def test_version_in_meta_matches_what_the_cli_reports():
    """Both sides of the comparison come from the executable."""
    reported = subprocess.run(
        [sys.executable, "-m", "keprompt", "--version"],
        cwd=TEST_DIR, capture_output=True, text=True, timeout=120).stdout.strip()
    envelope, _ = run_cli("models", "get", offline=True)
    assert envelope["meta"]["version"] in reported

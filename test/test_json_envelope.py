"""
Tests for JSON API response envelope consistency.

Every manager's execute() must return a dict with at minimum:
    {"success": bool, "data": <payload>, "timestamp": str}

The CLI envelope (--json mode) wraps that into:
    {"success": bool, "data": ..., "error": ..., "stdout": ..., "meta": {...}}

This test suite validates both layers.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ISO-8601 timestamp regex (with or without trailing Z)
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")


def assert_manager_envelope(response: dict, *, expect_success: bool = True):
    """Assert that a manager-level response follows the standard envelope."""
    assert isinstance(response, dict), f"Response must be a dict, got {type(response)}"
    assert "success" in response, f"Missing 'success' key. Keys: {list(response.keys())}"
    assert response["success"] is expect_success, (
        f"Expected success={expect_success}, got {response['success']}"
    )

    if expect_success:
        assert "data" in response, f"Successful response missing 'data' key. Keys: {list(response.keys())}"
        assert response["data"] is not None, "Successful response has data=None"
    else:
        assert "error" in response, f"Failed response missing 'error' key. Keys: {list(response.keys())}"

    # Timestamp present and valid ISO format
    assert "timestamp" in response, f"Missing 'timestamp' key. Keys: {list(response.keys())}"
    assert ISO_TS_RE.match(response["timestamp"]), (
        f"Timestamp not ISO-8601: {response['timestamp']}"
    )


def assert_json_serializable(obj, path="root"):
    """Recursively assert that an object is JSON-serializable."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str), f"Non-string dict key at {path}: {type(k)}"
            assert_json_serializable(v, f"{path}.{k}")
        return
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_json_serializable(v, f"{path}[{i}]")
        return
    # Anything else is suspect
    pytest.fail(f"Non-serializable type {type(obj).__name__} at {path}")


def assert_cli_envelope(envelope: dict):
    """Assert the full CLI JSON envelope structure (--json output)."""
    # Top-level required keys
    for key in ("success", "data", "error", "meta"):
        assert key in envelope, f"CLI envelope missing '{key}'. Keys: {list(envelope.keys())}"

    # Mutual exclusivity: exactly one of data/error is non-null
    if envelope["success"]:
        assert envelope["data"] is not None, "success=True but data is None"
        assert envelope["error"] is None, f"success=True but error is not None: {envelope['error']}"
    else:
        assert envelope["data"] is None, f"success=False but data is not None"
        assert envelope["error"] is not None, "success=False but error is None"

    # Meta structure
    meta = envelope["meta"]
    assert isinstance(meta, dict), f"meta must be a dict, got {type(meta)}"
    assert "schema_version" in meta, "meta missing 'schema_version'"
    assert meta["schema_version"] == 1
    assert "command" in meta, "meta missing 'command'"
    assert "version" in meta, "meta missing 'version'"
    assert "timestamp" in meta, "meta missing 'timestamp'"
    assert ISO_TS_RE.match(meta["timestamp"]), f"meta.timestamp not ISO-8601: {meta['timestamp']}"


def make_args(**kwargs):
    """Build an argparse.Namespace with sensible defaults for JSON mode."""
    defaults = {"pretty": False, "json": True, "dump": False, "format": "full"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Provider Manager
# ---------------------------------------------------------------------------

class TestProviderManager:
    def test_list_providers(self):
        from keprompt.api import ProviderManager

        args = make_args(command="provider", provider_command="get")
        mgr = ProviderManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert response.get("object_type") == "provider_list"

        # Each provider has name and models_count
        if response["data"]:
            p = response["data"][0]
            assert "name" in p
            assert "models_count" in p

        assert_json_serializable(response)

    def test_unknown_command(self):
        from keprompt.api import ProviderManager

        args = make_args(command="provider", provider_command="bogus")
        mgr = ProviderManager(args)
        response = mgr.execute()

        assert_manager_envelope(response, expect_success=False)
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Model Manager
# ---------------------------------------------------------------------------

class TestModelManager:
    def test_list_models(self):
        from keprompt.ModelManager import ModelManager

        args = make_args(
            command="models", models_command="get",
            name=None, provider=None, company=None,
        )
        mgr = ModelManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert_json_serializable(response)

        # Spot-check model fields
        if response["data"]:
            m = response["data"][0]
            for field in ("provider", "model", "input_cost", "output_cost"):
                assert field in m, f"Model missing '{field}'"

    def test_list_models_with_filter(self):
        from keprompt.ModelManager import ModelManager

        args = make_args(
            command="models", models_command="get",
            name="gpt", provider=None, company=None,
        )
        mgr = ModelManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert_json_serializable(response)

    def test_reset_models(self):
        from keprompt.ModelManager import ModelManager

        args = make_args(command="models", models_command="reset")
        mgr = ModelManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], dict)
        assert "message" in response["data"]
        assert_json_serializable(response)

    def test_unsupported_command(self):
        from keprompt.ModelManager import ModelManager

        args = make_args(command="models", models_command="explode")
        mgr = ModelManager(args)
        response = mgr.execute()

        assert_manager_envelope(response, expect_success=False)
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Function Manager
# ---------------------------------------------------------------------------

class TestFunctionManager:
    def test_list_functions(self):
        from keprompt.api import FunctionManager

        args = make_args(command="functions", functions_command="get")
        mgr = FunctionManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert response.get("object_type") == "function_list"
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Database Manager
# ---------------------------------------------------------------------------

class TestDatabaseManager:
    def test_get(self):
        from keprompt.database import DatabaseManager

        args = make_args(command="database", database_command="get")
        mgr = DatabaseManager()
        mgr.args = args
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], dict)
        assert "cmd" in response["data"]
        assert_json_serializable(response)

    def test_create(self):
        from keprompt.database import DatabaseManager

        args = make_args(command="database", database_command="create")
        mgr = DatabaseManager()
        mgr.args = args
        response = mgr.execute()

        assert_manager_envelope(response)
        assert_json_serializable(response)

    def test_delete(self):
        from keprompt.database import DatabaseManager

        args = make_args(command="database", database_command="delete")
        mgr = DatabaseManager()
        mgr.args = args
        response = mgr.execute()

        assert_manager_envelope(response)
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Prompt Manager
# ---------------------------------------------------------------------------

class TestPromptManager:
    def test_list_prompts(self):
        from keprompt.Prompt import PromptManager

        args = make_args(command="prompt", prompt_command="get")
        mgr = PromptManager(args)
        response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Chat Manager — unit tests with mocked DB/VM
# ---------------------------------------------------------------------------

class TestChatManagerGet:
    """Test execute_get envelope shapes."""

    def test_list_chats_empty(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="get", chat_id=None, limit=None)
        mgr = ChatManager(args)

        with patch.object(mgr, "list_chats", return_value=[]):
            response = mgr.execute_get()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert response["data"] == []
        assert_json_serializable(response)

    def test_list_chats_with_limit(self):
        from keprompt.chat_manager import ChatManager

        fake_chats = [{"chat_id": "abc12345", "prompt_name": "test"}]
        args = make_args(command="chat", chat_command="get", chat_id=None, limit=5)
        mgr = ChatManager(args)

        with patch.object(mgr, "list_chats", return_value=fake_chats):
            response = mgr.execute_get()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 1
        assert_json_serializable(response)

    def test_get_single_chat(self):
        from keprompt.chat_manager import ChatManager

        fake_chat = {"chat_id": "abc12345", "prompt_name": "test", "messages": []}
        args = make_args(command="chat", chat_command="get", chat_id="abc12345", limit=None, format="full")
        mgr = ChatManager(args)

        with patch.object(mgr, "get_chat", return_value=fake_chat):
            response = mgr.execute_get()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 1
        assert response["data"][0]["chat_id"] == "abc12345"
        assert_json_serializable(response)


class TestChatManagerDelete:
    """Test execute_delete envelope shapes."""

    def test_delete_specific_chat(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="delete", chat_id="abc12345")
        mgr = ChatManager(args)

        with patch.object(mgr, "delete_chat", return_value=True):
            response = mgr.execute_delete()

        assert_manager_envelope(response)
        assert isinstance(response["data"], dict)
        assert response["data"]["chat_id"] == "abc12345"
        assert response["data"]["deleted"] is True
        assert_json_serializable(response)

    def test_delete_nonexistent_chat(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="delete", chat_id="nope1234")
        mgr = ChatManager(args)

        with patch.object(mgr, "delete_chat", return_value=False):
            response = mgr.execute_delete()

        assert_manager_envelope(response)
        assert response["data"]["deleted"] is False
        assert_json_serializable(response)

    def test_cleanup(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(
            command="chat", chat_command="delete",
            chat_id=None, max_days=30, max_count=None, max_size_gb=None,
        )
        mgr = ChatManager(args)

        cleanup_result = {"deleted_chats": 5, "deleted_costs": 10}
        with patch.object(mgr, "cleanup_chats", return_value=cleanup_result):
            response = mgr.execute_delete()

        assert_manager_envelope(response)
        assert isinstance(response["data"], dict)
        assert_json_serializable(response)


class TestChatManagerCreate:
    """Test execute_create envelope shapes."""

    def test_missing_prompt(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="new", prompt=None, set=[])
        mgr = ChatManager(args)
        response = mgr.execute_create()

        assert_manager_envelope(response, expect_success=False)
        assert "required" in response["error"].lower()
        assert_json_serializable(response)

    def test_successful_create(self):
        """Test that a successful create returns the full chat conversation envelope."""
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="new", prompt="hello", set=[])
        mgr = ChatManager(args)

        # Build a fake VM
        mock_vm = MagicMock()
        mock_vm.prompt_uuid = "test1234"
        mock_vm.prompt_name = "hello"
        mock_vm.prompt_version = "1.0.0"
        mock_vm.cost_in = 0.001
        mock_vm.cost_out = 0.002
        mock_vm.toks_in = 100
        mock_vm.toks_out = 50
        mock_vm.model_name = "gpt-4o"
        mock_vm.model = MagicMock(provider="openai")
        mock_vm.interaction_no = 1
        mock_vm.last_response = "Hello! How can I help?"
        mock_vm.vdict = {"name": "World"}
        mock_vm.prompt = MagicMock()
        mock_vm.prompt.messages = []
        mock_vm.prompt.to_json.return_value = []

        with patch("keprompt.chat_manager.VM", return_value=mock_vm) as mock_vm_cls, \
             patch.object(mgr, "save_chat"), \
             patch.object(mgr, "_make_variables_serializable", return_value={"name": "World"}):
            mock_vm.execute.return_value = None
            response = mgr.execute_create()

        assert_manager_envelope(response)
        assert response.get("object_type") == "chat_conversation"
        assert response.get("chat_id") == "test1234"
        assert response.get("ai_response") is not None

        # data sub-envelope
        data = response["data"]
        assert isinstance(data, dict)
        assert "chat_id" in data
        assert "metadata" in data
        assert "params" in data
        assert isinstance(data["metadata"], dict)
        for field in ("total_cost", "tokens_in", "tokens_out", "elapsed_time", "model", "provider", "api_calls"):
            assert field in data["metadata"], f"metadata missing '{field}'"

        assert_json_serializable(response)

    def test_vm_init_error(self):
        """Test that a VM init error returns a proper failure envelope."""
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="new", prompt="nonexistent", set=[])
        mgr = ChatManager(args)

        with patch("keprompt.chat_manager.VM", side_effect=Exception("Prompt not found")):
            response = mgr.execute_create()

        assert_manager_envelope(response, expect_success=False)
        assert "Prompt not found" in response["error"]
        assert_json_serializable(response)


class TestChatManagerSuccess:
    """Test the success() method used by execute_update (chat reply)."""

    def test_reply_success_envelope(self):
        from keprompt.chat_manager import ChatManager

        args = make_args(command="chat", chat_command="reply")
        mgr = ChatManager(args)

        mock_vm = MagicMock()
        mock_vm.prompt_uuid = "repl1234"
        mock_vm.prompt_name = "test"
        mock_vm.prompt_version = "1.0.0"
        mock_vm.cost_in = 0.01
        mock_vm.cost_out = 0.02
        mock_vm.toks_in = 200
        mock_vm.toks_out = 100
        mock_vm.model_name = "claude-sonnet-4-20250514"
        mock_vm.model = MagicMock(provider="anthropic")
        mock_vm.interaction_no = 2
        mock_vm.last_response = "Here is the answer."
        mock_vm.prompt = MagicMock()
        mock_vm.prompt.messages = []
        mock_vm.prompt.to_json.return_value = []

        response = mgr.success(mock_vm, elapsed_time=1.5, params_dict={"key": "val"})

        assert_manager_envelope(response)
        assert response.get("object_type") == "chat_conversation"
        assert response.get("chat_id") == "repl1234"
        assert isinstance(response.get("ai_response"), str)

        data = response["data"]
        assert "chat_id" in data
        assert "metadata" in data
        assert data["metadata"]["elapsed_time"] == 1.5
        assert data["params"] == {"key": "val"}

        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# Server Manager — unit tests with mocked server registry
# ---------------------------------------------------------------------------

class TestServerManager:
    def test_list_servers_empty(self):
        from keprompt.api import ServerManager

        args = make_args(command="server", server_command="get", all=False, active_only=False, directory=None)
        mgr = ServerManager(args)

        with patch("keprompt.api.sync_registry"), \
             patch("keprompt.api.list_servers", return_value=[]):
            response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert response["data"] == []
        assert_json_serializable(response)

    def test_status_not_registered(self):
        from keprompt.api import ServerManager

        args = make_args(command="server", server_command="status", all=False, directory="/tmp/test")
        mgr = ServerManager(args)

        with patch("keprompt.api.sync_registry"), \
             patch("keprompt.api.get_target_directories", return_value=["/tmp/test"]), \
             patch("keprompt.api.get_server", return_value=None):
            response = mgr.execute()

        assert_manager_envelope(response)
        assert isinstance(response["data"], list)
        assert response["data"][0]["status"] == "not_registered"
        assert_json_serializable(response)

    def test_stop_server(self):
        from keprompt.api import ServerManager

        args = make_args(command="server", server_command="stop", all=False, directory="/tmp/test")
        mgr = ServerManager(args)

        with patch("keprompt.api.sync_registry"), \
             patch("keprompt.api.get_target_directories", return_value=["/tmp/test"]), \
             patch("keprompt.api.stop_server", return_value=True):
            response = mgr.execute()

        assert_manager_envelope(response)
        assert response["data"][0]["stopped"] is True
        assert_json_serializable(response)

    def test_start_all_error(self):
        from keprompt.api import ServerManager

        args = make_args(command="server", server_command="start", all=True, directory=None,
                         port=None, host="localhost", web_gui=False, reload=False)
        mgr = ServerManager(args)

        with patch("keprompt.api.sync_registry"):
            response = mgr.execute()

        assert_manager_envelope(response, expect_success=False)
        assert_json_serializable(response)

    def test_unknown_command(self):
        from keprompt.api import ServerManager

        args = make_args(command="server", server_command="nope")
        mgr = ServerManager(args)

        with patch("keprompt.api.sync_registry"):
            response = mgr.execute()

        assert_manager_envelope(response, expect_success=False)
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# handle_json_command — error wrapping
# ---------------------------------------------------------------------------

class TestHandleJsonCommand:
    def test_unknown_command_error(self):
        from keprompt.api import handle_json_command

        args = make_args(command="banana")
        response = handle_json_command(args)

        assert_manager_envelope(response, expect_success=False)
        assert "Unknown Object" in response["error"]
        assert "source" in response
        assert_json_serializable(response)


# ---------------------------------------------------------------------------
# CLI Envelope integration tests (subprocess)
# ---------------------------------------------------------------------------

class TestCLIEnvelope:
    """Integration tests — invoke the real CLI with --json and validate the
    full envelope that gets written to stdout."""

    @staticmethod
    def _run_cli(*extra_args: str) -> dict:
        """Run keprompt CLI with --json and return parsed envelope.

        Note: --json is a parent_parser flag inherited by subcommand parsers,
        so it must come AFTER the subcommand, e.g. `keprompt models get --json`.

        Some commands may print non-JSON text to stdout before the JSON envelope
        (e.g., deprecation warnings from model_updater.reset_to_defaults).
        We extract the JSON object by finding the first '{' at the start of a line.
        """
        cmd = [sys.executable, "-m", "keprompt"] + list(extra_args) + ["--json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        stdout = result.stdout.strip()
        assert stdout, f"CLI produced no stdout. stderr: {result.stderr}"

        # Find the JSON object — first '{' at start of a line
        json_start = None
        for i, line in enumerate(stdout.split("\n")):
            if line.lstrip().startswith("{"):
                json_start = stdout.index(line)
                break
        assert json_start is not None, f"No JSON object found in stdout: {stdout[:200]}"

        envelope = json.loads(stdout[json_start:])
        return envelope

    def test_models_get(self):
        envelope = self._run_cli("models", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], list)
        assert envelope["meta"]["command"] == "models"

    def test_models_get_with_filter(self):
        envelope = self._run_cli("models", "get", "--name", "gpt")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        # Every model in data should match the filter
        for m in envelope["data"]:
            assert "gpt" in m.get("model", "").lower(), f"Filter leak: {m.get('model')}"

    def test_models_reset(self):
        envelope = self._run_cli("models", "reset")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], dict)
        assert "message" in envelope["data"]

    def test_provider_list(self):
        envelope = self._run_cli("provider", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], list)
        assert envelope["meta"]["command"] == "provider"

    def test_functions_list(self):
        envelope = self._run_cli("functions", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], list)
        assert envelope["meta"]["command"] == "functions"

    def test_database_get(self):
        envelope = self._run_cli("database", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], dict)

    def test_prompt_list(self):
        envelope = self._run_cli("prompt", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], list)
        assert envelope["meta"]["command"] == "prompt"

    def test_chat_list(self):
        envelope = self._run_cli("chat", "get")
        assert_cli_envelope(envelope)
        assert envelope["success"] is True
        assert isinstance(envelope["data"], list)
        assert envelope["meta"]["command"] == "chat"

    def test_unknown_command_error(self):
        """Unknown commands are caught by argparse before our code runs,
        so they produce stderr (argparse error) but no JSON stdout.
        Verify we handle this gracefully."""
        cmd = [sys.executable, "-m", "keprompt", "banana", "get", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                cwd=str(Path(__file__).resolve().parent.parent))
        # argparse exits with code 2 and writes to stderr
        assert result.returncode != 0
        # If there happens to be JSON output, it should be a valid envelope
        if result.stdout.strip():
            envelope = json.loads(result.stdout.strip())
            assert_cli_envelope(envelope)
            assert envelope["success"] is False

    def test_envelope_data_error_mutual_exclusivity(self):
        """Across multiple commands, verify data/error mutual exclusivity holds."""
        commands = [
            ["models", "get"],
            ["provider", "get"],
            ["functions", "get"],
            ["database", "get"],
            ["chat", "get"],
        ]
        for cmd_args in commands:
            envelope = self._run_cli(*cmd_args)
            assert_cli_envelope(envelope)
            # Double-check: data XOR error
            has_data = envelope["data"] is not None
            has_error = envelope["error"] is not None
            assert has_data != has_error, (
                f"data/error exclusivity violated for {cmd_args}: "
                f"data={has_data}, error={has_error}"
            )

    def test_meta_version_consistent(self):
        """meta.version should match across calls."""
        e1 = self._run_cli("models", "get")
        e2 = self._run_cli("provider", "get")
        assert e1["meta"]["version"] == e2["meta"]["version"]
        # Should look like a semver-ish string
        assert re.match(r"\d+\.\d+\.\d+", e1["meta"]["version"])

    def test_meta_schema_version(self):
        envelope = self._run_cli("models", "get")
        assert envelope["meta"]["schema_version"] == 1

    def test_envelope_is_single_json_object(self):
        """The JSON output should be parseable from stdout as exactly one dict."""
        envelope = self._run_cli("models", "get")
        assert isinstance(envelope, dict)

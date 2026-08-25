"""Tests for --set-from-json: file load, merge with --set, create/reply wiring."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from keprompt.chat_manager import ChatManager


def make_args(**kwargs):
    defaults = {"pretty": False, "json": True, "dump": False, "format": "full"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestLoadSetFromJson:
    def test_loads_object_and_keeps_json_types(self, tmp_path):
        path = tmp_path / "vars.json"
        path.write_text('{"question": "hello", "n": 2, "ok": true}', encoding="utf-8")

        data = ChatManager._load_set_from_json(str(path))

        assert data == {"question": "hello", "n": 2, "ok": True}

    def test_empty_object(self, tmp_path):
        path = tmp_path / "vars.json"
        path.write_text("{}", encoding="utf-8")

        assert ChatManager._load_set_from_json(str(path)) == {}

    def test_missing_file(self, tmp_path):
        path = tmp_path / "missing.json"
        with pytest.raises(ValueError, match="cannot read"):
            ChatManager._load_set_from_json(str(path))

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            ChatManager._load_set_from_json(str(path))

    def test_rejects_array(self, tmp_path):
        path = tmp_path / "list.json"
        path.write_text('["a", "b"]', encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            ChatManager._load_set_from_json(str(path))

    def test_rejects_scalar(self, tmp_path):
        path = tmp_path / "scalar.json"
        path.write_text('"hello"', encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            ChatManager._load_set_from_json(str(path))


class TestCreateFromJson:
    def _mock_vm(self):
        mock_vm = MagicMock()
        mock_vm.prompt_uuid = "test1234"
        mock_vm.prompt_name = "hello"
        mock_vm.prompt_version = "1.0.0"
        mock_vm.cost_in = 0.0
        mock_vm.cost_out = 0.0
        mock_vm.toks_in = 0
        mock_vm.toks_out = 0
        mock_vm.model_name = "gpt-4o"
        mock_vm.model = MagicMock(provider="openai")
        mock_vm.interaction_no = 1
        mock_vm.round_trip_count = 0
        mock_vm.api_time = 0.0
        mock_vm.tool_time = 0.0
        mock_vm.last_response = "ok"
        mock_vm.vdict = {}
        mock_vm.prompt = MagicMock()
        mock_vm.prompt.messages = []
        mock_vm.prompt.to_json.return_value = []
        mock_vm.execute.return_value = None
        return mock_vm

    def test_passes_json_params_to_vm(self, tmp_path):
        path = tmp_path / "vars.json"
        path.write_text('{"question": "hello", "n": 2}', encoding="utf-8")
        args = make_args(
            command="chat",
            chat_command="create",
            prompt="hello",
            set=[],
            set_from_json=str(path),
        )
        mgr = ChatManager(args)
        mock_vm = self._mock_vm()

        with patch("keprompt.chat_manager.VM", return_value=mock_vm) as mock_vm_cls, \
             patch.object(mgr, "save_chat"), \
             patch.object(mgr, "_make_variables_serializable", return_value={}):
            mgr.execute_create()

        params = mock_vm_cls.call_args.kwargs["params"]
        assert params["question"] == "hello"
        assert params["n"] == 2

    def test_set_overrides_json_on_matching_key(self, tmp_path):
        path = tmp_path / "vars.json"
        path.write_text('{"question": "from-file", "name": "Alice"}', encoding="utf-8")
        args = make_args(
            command="chat",
            chat_command="create",
            prompt="hello",
            set=[["question", "from-cli"]],
            set_from_json=str(path),
        )
        mgr = ChatManager(args)
        mock_vm = self._mock_vm()

        with patch("keprompt.chat_manager.VM", return_value=mock_vm) as mock_vm_cls, \
             patch.object(mgr, "save_chat"), \
             patch.object(mgr, "_make_variables_serializable", return_value={}):
            mgr.execute_create()

        params = mock_vm_cls.call_args.kwargs["params"]
        assert params["question"] == "from-cli"
        assert params["name"] == "Alice"

    def test_missing_json_file_fails_envelope(self, tmp_path):
        args = make_args(
            command="chat",
            chat_command="create",
            prompt="hello",
            set=[],
            set_from_json=str(tmp_path / "nope.json"),
        )
        mgr = ChatManager(args)
        response = mgr.execute_create()

        assert response["success"] is False
        assert "cannot read" in response["error"]

    def test_invalid_json_fails_envelope(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{", encoding="utf-8")
        args = make_args(
            command="chat",
            chat_command="create",
            prompt="hello",
            set=[],
            set_from_json=str(path),
        )
        mgr = ChatManager(args)
        response = mgr.execute_create()

        assert response["success"] is False
        assert "invalid JSON" in response["error"]


class TestReplyFromJson:
    def test_json_before_load_vm_on_bad_file(self, tmp_path):
        args = make_args(
            command="chat",
            chat_command="reply",
            chat_id="abcd1234",
            answer="hi",
            set=[],
            set_from_json=str(tmp_path / "nope.json"),
        )
        mgr = ChatManager(args)

        with patch.object(mgr, "load_vm") as load_vm:
            response = mgr.execute_update()

        load_vm.assert_not_called()
        assert response["success"] is False
        assert "cannot read" in response["error"]

    def test_set_variable_then_set_statements(self, tmp_path):
        path = tmp_path / "vars.json"
        path.write_text('{"question": "from-file", "n": 2}', encoding="utf-8")
        args = make_args(
            command="chat",
            chat_command="reply",
            chat_id="abcd1234",
            answer="hi",
            set=[["question", "from-cli"]],
            set_from_json=str(path),
        )
        mgr = ChatManager(args)
        mock_vm = MagicMock()
        mock_vm.prompt.messages = []
        mock_vm.prompt_uuid = "abcd1234"
        mock_vm.prompt_name = "hello"
        mock_vm.prompt_version = "1.0.0"
        mock_vm.cost_in = 0.0
        mock_vm.cost_out = 0.0
        mock_vm.toks_in = 0
        mock_vm.toks_out = 0
        mock_vm.model_name = ""
        mock_vm.model = None
        mock_vm.interaction_no = 1
        mock_vm.round_trip_count = 0
        mock_vm.api_time = 0.0
        mock_vm.tool_time = 0.0
        mock_vm.last_response = "ok"
        mock_vm.provider = ""
        mock_vm.vdict = {}

        with patch.object(mgr, "load_vm", return_value=mock_vm), \
             patch.object(mgr, "save_chat"), \
             patch.object(mgr, "_extract_ai_response", return_value="ok"):
            mgr.execute_update()

        mock_vm.set_variable.assert_any_call("question", "from-file")
        mock_vm.set_variable.assert_any_call("n", 2)
        mock_vm.add_statement.assert_any_call(keyword=".set", value="question from-cli")
        mock_vm.add_statement.assert_any_call(keyword=".user", value="hi")
        mock_vm.add_statement.assert_any_call(keyword=".exec", value="")

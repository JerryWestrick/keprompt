# keprompt/tbd_session_manager.py
"""High-level chat management for KePrompt.

Provides the interface between the VM and the database layer.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from rich.markdown import Markdown
from rich.table import Table

from keprompt.AiPrompt import AiTextPart
from keprompt.database import get_db_manager, Chat, CostTracking
from keprompt.ModelManager import ModelManager
from keprompt.config import get_config
from keprompt.AiPrompt import AiCall, AiResult, AiMessage
from keprompt.keprompt_logger import LogMode, StandardLogger
from keprompt.keprompt_vm import VM
from keprompt.version import __version__


class LegacyChatManager:
    """High-level Chat operations (formerly SessionManager)."""

    def __init__(self, args: argparse.Namespace = None):
        self.args = args
        self.db_manager = get_db_manager()
        self._hostname = socket.gethostname()
        self._git_commit = self._get_git_commit()

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # Short hash
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    # --------------------------------------------------------------------- #
    #  Serialisation helpers
    # --------------------------------------------------------------------- #
    def _make_serializable(self, obj):
        """Make an object JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(i) for i in obj]
        if hasattr(obj, "__class__") and obj.__class__.__name__ == "AiModel":
            return str(obj)
        if hasattr(obj, "__class__") and "Path" in obj.__class__.__name__:
            return str(obj)
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

    # --------------------------------------------------------------------- #
    #  Chat name generation
    # --------------------------------------------------------------------- #
    # def generate_session_name(
    #     self,
    #     prompt_name: str = None,
    #     prompt_version: str = None,
    #     chat_id: str = None,
    #     process_id: int = None,
    # ) -> str:
    #     """Generate automatic session name using our agreed format."""
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     process_id = process_id or os.getpid()
    #
    #     if prompt_name:
    #         sanitized_name = "".join(
    #             c if c.isalnum() or c in "_-" else "_" for c in prompt_name
    #         ).strip("_")
    #     else:
    #         sanitized_name = "session"
    #
    #     sanitized_version = (
    #         prompt_version.replace(".", "_") if prompt_version else "0_0_0"
    #     )
    #     return (
    #         f"{sanitized_name}_v{sanitized_version}_{timestamp}_{process_id}"
    #     )
    #
    # --------------------------------------------------------------------- #
    #  Persistence helpers
    # --------------------------------------------------------------------- #
    def save_session(self, vm) -> str:
        """Save chat from VM state."""

        # Prepare session data
        messages_json = json.dumps(vm.prompt.to_json())

        # Prepare VM state
        vm_state = {
            "ip": vm.ip,
            "model_name": vm.model_name,
            "company": vm.model.company if vm.model else "",
            "provider": (vm.model.provider if getattr(vm, "model", None) else vm.provider),
            "interaction_no": vm.interaction_no,
            "created": datetime.now().isoformat(),
            "log_mode": vm.log_mode.name,
            "vm_debug": vm.vm_debug,
            "exec_debug": vm.exec_debug,
            # runtime counters
            "toks_in": getattr(vm, "toks_in", 0),
            "toks_out": getattr(vm, "toks_out", 0),
            "cost_in": float(getattr(vm, "cost_in", 0.0)),
            "cost_out": float(getattr(vm, "cost_out", 0.0)),
            # prompt meta
            "prompt_name": getattr(vm, "prompt_name", None),
            "prompt_version": getattr(vm, "prompt_version", None),
        }
        vm_state_json = json.dumps(vm_state)

        # Prepare variables (make serializable)
        serializable_vars = self._make_variables_serializable(vm.vdict)
        variables_json = json.dumps(serializable_vars)

        # Prepare metadata
        metadata = {
            "prompt_name": vm.prompt_name or "Unknown",
            "prompt_version": vm.prompt_version or "0.0.0",
            "prompt_filename": vm.filename,
            "hostname": self._hostname,
            "git_commit": self._git_commit,
            "total_api_calls": vm.interaction_no,
            "total_tokens_in": vm.toks_in,
            "total_tokens_out": vm.toks_out,
            "total_cost": float(vm.cost_in + vm.cost_out),
        }

        # Prepare statements
        statements_json = json.dumps(vm.serialize_statements())

        # Save to database
        self.db_manager.save_chat(
            chat_id=vm.prompt_uuid,
            chat_name="",  # kept for compatibility
            messages_json=messages_json,
            vm_state_json=vm_state_json,
            variables_json=variables_json,
            statements_json=statements_json,
            **metadata,
        )

        # Save any pending cost records
        for msg_no, cost_data in vm.pending_costs:
            self.db_manager.save_cost_tracking(
                chat_id=vm.prompt_uuid, msg_no=msg_no, **cost_data
            )
        vm.pending_costs = []  # Clear after saving

        return vm.prompt_uuid

    # def save_cost_tracking(
    #     self,
    #     vm,
    #     msg_no: int,
    #     call_id: str,
    #     tokens_in: int,
    #     tokens_out: int,
    #     cost_in: float,
    #     cost_out: float,
    #     elapsed_time: float,
    #     model: str,
    #     provider: str,
    #     success: bool = True,
    #     error_message: str = None,
    #     **kwargs,
    # ) -> CostTracking:
    #     """Save cost tracking data."""
    #     cost_data = {
    #         "call_id": call_id,
    #         "tokens_in": tokens_in,
    #         "tokens_out": tokens_out,
    #         "cost_in": float(cost_in),
    #         "cost_out": float(cost_out),
    #         "estimated_costs": float(cost_in + cost_out),
    #         "elapsed_time": float(elapsed_time),
    #         "model": model,
    #         "provider": provider,
    #         "success": success,
    #         "error_message": error_message,
    #         "prompt_semantic_name": vm.prompt_name,
    #         "prompt_version_tracking": vm.prompt_version,
    #         "expected_params": json.dumps(vm.expected_params)
    #         if vm.expected_params
    #         else None,
    #         "execution_mode": getattr(
    #             vm, "log_mode", "production"
    #         ).name.lower()
    #         if hasattr(getattr(vm, "log_mode", None), "name")
    #         else "production",
    #         "parameters": json.dumps(self._make_serializable(vm.vdict))
    #         if vm.vdict
    #         else None,
    #         "environment": os.getenv("ENVIRONMENT", "development"),
    #         **kwargs,
    #     }
    #
    #     return self.db_manager.save_cost_tracking(
    #         chat_id=vm.prompt_uuid, msg_no=msg_no, **cost_data
    #     )

    # --------------------------------------------------------------------- #
    #  Loading helpers
    # --------------------------------------------------------------------- #
    def load_vm(self, chat_id: str) -> Optional[VM]:
        """Load and populate a VM instance from chat data."""
        session_db = self.get_session(chat_id)
        if not session_db:
            return None

        session = session_db["session"]
        messages_data = session_db["messages"]
        variables_data = session_db["variables"]

        # Create new VM instance
        vm = VM(
            filename=None,  # Will be set from session
            global_vars={},
            log_mode=LogMode.PRODUCTION,  # Default, will be overridden if saved
        )

        # Preserve identity continuity
        vm.prompt_uuid = chat_id

        # Restore VM state from database
        vm_state = json.loads(session.vm_state_json) if session.vm_state_json else {}
        vm.ip = vm_state.get("ip", 0)
        vm.model_name = vm_state.get("model_name", "")
        vm.provider = vm_state.get("provider", vm.provider)
        vm.interaction_no = vm_state.get("interaction_no", 0)
        # counters
        vm.toks_in = vm_state.get("toks_in", 0)
        vm.toks_out = vm_state.get("toks_out", 0)
        vm.cost_in = vm_state.get("cost_in", 0.0)
        vm.cost_out = vm_state.get("cost_out", 0.0)
        # prompt meta
        vm.prompt_name = vm_state.get("prompt_name", vm.prompt_name)
        vm.prompt_version = vm_state.get("prompt_version", vm.prompt_version)

        # Restore LLM configuration if we have model info
        if vm.model_name:
            if vm.model_name in ModelManager.models:
                vm.model = ModelManager.get_model(vm.model_name)
                # Set up basic LLM configuration
                vm.llm = {"model": vm.model_name}
                vm.prompt.company = vm.model.company
                vm.prompt.model = vm.model_name
                vm.prompt.provider = vm.model.provider
                vm.provider = vm.model.provider

                # Get API key
                try:
                    config = get_config()
                    api_key = config.get_api_key(vm.model.provider)
                    if api_key:
                        vm.llm["API_KEY"] = api_key
                        vm.api_key = api_key
                        vm.prompt.api_key = api_key
                except Exception as e:
                    # Leave API key unset; will be obtained on-demand
                    if hasattr(vm, "logger") and isinstance(vm.logger, StandardLogger):
                        vm.logger.warning(f"API key not restored for provider {vm.model.provider}: {e}")
            else:
                # Model not found in registry; keep model_name and provider from state
                vm.model = None
        else:
            # No model info saved
            vm.model = None

        # Restore messages (universal format)
        vm.prompt.messages = []

        for msg_data in messages_data:
            role = msg_data.get("role", "")
            content_data = msg_data.get("content", [])

            # Reconstruct message parts
            content_parts = []
            for part_data in content_data:
                part_type = part_data.get("type", "")

                if part_type == "text":
                    content_parts.append(
                        AiTextPart(vm=vm, text=part_data.get("text", ""))
                    )
                elif part_type == "tool":
                    content_parts.append(
                        AiCall(
                            vm=vm,
                            name=part_data.get("name", ""),
                            arguments=part_data.get("arguments", {}),
                            id=part_data.get("id", ""),
                        )
                    )
                elif part_type == "tool_result":
                    content_parts.append(
                        AiResult(
                            vm=vm,
                            name=part_data.get("name", ""),
                            id=part_data.get("tool_use_id", ""),
                            result=part_data.get("content", ""),
                        )
                    )

            # Add message to prompt
            vm.prompt.messages.append(
                AiMessage(vm=vm, role=role, content=content_parts)
            )

        # Restore variables
        vm.vdict.update(variables_data)

        # Restore original filename from session metadata
        if session.prompt_filename:
            vm.filename = session.prompt_filename

        # Restore statements if available
        statements_json = (
            session.statements_json
            if hasattr(session, "statements_json")
            else None
        )
        if statements_json:
            statements_data = json.loads(statements_json)
            vm.deserialize_statements(statements_data)

        # Restore logging configuration from vm_state
        if "log_mode" in vm_state:
            vm.log_mode = LogMode[vm_state["log_mode"]]
        if "vm_debug" in vm_state:
            vm.vm_debug = vm_state["vm_debug"]
        if "exec_debug" in vm_state:
            vm.exec_debug = vm_state["exec_debug"]

        # Reinitialize logger with restored log_mode
        prompt_name = (
            os.path.splitext(os.path.basename(vm.filename))[0]
            if vm.filename
            else "session"
        )
        vm.logger = StandardLogger(prompt_name=prompt_name, mode=vm.log_mode)

        return vm

    # --------------------------------------------------------------------- #
    #  Query helpers
    # --------------------------------------------------------------------- #
    def get_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat with all related data."""
        return self.db_manager.get_chat_with_costs(chat_id)

    def list_sessions(self, limit: int = 100) -> list:
        """List recent sessions."""
        sessions = self.db_manager.list_chats(limit=limit)
        return [
            {
                "chat_id": conv.chat_id,
                "created_timestamp": (
                    conv.created_timestamp.isoformat()
                    if conv.created_timestamp
                    else ""
                ),
                "prompt_name": conv.prompt_name,
                "prompt_version": conv.prompt_version,
                "prompt_filename": conv.prompt_filename,
                "total_cost": float(conv.total_cost),
                "total_api_calls": conv.total_api_calls,
            }
            for conv in sessions
        ]

    def delete_session(self, chat_id: str) -> bool:
        """Delete chat and all related data."""
        return self.db_manager.delete_chat(chat_id)

    def cleanup_sessions(self, max_days: int = None, max_count: int = None, max_size_gb: float = None, ) -> Dict[str, int]:
        """Clean up old sessions."""
        return self.db_manager.cleanup_old_chats(
            max_days=max_days,
            max_count=max_count,
            max_size_gb=max_size_gb,
        )

    def execute_get(self):
        chat_id = getattr(self.args, "session", None)
        limit = getattr(self.args, "limit", None)

        # Pretty output: return Rich tables when requested
        if getattr(self.args, "pretty", False):
            if chat_id:
                data = self.get_session(chat_id)
                title = f"Chat Details | {chat_id}"
                table = Table(title=title)
                table.add_column("Field", style="cyan", no_wrap=True)
                table.add_column("Value", style="green")

                def _fmt(v):
                    try:
                        if isinstance(v, (dict, list)):
                            return json.dumps(v, default=str)
                        if hasattr(v, "isoformat"):
                            return v.isoformat()
                        return str(v)
                    except Exception:
                        return str(v)

                if isinstance(data, dict):
                    for k, v in data.items():
                        table.add_row(str(k), _fmt(v))
                else:
                    table.add_row("data", _fmt(data))
                return table
            else:
                sessions = self.list_sessions(limit=limit or 100)
                table = Table(title="Recent Sessions")
                table.add_column("Chat ID", style="cyan", no_wrap=True)
                table.add_column("Created", style="magenta")
                table.add_column("Prompt", style="green")
                table.add_column("Version", style="yellow", justify="right")
                table.add_column("API Calls", style="blue", justify="right")
                table.add_column("Total Cost", style="white", justify="right")

                for s in sessions:
                    sid = s.get("chat_id", "")
                    created = s.get("created_timestamp", "")
                    prompt = s.get("prompt_name", "")
                    ver = str(s.get("prompt_version", ""))
                    calls = str(s.get("total_api_calls", ""))
                    cost = f"{float(s.get('total_cost', 0.0)):.6f}"
                    table.add_row(sid, created, prompt, ver, calls, cost)
                return table

        # Default: JSON/text structures
        if chat_id:
            return [self.get_session(chat_id)]
        if limit:
            return self.list_sessions(limit=limit)
        return self.list_sessions()


    def execute_delete(self):
        chat_id = getattr(self.args, "session", None)

        if chat_id:
            ok = self.delete_session(chat_id)
                msg = f"chat id {chat_id} {'deleted' if ok else 'not deleted'}"
            return  [msg]
        else:
            # Cleanup mode
            max_days = getattr(self.args, "max_days", None)
            max_count = getattr(self.args, "max_count", None)
            max_size_gb = getattr(self.args, "max_size_gb", None)
            result = self.cleanup_sessions(
                max_days=max_days,
                max_count=max_count,
                max_size_gb=max_size_gb,
            )
            return result

    def success(self, vm: VM, elapsed_time: float, params_dict: dict=None) -> dict:
        # Extract last assistant textual response
        ai_response = ""
        if getattr(vm, "prompt", None) and vm.prompt.messages:
            for message in reversed(vm.prompt.messages):
                if message.role == "assistant" and getattr(message, "content", None):
                    for part in message.content:
                        if hasattr(part, "text") and part.text:
                            ai_response = part.text
                            break
                    break
        if not ai_response and hasattr(vm, "last_response"):
            ai_response = vm.last_response

        metadata = {
            "total_cost": float(getattr(vm, "cost_in", 0.0) + getattr(vm, "cost_out", 0.0)),
            "tokens_in": getattr(vm, "toks_in", 0),
            "tokens_out": getattr(vm, "toks_out", 0),
            "elapsed_time": elapsed_time,
            "model": getattr(vm, "model_name", ""),
            "provider": getattr(getattr(vm, "model", None), "provider", getattr(vm, "provider", "")),
            "api_calls": getattr(vm, "interaction_no", 0),
        }

        return {
            "success": True,
            "chat_id": vm.prompt_uuid,
            "ai_response": ai_response,
            "metadata": metadata,
            "params": params_dict,
        }


    def colorize(self, role: str, txt: str) -> str:
        """Colorize text for pretty output."""
        role_color_map = {
            'system': 'cyan',
            'user': 'green',
            'assistant': 'yellow',
            'tool': 'cyan',
            'tool_result': 'cyan'
        }
        clr = role_color_map.get(role, 'white')
        return f"[{clr}]{txt}[/]"

    def execute_create(self):
        """Create a new session by executing a prompt once and persisting the VM.
        Returns a compact payload with chat_id, last AI response, metadata and params.
        """
        from .keprompt_vm import PromptResolutionError

        prompt_ref = getattr(self.args, "prompt", None)
        param_pairs = getattr(self.args, "param", None)  # list of [name, value]
        if not param_pairs:
            param_pairs = []

        # Helper to fail consistently
        def fail(msg: str):
            return [{
                "success": False,
                "error": msg,
                "timestamp": datetime.now().isoformat(),
            }]

        if not prompt_ref:
            return fail("--prompt is required")


        params_dict = {str(k): v for k, v in param_pairs} # Convert list of (name, value) pairs to dict

        # Instantiate VM with internal prompt resolution and default globals
        try:
            vm = VM(prompt_ref=prompt_ref, params=params_dict, log_mode=LogMode.PRODUCTION)
        except PromptResolutionError as e:
            return fail(str(e))
        except Exception as e:
            return fail(f"Failed to initialize VM: {e}")

        start_time = datetime.now()
        try:
            vm.execute()
        except Exception as e:
            return fail(f"Execution failed: {e}")
        end_time = datetime.now()

        # Persist the new session
        self.save_session(vm)

        # Extract last assistant textual response
        if self.args.pretty:
            table = Table(title=f"Conversation {vm.prompt_uuid}[{vm.prompt_name}:{vm.prompt_version}]")
            table.add_column("Role", style="cyan", no_wrap=True)
            table.add_column("Message", style="green")

            for msg in vm.prompt.messages:
                role = msg.role
                txt = ''
                for part in msg.content:
                    if hasattr(part, "text") and part.text:
                        txt += f"{part.text}\n"
                md = Markdown(txt[:-1])
                table.add_row(self.colorize(role,role), md)

            return table


        return self.success(vm=vm, elapsed_time=(end_time - start_time).total_seconds(), params_dict=params_dict)

    def execute_update(self):
        chat_id = getattr(self.args, "session", None)
        answer = getattr(self.args, "answer", None)

        # Load VM from existing session
        vm = self.load_vm(chat_id)
        if not vm:
            return f"Chat {chat_id} not found or failed to load"

        vm.add_statement(keyword=".user", value=answer)
        vm.add_statement(keyword=".exec", value='')
        start_time = datetime.now()
        vm.execute()
        end_time = datetime.now()
        self.save_session(vm)
        if self.args.pretty:
            table = Table(title=f"Conversation {vm.prompt_uuid}[{vm.prompt_name}:{vm.prompt_version}]")
            table.add_column("Role", style="cyan", no_wrap=True)
            table.add_column("Message", style="green")

            for msg in vm.prompt.messages:
                role = msg.role
                txt = ''
                for part in msg.content:
                    if hasattr(part, "text") and part.text:
                        txt += f"{part.text}\n"
                md = Markdown(txt[:-1])
                table.add_row(self.colorize(role,role), md)

            return table


        return self.success(vm=vm, elapsed_time=(end_time - start_time).total_seconds())

    # --------------------------------------------------------------------- #
    #  Core CLI entry point – always returns JSON
    # --------------------------------------------------------------------- #
    def execute(self):
        """Execute command-line interface and always return a JSON payload."""

        cmd = self.args.session_command

        # Helper to build a standard JSON result
        def make_result(success: bool, data, timestamp=None):
            return json.dumps(
                {
                    "success": success,
                    "data": data,
                    "timestamp": timestamp or datetime.now().isoformat(),
                }
            )

        data = "unknown command"
        timestamp = datetime.now().isoformat()
        success = True
        try:
            if cmd == "get":    data = self.execute_get()
            if cmd == 'delete': data = self.execute_delete()
            if cmd == "create": data = self.execute_create()
            if cmd == "update": data = self.execute_update()
        except Exception as e:
            success = False
            data = str(e)

        return data


    @staticmethod
    def _make_variables_serializable(variables: Dict[str, Any]) -> Dict[str, Any]:
        """Make variables JSON serializable by converting complex objects to strings"""
        serializable_vars = {}
        for key, value in variables.items():
            if hasattr(value, "__class__") and value.__class__.__name__ == "AiModel":
                serializable_vars[key] = str(value)
            elif hasattr(value, "__class__") and "Path" in value.__class__.__name__:
                serializable_vars[key] = str(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                serializable_vars[key] = value
            else:
                try:
                    json.dumps(value)
                    serializable_vars[key] = value
                except (TypeError, ValueError):
                    serializable_vars[key] = str(value)
        return serializable_vars


# Backward-compatible helper for modules that import get_session_manager
# Returns a ChatManager instance from the new chat_manager module; args are optional and can be injected later.
def get_session_manager():
    raise RuntimeError("SessionManager is removed. Use ChatManager (from keprompt.chat_manager) and 'chat' commands.")

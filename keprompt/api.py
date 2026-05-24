"""
JSON API module for keprompt - provides REST-style commands that return structured JSON data.
This module implements the core data layer that separates business logic from presentation.
"""
import argparse
# Import the global output format flag
import os
from datetime import datetime
from typing import Dict, Any

from rich.table import Table

from . import FunctionSpace
from .ModelManager import ModelManager
from .Prompt import PromptManager
from .database import DatabaseManager
from .chat_manager import ChatManager
from .db_cli import init_database, delete_database, truncate_database

from rich.console import Console

console = Console()




class ProviderManager():
    """Handles provider commands"""
    
    @classmethod
    def register_cli(cls, parent_subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
        parser = parent_subparsers.add_parser(
            "provider",
            aliases=["providers"],
            parents=[parent_parser],
            help="Provider operations",
        )
        subparsers = parser.add_subparsers(dest="provider_command", required=True)
        subparsers.add_parser(
            "get",
            aliases=["list", "show"],
            parents=[parent_parser],
            help="List all providers",
        )

    def __init__(self, args: argparse.Namespace):
        self.args = args

    def execute(self):
        cmd = self.args.provider_command

        if cmd in ('get', 'list', 'show'):
            # Ensure models are loaded
            ModelManager._load_all_models()

            # Get unique providers with their model counts
            providers = {}
            for model in ModelManager.models.values():
                provider = model.provider
                if provider not in providers:
                    providers[provider] = {
                        "name": provider,
                        "models_count": 0
                    }
                providers[provider]["models_count"] += 1

            provider_list = sorted(providers.values(), key=lambda x: x["name"])

            # Return JSON with object_type for OutputFormatter
            return {
                "success": True,
                "object_type": "provider_list",
                "data": provider_list,
                "timestamp": datetime.now().isoformat()
            }

        return {"success": False, "error": f"Unknown provider command: {cmd}", "timestamp": datetime.now().isoformat()}


class FunctionManager():
    """Handles function commands """
    
    @classmethod
    def register_cli(cls, parent_subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
        parser = parent_subparsers.add_parser(
            "functions",
            aliases=["function"],
            parents=[parent_parser],
            help="Function operations",
        )
        subparsers = parser.add_subparsers(dest="functions_command", required=True)
        subparsers.add_parser(
            "get",
            aliases=["list", "show"],
            parents=[parent_parser],
            help="List available functions",
        )
        subparsers.add_parser(
            "update",
            parents=[parent_parser],
            help="Update functions",
        )

    def __init__(self, args:argparse.Namespace):
        self.args = args


    def execute(self):
        cmd = self.args.functions_command

        # Return JSON data - OutputFormatter will handle pretty display
        return {
            "success": True,
            "object_type": "function_list",
            "data": FunctionSpace.functions.tools_array,
            "timestamp": datetime.now().isoformat()
        }


def handle_json_command(args: argparse.Namespace) -> dict[str, Any]:
    """Handle JSON API commands and return exit code"""
    try:
        command = args.command

        # Normalize singular/plural and route to appropriate manager
        if command in ('prompt', 'prompts'):
            cmd_manager = PromptManager(args)
        elif command in ('models', 'model'):
            cmd_manager = ModelManager(args)
        elif command in ('provider', 'providers'):
            cmd_manager = ProviderManager(args)
        elif command in ('functions', 'function'):
            cmd_manager = FunctionManager(args)
        elif command in ('chat', 'chats', 'conversation', 'conversations'):
            cmd_manager = ChatManager(args)
        elif command in ('database', 'databases'):
            cmd_manager = DatabaseManager(args)
        elif command in ('init', 'workspace'):
            from .workspace_manager import WorkspaceManager
            cmd_manager = WorkspaceManager(args)
        else:
            raise Exception(f"Unknown Object '{command}'")

        response = cmd_manager.execute()
        # here we need to work out print format...

        return response

    except Exception as e:
        etext = str(e)
        src = ''
        lno = 0

        # Extract source and line info from traceback if available
        if hasattr(e, '__traceback__'):
            tb = e.__traceback__
            while tb:
                src = tb.tb_frame.f_code.co_filename
                lno = tb.tb_lineno
                tb = tb.tb_next

        response = {'success': False, 'source': f'{src}:{lno}', 'error': f'Command failed: {etext}', 'timestamp': datetime.now().isoformat()}
        return response

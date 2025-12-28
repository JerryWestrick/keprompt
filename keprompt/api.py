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
from .server_registry import sync_registry, get_server, list_servers, get_target_directories, stop_server, find_free_port

from rich.console import Console

class JSONResponse:
    """Standard JSON response format for all API commands"""
    
    @staticmethod
    def success(data: Any, message: str = None) -> Dict[str, Any]:
        """Create a successful JSON response"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        if message:
            response["message"] = message
        return response
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Any = None) -> Dict[str, Any]:
        """Create an error JSON response"""
        response = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }
        if error_code:
            response["error_code"] = error_code
        if details:
            response["details"] = details
        return response

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
            "list",
            aliases=["get", "show"],
            parents=[parent_parser],
            help="List all providers",
        )

    def __init__(self, args: argparse.Namespace):
        self.args = args

    def execute(self):
        cmd = self.args.provider_command

        if cmd in ('list', 'get', 'show'):
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

            if getattr(self.args, "pretty", False):
                table = Table(title="Available Providers")
                table.add_column("Provider", style="cyan", no_wrap=True)
                table.add_column("Model Count", style="green", justify="right")

                # Provider color mapping
                provider_colors = {
                    'openrouter': 'yellow',
                    'openai': 'green',
                    'anthropic': 'magenta',
                    'gemini': 'red',
                    'google': 'red',
                    'mistral': 'bright_yellow',
                    'xai': 'white',
                    'deepseek': 'blue',
                }
                
                for provider in provider_list:
                    provider_name = provider["name"]
                    color = provider_colors.get(provider_name.lower(), 'cyan')
                    colored_name = f"[{color}]{provider_name}[/{color}]"
                    table.add_row(colored_name, str(provider["models_count"]))

                return table

            # default: JSON
            return {"success": True, "data": provider_list, "timestamp": datetime.now().isoformat()}

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

        if getattr(self.args, "pretty", False):
            table = Table(title="Available Functions")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description/Parameters", style="green")

            for tool in FunctionSpace.functions.tools_array:
                function = tool['function']
                name = function['name']
                description = function['description']

                table.add_row(name, description,)
                for k, v in function.get('parameters', {}).get('properties', {}).items():
                    table.add_row("", f"[bold blue]{k:10}[/]: {v.get('description', '')}")

                table.add_row("", "")

            return table

        # default: text
        return {"success": True, "data": FunctionSpace.functions.tools_array, "timestamp": datetime.now().isoformat()}


class ServerManager:
    """Handles server commands"""
    
    @classmethod
    def register_cli(cls, parent_subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
        parser = parent_subparsers.add_parser(
            "server",
            parents=[parent_parser],
            help="HTTP server operations",
        )
        subparsers = parser.add_subparsers(dest="server_command", required=True)

        def add_server_scope_args(p):
            scope_group = p.add_mutually_exclusive_group()
            scope_group.add_argument("--directory", help="Directory path (default: current directory)")
            scope_group.add_argument("--all", action="store_true", help="Apply to all registered servers")

        start = subparsers.add_parser("start", parents=[parent_parser], help="Start HTTP server")
        add_server_scope_args(start)
        start.add_argument("--port", type=int, help="Port (auto-assigned if not specified)")
        start.add_argument("--web-gui", action="store_true", help="Enable web GUI")
        start.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
        start.add_argument("--host", default="localhost", help="Host to bind (default: localhost)")

        listing = subparsers.add_parser("list", parents=[parent_parser], help="List servers")
        add_server_scope_args(listing)
        listing.add_argument("--active-only", action="store_true", help="Show only running servers")

        status = subparsers.add_parser("status", parents=[parent_parser], help="Check server status")
        add_server_scope_args(status)

        stop = subparsers.add_parser("stop", parents=[parent_parser], help="Stop server")
        add_server_scope_args(stop)
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
    
    def execute(self):
        """Execute server command"""
        cmd = self.args.server_command
        
        # Auto-sync registry before every operation
        sync_registry()
        
        if cmd == 'start':
            return self._start_server()
        elif cmd == 'list':
            return self._list_servers()
        elif cmd == 'status':
            return self._status_servers()
        elif cmd == 'stop':
            return self._stop_servers()
        else:
            return JSONResponse.error(f"Unknown server command: {cmd}")
    
    def _start_server(self):
        """Start HTTP server"""
        from pathlib import Path
        from .http_server import run_http_server

        # Validate: cannot use --all with start
        if getattr(self.args, 'all', False):
            return JSONResponse.error(
                "Cannot start all servers at once. "
                "Start each server individually with 'keprompt server start' "
                "or 'keprompt server start --directory <path>'",
                error_code="INVALID_OPERATION"
            )
        
        # Get target directory
        directory = self.args.directory if hasattr(self.args, 'directory') and self.args.directory else str(Path.cwd().resolve())
        directory = str(Path(directory).resolve())
        
        # Check if already running
        existing = get_server(directory)
        if existing and existing.status == 'running':
            return JSONResponse.error(
                f"Server already running for {directory}",
                error_code="ALREADY_RUNNING",
                details={
                    "directory": directory,
                    "port": existing.port,
                    "pid": existing.pid
                }
            )
        
        # Find port
        port = self.args.port if hasattr(self.args, 'port') and self.args.port else find_free_port()
        
        # Build server args
        server_args = [
            '--host', self.args.host if hasattr(self.args, 'host') else 'localhost',
            '--port', str(port)
        ]
        
        if getattr(self.args, 'web_gui', False):
            server_args.append('--web-gui')
        if getattr(self.args, 'reload', False):
            server_args.append('--reload')
        
        # Start server (this will not return until server stops)
        try:
            run_http_server(args=server_args, working_directory=directory)
            return JSONResponse.success({
                "started": True,
                "directory": directory,
                "port": port
            })
        except Exception as e:
            return JSONResponse.error(f"Failed to start server: {str(e)}")
    
    def _list_servers(self):
        """List servers"""
        all_servers = getattr(self.args, 'all', False)
        active_only = getattr(self.args, 'active_only', False)
        
        servers = list_servers(all_servers=all_servers, active_only=active_only)
        
        if getattr(self.args, "pretty", False):
            title = "Server Registry"
            if active_only:
                title += " (Active Only)"
            
            table = Table(title=title)
            table.add_column("Directory", style="cyan", no_wrap=False)
            table.add_column("Port", style="green", justify="right")
            table.add_column("PID", style="yellow", justify="right")
            table.add_column("Status", style="magenta")
            table.add_column("Started", style="dim")
            table.add_column("Web GUI", style="blue")
            
            for server in servers:
                status_style = "green" if server.status == 'running' else "red"
                table.add_row(
                    server.directory,
                    str(server.port),
                    str(server.pid),
                    f"[{status_style}]{server.status}[/]",
                    server.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Yes" if server.web_gui_enabled else "No"
                )
            
            if not servers:
                table.add_row("No servers found", "", "", "", "", "")
            
            return table
        
        # JSON format
        server_list = []
        for server in servers:
            server_list.append({
                "directory": server.directory,
                "port": server.port,
                "pid": server.pid,
                "status": server.status,
                "started_at": server.started_at.isoformat(),
                "died_at": server.died_at.isoformat() if server.died_at else None,
                "web_gui_enabled": server.web_gui_enabled
            })
        
        return JSONResponse.success(server_list)
    
    def _status_servers(self):
        """Check server status"""
        all_servers = getattr(self.args, 'all', False)
        directory = getattr(self.args, 'directory', None)
        
        directories = get_target_directories(all_servers, directory)
        
        statuses = []
        for dir_path in directories:
            server = get_server(dir_path)
            if server:
                statuses.append({
                    "directory": dir_path,
                    "port": server.port,
                    "pid": server.pid,
                    "status": server.status,
                    "running": server.status == 'running'
                })
            else:
                statuses.append({
                    "directory": dir_path,
                    "status": "not_registered",
                    "running": False
                })
        
        if getattr(self.args, "pretty", False):
            table = Table(title="Server Status")
            table.add_column("Directory", style="cyan")
            table.add_column("Status", style="magenta")
            table.add_column("Port", style="green")
            table.add_column("PID", style="yellow")
            
            for status in statuses:
                status_text = status["status"]
                status_style = "green" if status["running"] else "red"
                
                table.add_row(
                    status["directory"],
                    f"[{status_style}]{status_text}[/]",
                    str(status.get("port", "N/A")),
                    str(status.get("pid", "N/A"))
                )
            
            return table
        
        return JSONResponse.success(statuses)
    
    def _stop_servers(self):
        """Stop servers"""
        all_servers = getattr(self.args, 'all', False)
        directory = getattr(self.args, 'directory', None)
        
        directories = get_target_directories(all_servers, directory)
        
        results = []
        for dir_path in directories:
            success = stop_server(dir_path)
            results.append({
                "directory": dir_path,
                "stopped": success
            })
        
        if getattr(self.args, "pretty", False):
            table = Table(title="Stop Server Results")
            table.add_column("Directory", style="cyan")
            table.add_column("Result", style="magenta")
            
            for result in results:
                result_style = "green" if result["stopped"] else "red"
                result_text = "Stopped" if result["stopped"] else "Not running"
                
                table.add_row(
                    result["directory"],
                    f"[{result_style}]{result_text}[/]"
                )
            
            return table
        
        return JSONResponse.success(results)


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
        elif command == 'server':
            cmd_manager = ServerManager(args)
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

        response = {'success': False, 'source': f'{src}:{lno}', 'error': f'Command failed: {etext}'}
        return response

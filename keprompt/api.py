"""
JSON API module for keprompt - provides REST-style commands that return structured JSON data.
This module implements the core data layer that separates business logic from presentation.
"""
import argparse
import inspect
import json
# Import the global output format flag
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from rich.table import Table

from .ModelManager import ModelManager
from .Prompt import PromptManager
from .database import DatabaseManager
from .keprompt_functions import DefinedToolsArray, DefinedFunctions
from .keprompt_vm import VM
from .chat_manager import ChatManager
from .version import __version__


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


from dataclasses import dataclass, asdict


class ProviderManager():
    """Handles provider commands"""

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
                
                for provider in provider_list:
                    table.add_row(provider["name"], str(provider["models_count"]))
                
                return table
            
            # default: JSON
            return {"success": True, "data": provider_list, "timestamp": datetime.now().isoformat()}
        
        return {"success": False, "error": f"Unknown provider command: {cmd}", "timestamp": datetime.now().isoformat()}


class FunctionManager():
    """Handles function commands """

    def __init__(self, args:argparse.Namespace):
        self.args = args


    def execute(self):

        cmd = self.args.functions_command

        if getattr(self.args, "pretty", False):
            table = Table(title="Available Functions")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description/Parameters", style="green")

            for tool in DefinedToolsArray:
                function = tool['function']
                name = function['name']
                description = function['description']

                table.add_row(name, description,)
                for k, v in function.get('parameters', {}).get('properties', {}).items():
                    table.add_row("", f"[bold blue]{k:10}[/]: {v.get('description', '')}")

                table.add_row("", "")

            return table

        # default: text
        return {"success": True, "data": DefinedToolsArray, "timestamp": datetime.now().isoformat()}




class ResourceDiscovery:
    """Handles resource discovery commands (get prompts, models, providers, etc.)"""


    @staticmethod
    def get_prompts(pattern: str = "*") -> Dict[str, Any]:
        """Get all prompts with metadata, code, and statements"""
    @staticmethod
    def get_models(name_filter: str = None, provider_filter: str = None, company_filter: str = None) -> Dict[str, Any]:
        """Get all available models with filtering options"""
        try:
            models = []
            
            for model_name, model in ModelManager.models.items():
                # Apply filters
                if name_filter and name_filter.lower() not in model_name.lower():
                    continue
                if provider_filter and provider_filter.lower() not in model.provider.lower():
                    continue
                if company_filter and company_filter.lower() not in model.company.lower():
                    continue
                
                models.append({
                    "name": model_name,
                    "provider": model.provider,
                    "company": model.company,
                    "max_tokens": model.max_tokens,
                    "input_cost": model.input_cost,
                    "output_cost": model.output_cost,
                    "input_cost_per_million": model.input_cost * 1_000_000,
                    "output_cost_per_million": model.output_cost * 1_000_000,
                    "supports_vision": model.supports.get("vision", False),
                    "supports_functions": model.supports.get("function_calling", False),
                    "description": model.description
                })
            
            # Sort by provider, then company, then name
            models.sort(key=lambda x: (x["provider"], x["company"], x["name"]))
            
            return JSONResponse.success(models)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get models: {str(e)}")
    
    @staticmethod
    def get_providers() -> Dict[str, Any]:
        """Get all available providers (API services)"""
        try:
            providers = {}
            
            for model in ModelManager.models.values():
                provider = model.provider
                if provider not in providers:
                    providers[provider] = {
                        "name": provider,
                        "models_count": 0,
                        "companies": set()
                    }
                providers[provider]["models_count"] += 1
                providers[provider]["companies"].add(model.company)
            
            # Convert to list and clean up
            provider_list = []
            for provider_data in providers.values():
                provider_list.append({
                    "name": provider_data["name"],
                    "models_count": provider_data["models_count"],
                    "companies": sorted(list(provider_data["companies"]))
                })
            
            provider_list.sort(key=lambda x: x["name"])
            
            return JSONResponse.success(provider_list)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get providers: {str(e)}")
    
    @staticmethod
    def get_companies() -> Dict[str, Any]:
        """Get all available companies (model creators)"""
        try:
            companies = {}
            
            for model in ModelManager.models.values():
                company = model.company
                if company not in companies:
                    companies[company] = {
                        "name": company,
                        "models_count": 0,
                        "providers": set()
                    }
                companies[company]["models_count"] += 1
                companies[company]["providers"].add(model.provider)
            
            # Convert to list and clean up
            company_list = []
            for company_data in companies.values():
                company_list.append({
                    "name": company_data["name"],
                    "models_count": company_data["models_count"],
                    "providers": sorted(list(company_data["providers"]))
                })
            
            company_list.sort(key=lambda x: x["name"])
            
            return JSONResponse.success(company_list)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get companies: {str(e)}")
    
    @staticmethod
    def get_functions() -> Dict[str, Any]:
        """Get all available functions"""
        try:
            functions = []
            
            for tool in DefinedToolsArray:
                function = tool['function']
                
                # Extract parameters
                parameters = []
                if 'parameters' in function and 'properties' in function['parameters']:
                    for param_name, param_info in function['parameters']['properties'].items():
                        parameters.append({
                            "name": param_name,
                            "description": param_info.get('description', ''),
                            "type": param_info.get('type', 'string'),
                            "required": param_name in function['parameters'].get('required', [])
                        })
                
                functions.append({
                    "name": function['name'],
                    "description": function['description'],
                    "parameters": parameters
                })
            
            functions.sort(key=lambda x: x["name"])
            
            return JSONResponse.success(functions)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get functions: {str(e)}")



class SystemManagement:
    """Handles system management commands (workspace, models, builtins, database)"""
    
    @staticmethod
    def create_workspace() -> Dict[str, Any]:
        """Initialize workspace (prompts and functions directories)"""
        try:
            from .function_loader import FunctionLoader
            
            # Ensure directories exist
            os.makedirs('prompts', exist_ok=True)
            os.makedirs('logs', exist_ok=True)
            
            # Initialize functions
            loader = FunctionLoader()
            loader.ensure_functions_directory()
            
            return JSONResponse.success({
                "workspace_initialized": True,
                "directories_created": ["prompts", "logs", "prompts/functions"],
                "builtins_installed": True
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to create workspace: {str(e)}")
    
    @staticmethod
    def update_models(provider: str = None) -> Dict[str, Any]:
        """
        Update model definitions by downloading LiteLLM database.
        
        Note: The provider parameter is deprecated and will be ignored.
        All model updates now use the centralized LiteLLM database.
        """
        try:
            from .model_updater import update_models
            
            # Call update_models (provider parameter is now deprecated and ignored)
            update_models(target=provider)
            
            message = "Models updated successfully from LiteLLM database"
            if provider:
                message += f" (Note: --provider '{provider}' flag is deprecated and was ignored)"
            
            return JSONResponse.success({
                "updated": True,
                "message": message,
                "file": "prompts/functions/model_prices_and_context_window.json"
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to update models: {str(e)}")
    
    @staticmethod
    def get_builtins_status() -> Dict[str, Any]:
        """Check built-in functions status"""
        try:
            from .function_loader import FunctionLoader
            import subprocess
            
            loader = FunctionLoader()
            builtin_path = loader.functions_dir / loader.builtin_name
            
            if not builtin_path.exists():
                return {
                    "error": "Built-in functions not found",
                    "installed": False,
                    "message": "Built-in functions not found"
                }
            
            # Try to get version
            try:
                result = subprocess.run([str(builtin_path), "--version"], 
                                      capture_output=True, text=True, timeout=10)
                version = result.stdout.strip() if result.returncode == 0 else "unknown"
            except:
                version = "unknown"
            
            return {
                "installed": True,
                "version": version,
                "path": str(builtin_path)
            }
            
        except Exception as e:
            return JSONResponse.error(f"Failed to check builtins: {str(e)}")
    
    @staticmethod
    def update_builtins() -> Dict[str, Any]:
        """Update built-in functions"""
        try:
            from .function_loader import FunctionLoader
            
            loader = FunctionLoader()
            loader._install_builtin_functions()
            
            return JSONResponse.success({
                "updated": True,
                "message": "Built-in functions updated successfully"
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to update builtins: {str(e)}")
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Get database statistics and information"""
        try:
            from pathlib import Path
            import os
            
            db_path = Path("prompts/chats.db")
            
            if not db_path.exists():
                return JSONResponse.success({
                    "database_exists": False,
                    "message": "Database not found",
                    "path": str(db_path)
                })
            
            # Get basic file stats
            stats = os.stat(db_path)
            size_mb = stats.st_size / (1024 * 1024)
            
            # Try to get chat count
            try:
                from .chat_manager import ChatManager
                chat_manager = ChatManager()
                chats = chat_manager.list_chats(limit=1000)  # list chats
                chat_count = len(chats)
            except Exception:
                chat_count = "unknown"
            
            return JSONResponse.success({
                "database_exists": True,
                "path": str(db_path),
                "size_mb": round(size_mb, 2),
                "chat_count": chat_count,
                "last_modified": stats.st_mtime
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get database stats: {str(e)}")
    
    @staticmethod
    def create_database() -> Dict[str, Any]:
        """Initialize database and create tables"""
        try:
            from .db_cli import init_database
            
            # Call the existing function (it prints to console but we'll capture success)
            init_database()
            
            return JSONResponse.success({
                "database_initialized": True,
                "message": "Database initialized successfully"
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to create database: {str(e)}")
    
    @staticmethod
    def delete_database() -> Dict[str, Any]:
        """Delete entire database"""
        try:
            from .db_cli import delete_database
            
            # Call the existing function (it prints to console but we'll capture success)
            delete_database()
            
            return JSONResponse.success({
                "database_deleted": True,
                "message": "Database deleted successfully"
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to delete database: {str(e)}")
    
    @staticmethod
    def update_database(max_days: int = None, max_count: int = None, max_gb: float = None) -> Dict[str, Any]:
        """Clean up old chat (truncate database)"""
        try:
            from .db_cli import truncate_database
            
            # Call the existing function (it prints to console but we'll capture success)
            truncate_database(max_days=max_days, max_count=max_count, max_gb=max_gb)
            
            return JSONResponse.success({
                "database_truncated": True,
                "message": "Database cleanup completed",
                "parameters": {
                    "max_days": max_days,
                    "max_count": max_count,
                    "max_gb": max_gb
                }
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to update database: {str(e)}")



class ServerManager:
    """Handles server commands"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
    
    def execute(self):
        """Execute server command"""
        from .server_registry import (
            sync_registry, register_server, unregister_server, get_server,
            list_servers, find_free_port, stop_server, get_target_directories
        )
        from pathlib import Path
        
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
        from .server_registry import get_server, find_free_port
        from .http_server import run_http_server
        from pathlib import Path
        import sys
        
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
        from .server_registry import list_servers
        
        all_servers = getattr(self.args, 'all', False)
        active_only = getattr(self.args, 'active_only', False)
        
        servers = list_servers(all_servers=all_servers, active_only=active_only)
        
        if getattr(self.args, "pretty", False):
            from rich.table import Table
            
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
        from .server_registry import get_target_directories, get_server
        
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
            from rich.table import Table
            
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
        from .server_registry import get_target_directories, stop_server as stop_server_func
        
        all_servers = getattr(self.args, 'all', False)
        directory = getattr(self.args, 'directory', None)
        
        directories = get_target_directories(all_servers, directory)
        
        results = []
        for dir_path in directories:
            success = stop_server_func(dir_path)
            results.append({
                "directory": dir_path,
                "stopped": success
            })
        
        if getattr(self.args, "pretty", False):
            from rich.table import Table
            
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


def handle_json_command(args: argparse.Namespace) -> dict[str, Any] :
    """Handle JSON API commands and return exit code"""
    try:
        command = args.command

        # Normalize singular/plural and route to appropriate manager
        if   command in ('prompt', 'prompts'):
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

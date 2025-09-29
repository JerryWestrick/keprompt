"""
JSON API module for keprompt - provides REST-style commands that return structured JSON data.
This module implements the core data layer that separates business logic from presentation.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .AiRegistry import AiRegistry
from .keprompt_functions import DefinedToolsArray
from .keprompt_vm import VM
from .version import __version__


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


class ResourceDiscovery:
    """Handles resource discovery commands (get prompts, models, providers, etc.)"""
    
    @staticmethod
    def get_prompts(pattern: str = "*") -> Dict[str, Any]:
        """Get all prompts with metadata, code, and statements"""
        try:
            from .keprompt import glob_prompt
            
            prompt_files = glob_prompt(pattern)
            prompts = []
            
            for prompt_file in prompt_files:
                prompt_data = ResourceDiscovery._parse_prompt_file(str(prompt_file))
                prompts.append(prompt_data)
            
            return JSONResponse.success(prompts)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get prompts: {str(e)}")
    
    @staticmethod
    def _parse_prompt_file(prompt_file: str) -> Dict[str, Any]:
        """Parse a prompt file and extract metadata, code, and statements"""
        try:
            with open(prompt_file, 'r') as f:
                lines = f.readlines()
            
            # Parse .prompt statement for metadata
            metadata = {}
            if lines and lines[0].strip().startswith('.prompt '):
                try:
                    json_content = "{" + lines[0].strip()[8:] + "}"
                    metadata = json.loads(json_content)
                except json.JSONDecodeError:
                    pass
            
            # Extract source content
            source = ''.join(lines)
            
            return {
                "filename": os.path.basename(prompt_file),
                "path": prompt_file,
                "name": metadata.get("name", os.path.basename(prompt_file)),
                "version": metadata.get("version", ""),
                "params": metadata.get("params", {}),
                "metadata": metadata,
                "source": source,
                "line_count": len(lines)
            }
            
        except Exception as e:
            return {
                "filename": os.path.basename(prompt_file),
                "path": prompt_file,
                "error": f"Failed to parse file: {str(e)}"
            }
    
    @staticmethod
    def get_models(name_filter: str = None, provider_filter: str = None, company_filter: str = None) -> Dict[str, Any]:
        """Get all available models with filtering options"""
        try:
            models = []
            
            for model_name, model in AiRegistry.models.items():
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
            
            for model in AiRegistry.models.values():
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
            
            for model in AiRegistry.models.values():
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


class SessionManagement:
    """Handles session management commands (create, get, update, delete sessions)"""
    
    @staticmethod
    def _make_variables_serializable(variables: Dict[str, Any]) -> Dict[str, Any]:
        """Make variables JSON serializable by converting complex objects to strings"""
        serializable_vars = {}
        for key, value in variables.items():
            if hasattr(value, '__class__') and value.__class__.__name__ == 'AiModel':
                serializable_vars[key] = str(value)
            elif hasattr(value, '__class__') and 'Path' in value.__class__.__name__:
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
    
    @staticmethod
    def create_session(prompt_name: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a new session by executing a prompt"""
        try:
            import io
            import contextlib
            from .keprompt import glob_prompt, create_global_variables
            from .keprompt_logger import LogMode
            
            # Find prompt file
            prompt_files = glob_prompt(prompt_name)
            if not prompt_files:
                return JSONResponse.error(f"Prompt '{prompt_name}' not found")
            
            if len(prompt_files) > 1:
                return JSONResponse.error(f"Multiple prompts match '{prompt_name}': {[str(f) for f in prompt_files]}")
            
            prompt_file = str(prompt_files[0])
            
            # Prepare global variables
            global_variables = create_global_variables()
            if params:
                global_variables.update(params)
            
            # Capture stdout and stderr during execution
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                # Execute prompt
                vm = VM(prompt_file, global_variables, log_mode=LogMode.PRODUCTION)
                vm.parse_prompt()
                start_time = datetime.now()
                vm.execute()
                end_time = datetime.now()
            
            # Parse captured stdout
            captured_output = stdout_capture.getvalue()
            stdout_lines = [line.strip() for line in captured_output.split('\n') if line.strip()]
            
            # Get the final AI response from the conversation
            ai_response = ""
            if hasattr(vm, 'prompt') and vm.prompt and vm.prompt.messages:
                # Find the last assistant message
                for message in reversed(vm.prompt.messages):
                    if message.role == 'assistant':
                        # Extract text content from the message
                        if hasattr(message, 'content') and message.content:
                            for content_part in message.content:
                                if hasattr(content_part, 'text'):
                                    ai_response = content_part.text
                                    break
                        break
            
            # Fallback to last_response if available
            if not ai_response and hasattr(vm, 'last_response'):
                ai_response = vm.last_response
            
            # Calculate elapsed time
            elapsed_time = (end_time - start_time).total_seconds()
            
            # Build metadata
            metadata = {
                "total_cost": float(vm.cost_in + vm.cost_out) if hasattr(vm, 'cost_in') and hasattr(vm, 'cost_out') else 0.0,
                "tokens_in": vm.toks_in if hasattr(vm, 'toks_in') else 0,
                "tokens_out": vm.toks_out if hasattr(vm, 'toks_out') else 0,
                "elapsed_time": elapsed_time,
                "model": vm.model_name if hasattr(vm, 'model_name') else "",
                "provider": vm.model.provider if hasattr(vm, 'model') and vm.model else "",
                "api_calls": vm.interaction_no if hasattr(vm, 'interaction_no') else 0
            }
            
            return JSONResponse.success({
                "session_id": vm.prompt_uuid,
                "stdout": stdout_lines,
                "ai_response": ai_response,
                "metadata": metadata,
                "params": params or {},
                "vm_state": {
                    "ip": vm.ip if hasattr(vm, 'ip') else 0,
                    "model_name": vm.model_name if hasattr(vm, 'model_name') else "",
                    "company": vm.model.company if hasattr(vm, 'model') and vm.model else "",
                    "interaction_no": vm.interaction_no if hasattr(vm, 'interaction_no') else 0,
                    "created": datetime.now().isoformat()
                },
                "variables": SessionManagement._make_variables_serializable(vm.vdict) if hasattr(vm, 'vdict') else {}
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to create session: {str(e)}")
    
    @staticmethod
    def get_sessions() -> Dict[str, Any]:
        """Get all available sessions"""
        try:
            from .session_manager import get_session_manager
            
            session_manager = get_session_manager()
            sessions = session_manager.list_sessions(limit=100)
            
            return JSONResponse.success(sessions)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get sessions: {str(e)}")
    
    @staticmethod
    def get_session(session_id: str) -> Dict[str, Any]:
        """Get session details and history"""
        try:
            from .session_manager import get_session_manager
            
            session_manager = get_session_manager()
            session_data = session_manager.get_session(session_id)
            
            if session_data is None:
                return JSONResponse.error(f"Session '{session_id}' not found")
            
            # Convert session data to JSON-serializable format
            result = {
                'session_id': session_data['session'].session_id,
                'created_timestamp': session_data['session'].created_timestamp.isoformat(),
                'prompt_name': session_data['session'].prompt_name,
                'prompt_version': session_data['session'].prompt_version,
                'prompt_filename': session_data['session'].prompt_filename,
                'total_cost': float(session_data['session'].total_cost),
                'total_api_calls': session_data['session'].total_api_calls,
                'total_tokens_in': session_data['session'].total_tokens_in,
                'total_tokens_out': session_data['session'].total_tokens_out,
                'messages': session_data['messages'],
                'vm_state': session_data['vm_state'],
                'variables': session_data['variables'],
                'costs': [
                    {
                        'msg_no': cost.msg_no,
                        'call_id': cost.call_id,
                        'timestamp': cost.timestamp.isoformat(),
                        'tokens_in': cost.tokens_in,
                        'tokens_out': cost.tokens_out,
                        'cost_in': float(cost.cost_in),
                        'cost_out': float(cost.cost_out),
                        'estimated_costs': float(cost.estimated_costs),
                        'elapsed_time': float(cost.elapsed_time),
                        'model': cost.model,
                        'provider': cost.provider,
                        'success': cost.success,
                        'error_message': cost.error_message
                    }
                    for cost in session_data['costs']
                ]
            }
            
            return JSONResponse.success(result)
            
        except Exception as e:
            return JSONResponse.error(f"Failed to get session: {str(e)}")
    
    @staticmethod
    def update_session(session_id: str, answer: str) -> Dict[str, Any]:
        """Continue a session with a user answer"""
        try:
            import io
            import contextlib
            from .keprompt import create_global_variables
            from .keprompt_logger import LogMode
            from .keprompt_vm import make_statement
            from .AiPrompt import AiTextPart
            
            # Load existing session
            vm = VM(None, create_global_variables(), log_mode=LogMode.PRODUCTION)
            loaded = vm.load_session(session_id)
            
            if not loaded:
                return JSONResponse.error(f"Session '{session_id}' not found")
            
            # Continue conversation
            vm.prompt_uuid = session_id
            vm.prompt.add_message(vm=vm, role='user', content=[AiTextPart(vm=vm, text=answer)])
            
            # Create statements for continuation
            vm.statements = []
            vm.statements.append(make_statement(vm, 0, '.exec', ''))
            vm.statements.append(make_statement(vm, 1, '.print', '<<last_response>>'))
            vm.statements.append(make_statement(vm, 2, '.exit', ''))
            
            # Capture stdout and stderr during execution
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                # Execute continuation
                start_time = datetime.now()
                vm.execute()
                end_time = datetime.now()
            
            # Parse captured stdout
            captured_output = stdout_capture.getvalue()
            stdout_lines = [line.strip() for line in captured_output.split('\n') if line.strip()]
            
            # Get the final AI response from the conversation
            ai_response = ""
            if hasattr(vm, 'prompt') and vm.prompt and vm.prompt.messages:
                # Find the last assistant message
                for message in reversed(vm.prompt.messages):
                    if message.role == 'assistant':
                        # Extract text content from the message
                        if hasattr(message, 'content') and message.content:
                            for content_part in message.content:
                                if hasattr(content_part, 'text'):
                                    ai_response = content_part.text
                                    break
                        break
            
            # Fallback to last_response if available
            if not ai_response and hasattr(vm, 'last_response'):
                ai_response = vm.last_response
            
            # Calculate elapsed time
            elapsed_time = (end_time - start_time).total_seconds()
            
            # Build metadata
            metadata = {
                "total_cost": float(vm.cost_in + vm.cost_out) if hasattr(vm, 'cost_in') and hasattr(vm, 'cost_out') else 0.0,
                "tokens_in": vm.toks_in if hasattr(vm, 'toks_in') else 0,
                "tokens_out": vm.toks_out if hasattr(vm, 'toks_out') else 0,
                "elapsed_time": elapsed_time,
                "model": vm.model_name if hasattr(vm, 'model_name') else "",
                "provider": vm.model.provider if hasattr(vm, 'model') and vm.model else "",
                "api_calls": vm.interaction_no if hasattr(vm, 'interaction_no') else 0
            }
            
            return JSONResponse.success({
                "session_id": session_id,
                "user_message": answer,
                "stdout": stdout_lines,
                "ai_response": ai_response,
                "metadata": metadata,
                "vm_state": {
                    "ip": vm.ip if hasattr(vm, 'ip') else 0,
                    "model_name": vm.model_name if hasattr(vm, 'model_name') else "",
                    "company": vm.model.company if hasattr(vm, 'model') and vm.model else "",
                    "interaction_no": vm.interaction_no if hasattr(vm, 'interaction_no') else 0,
                    "created": datetime.now().isoformat()
                },
                "variables": SessionManagement._make_variables_serializable(vm.vdict) if hasattr(vm, 'vdict') else {}
            })
            
        except Exception as e:
            return JSONResponse.error(f"Failed to update session: {str(e)}")
    
    @staticmethod
    def delete_session(session_id: str) -> Dict[str, Any]:
        """Delete a session"""
        try:
            from .session_manager import SessionManager
            
            session_manager = SessionManager()
            success = session_manager.delete_session(session_id)
            
            if success:
                return JSONResponse.success({
                    "session_id": session_id,
                    "deleted": True
                })
            else:
                return JSONResponse.error(f"Failed to delete session '{session_id}'")
            
        except Exception as e:
            return JSONResponse.error(f"Failed to delete session: {str(e)}")


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
        """Update model definitions"""
        try:
            from .model_updater import update_models
            
            result = update_models(provider or "All")
            
            return JSONResponse.success({
                "provider": provider or "All",
                "updated": True,
                "message": "Models updated successfully"
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
                return JSONResponse.success({
                    "installed": False,
                    "message": "Built-in functions not found"
                })
            
            # Try to get version
            try:
                result = subprocess.run([str(builtin_path), "--version"], 
                                      capture_output=True, text=True, timeout=10)
                version = result.stdout.strip() if result.returncode == 0 else "unknown"
            except:
                version = "unknown"
            
            return JSONResponse.success({
                "installed": True,
                "version": version,
                "path": str(builtin_path)
            })
            
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
            
            db_path = Path("prompts/sessions.db")
            
            if not db_path.exists():
                return JSONResponse.success({
                    "database_exists": False,
                    "message": "Database not found",
                    "path": str(db_path)
                })
            
            # Get basic file stats
            stats = os.stat(db_path)
            size_mb = stats.st_size / (1024 * 1024)
            
            # Try to get session count
            try:
                from .session_manager import get_session_manager
                session_manager = get_session_manager()
                sessions = session_manager.list_sessions(limit=1000)  # Get a large number to count
                session_count = len(sessions)
            except:
                session_count = "unknown"
            
            return JSONResponse.success({
                "database_exists": True,
                "path": str(db_path),
                "size_mb": round(size_mb, 2),
                "session_count": session_count,
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
        """Clean up old sessions (truncate database)"""
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


def print_json_response(response: Dict[str, Any]) -> None:
    """Print JSON response to stdout"""
    print(json.dumps(response, indent=2, ensure_ascii=False))


def handle_json_command(args: List[str]) -> int:
    """Handle JSON API commands and return exit code"""
    if len(args) < 2:
        print_json_response(JSONResponse.error("Missing verb and resource"))
        return 1
    
    verb = args[0].lower()
    resource = args[1].lower()
    
    try:
        if verb == "get":
            if resource == "prompts":
                pattern = args[2] if len(args) > 2 else "*"
                response = ResourceDiscovery.get_prompts(pattern)
            elif resource == "models":
                # Parse optional filters
                name_filter = None
                provider_filter = None
                company_filter = None
                i = 2
                while i < len(args):
                    if args[i] == "--name" and i + 1 < len(args):
                        name_filter = args[i + 1]
                        i += 2
                    elif args[i] == "--provider" and i + 1 < len(args):
                        provider_filter = args[i + 1]
                        i += 2
                    elif args[i] == "--company" and i + 1 < len(args):
                        company_filter = args[i + 1]
                        i += 2
                    else:
                        i += 1
                response = ResourceDiscovery.get_models(name_filter, provider_filter, company_filter)
            elif resource == "providers":
                response = ResourceDiscovery.get_providers()
            elif resource == "companies":
                response = ResourceDiscovery.get_companies()
            elif resource == "functions":
                response = ResourceDiscovery.get_functions()
            elif resource == "sessions":
                response = SessionManagement.get_sessions()
            elif resource == "session":
                if len(args) < 3:
                    response = JSONResponse.error("Missing session ID")
                else:
                    response = SessionManagement.get_session(args[2])
            elif resource == "builtins":
                response = SystemManagement.get_builtins_status()
            elif resource == "database":
                response = SystemManagement.get_database_stats()
            else:
                response = JSONResponse.error(f"Unknown resource: {resource}")
        
        elif verb == "create":
            if resource == "workspace":
                response = SystemManagement.create_workspace()
            elif resource == "session":
                # Parse prompt name and parameters
                if len(args) < 4 or args[2] != "--prompt":
                    response = JSONResponse.error("Usage: create session --prompt <name> [--param key value]...")
                else:
                    prompt_name = args[3]
                    params = {}
                    i = 4
                    while i < len(args):
                        if args[i] == "--param" and i + 2 < len(args):
                            params[args[i + 1]] = args[i + 2]
                            i += 3
                        else:
                            i += 1
                    response = SessionManagement.create_session(prompt_name, params)
            elif resource == "database":
                response = SystemManagement.create_database()
            else:
                response = JSONResponse.error(f"Cannot create resource: {resource}")
        
        elif verb == "update":
            if resource == "models":
                provider = args[2] if len(args) > 2 else None
                response = SystemManagement.update_models(provider)
            elif resource == "builtins":
                response = SystemManagement.update_builtins()
            elif resource == "session":
                if len(args) < 5 or args[3] != "--answer":
                    response = JSONResponse.error("Usage: update session <session_id> --answer <message>")
                else:
                    session_id = args[2]
                    answer = " ".join(args[4:])  # Join remaining args as answer
                    response = SessionManagement.update_session(session_id, answer)
            elif resource == "database":
                # Parse optional parameters for database truncation
                max_days = None
                max_count = None
                max_gb = None
                i = 2
                while i < len(args):
                    if args[i] == "--max-days" and i + 1 < len(args):
                        max_days = int(args[i + 1])
                        i += 2
                    elif args[i] == "--max-count" and i + 1 < len(args):
                        max_count = int(args[i + 1])
                        i += 2
                    elif args[i] == "--max-gb" and i + 1 < len(args):
                        max_gb = float(args[i + 1])
                        i += 2
                    else:
                        i += 1
                response = SystemManagement.update_database(max_days, max_count, max_gb)
            else:
                response = JSONResponse.error(f"Cannot update resource: {resource}")
        
        elif verb == "delete":
            if resource == "session":
                if len(args) < 3:
                    response = JSONResponse.error("Missing session ID")
                else:
                    response = SessionManagement.delete_session(args[2])
            elif resource == "database":
                response = SystemManagement.delete_database()
            else:
                response = JSONResponse.error(f"Cannot delete resource: {resource}")
        
        else:
            response = JSONResponse.error(f"Unknown verb: {verb}")
        
        print_json_response(response)
        return 0 if response["success"] else 1
        
    except Exception as e:
        print_json_response(JSONResponse.error(f"Command failed: {str(e)}"))
        return 1

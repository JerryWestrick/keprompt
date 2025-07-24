import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil

from rich.console import Console

console = Console()


class FunctionLoader:
    """Handles loading and execution of external user-defined functions."""
    
    def __init__(self, functions_dir: str = "./prompts/functions"):
        self.functions_dir = Path(functions_dir)
        self.functions_json = self.functions_dir / "functions.json"
        self.builtin_name = "keprompt_builtins"
        
    def ensure_functions_directory(self) -> None:
        """Ensure functions directory exists and has built-in functions."""
        prompts_dir = Path("./prompts")
        
        # Create prompts directory if it doesn't exist
        if not prompts_dir.exists():
            prompts_dir.mkdir(parents=True)
            console.print(f"Created directory: {prompts_dir}")
            
        # Create functions directory if it doesn't exist
        if not self.functions_dir.exists():
            self.functions_dir.mkdir(parents=True)
            console.print(f"Notice: Creating {self.functions_dir} and installing built-in functions")
            self._install_builtin_functions()
            
    def _install_builtin_functions(self) -> None:
        """Install the built-in functions executable."""
        builtin_source = Path(__file__).parent / "keprompt_builtins.py"
        builtin_target = self.functions_dir / self.builtin_name
        
        if builtin_source.exists():
            shutil.copy(builtin_source, builtin_target)
            os.chmod(builtin_target, 0o755)
        else:
            console.print(f"Warning: Built-in functions source not found: {builtin_source}")
        
    def _needs_regeneration(self) -> bool:
        """Check if functions.json needs to be regenerated."""
        if not self.functions_json.exists():
            return True
            
        functions_json_mtime = self.functions_json.stat().st_mtime
        
        # Check if any executable is newer than functions.json
        for file_path in self.functions_dir.iterdir():
            if file_path.is_file() and os.access(file_path, os.X_OK):
                if file_path.stat().st_mtime > functions_json_mtime:
                    return True
                    
        return False
        
    def _discover_executables(self) -> List[Path]:
        """Discover executable files in functions directory."""
        executables = []
        if self.functions_dir.exists():
            for file_path in sorted(self.functions_dir.iterdir()):
                if file_path.is_file() and os.access(file_path, os.X_OK):
                    executables.append(file_path)
        return executables
        
    def _get_function_definitions(self, executable: Path) -> List[Dict[str, Any]]:
        """Get function definitions from an executable."""
        try:
            result = subprocess.run(
                [f"./{executable.name}", "--list-functions"],
                cwd=self.functions_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                console.print(f"Warning: {executable.name} doesn't support --list-functions")
                return []
                
        except subprocess.TimeoutExpired:
            console.print(f"Warning: {executable.name} timed out on --list-functions")
            return []
        except json.JSONDecodeError:
            console.print(f"Warning: {executable.name} returned invalid JSON")
            return []
        except Exception as e:
            console.print(f"Warning: Error calling {executable.name}: {e}")
            return []
            
    def _generate_functions_json(self) -> None:
        """Generate functions.json from all executables."""
        all_functions = []
        seen_functions = set()
        
        executables = self._discover_executables()
        
        for executable in executables:
            definitions = self._get_function_definitions(executable)
            
            for func_def in definitions:
                func_name = func_def.get("name")
                if func_name and func_name not in seen_functions:
                    # Add executable info to function definition
                    func_def["_executable"] = str(executable)
                    all_functions.append(func_def)
                    seen_functions.add(func_name)
                    
        # Write functions.json
        functions_data = {
            "functions": all_functions,
            "generated_at": str(Path.cwd()),
            "version": "1.0"
        }
        
        with open(self.functions_json, 'w') as f:
            json.dump(functions_data, f, indent=2)
            
    def load_functions(self) -> Dict[str, Any]:
        """Load function definitions and return tools array and function mapping."""
        self.ensure_functions_directory()
        
        if self._needs_regeneration():
            self._generate_functions_json()
            
        # Load functions.json
        if not self.functions_json.exists():
            return {"tools_array": [], "function_map": {}}
            
        with open(self.functions_json, 'r') as f:
            data = json.load(f)
            
        functions = data.get("functions", [])
        
        # Build tools array for LLM
        tools_array = []
        function_map = {}
        
        for func_def in functions:
            func_name = func_def["name"]
            executable = func_def["_executable"]
            
            # Create tool definition for LLM
            tool = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": func_def["description"],
                    "parameters": func_def["parameters"]
                }
            }
            tools_array.append(tool)
            
            # Map function name to executable
            function_map[func_name] = executable
            
        return {
            "tools_array": tools_array,
            "function_map": function_map
        }
        
    def execute_function(self, function_name: str, arguments: Dict[str, Any], function_map: Dict[str, str]) -> str:
        """Execute a function by calling its executable."""
        if function_name not in function_map:
            raise Exception(f"Function '{function_name}' not found")
            
        executable = function_map[function_name]
        
        if not os.path.exists(executable):
            raise Exception(f"Executable for function '{function_name}' not found: {executable}")
            
        if not os.access(executable, os.X_OK):
            raise Exception(f"Executable for function '{function_name}' is not executable: {executable}")
            
        try:
            # Execute: echo 'json_args' | ./executable function_name
            executable_name = Path(executable).name
            result = subprocess.run(
                [f"./{executable_name}", function_name],
                cwd=self.functions_dir,
                input=json.dumps(arguments),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or "Unknown error"
                raise Exception(f"Function '{function_name}' failed: {error_msg}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"Function '{function_name}' timed out")
        except Exception as e:
            raise Exception(f"Error executing function '{function_name}': {e}")

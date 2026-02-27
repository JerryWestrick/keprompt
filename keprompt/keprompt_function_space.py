from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Callable

from .terminal_output import terminal_output

# Capture the project directory where KePrompt was started
# (can be overridden for testing or special setups)
PROJECT_DIR = Path(os.environ.get("KEPROMPT_PROJECT_DIR", os.getcwd()))


class FunctionSpace:
    """
    FunctionSpace represents and manages a directory of function_providers.

    This rewritten version now:
      • Tracks ALL instances of FunctionSpace in a class-level registry
      • Creates the ONE KePrompt singletons eagerly at import time:
            FunctionSpace.functions → prompts/functions
      • Loads function definitions immediately
      • Builds tools_array and function_array
      • Exposes callable wrappers
      • Provides a .call(name, args) execution API
    """

    # ------------------------------------------------------------------
    # CLASS‑LEVEL REGISTRY
    # ------------------------------------------------------------------
    _instances: Dict[str, "FunctionSpace"] = {}

    @classmethod
    def get(cls, directory: str) -> "FunctionSpace":
        """
        Retrieve an existing FunctionSpace or create one if needed.
        This powers the eager singletons below.
        """
        directory = str(directory)
        if directory not in cls._instances:
            cls._instances[directory] = cls(directory)
        return cls._instances[directory]

    # EAGER SINGLETONS – created immediately when module imports
    functions: "FunctionSpace" = None  # assigned after class definition

    # ------------------------------------------------------------------
    # INSTANCE INITIALIZATION
    # ------------------------------------------------------------------
    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

        self.function_array: List[Dict[str, Any]] = []
        self.tools_array: List[Dict[str, Any]] = []
        self.functions: Dict[str, Callable[..., Any]] = {}

        # Load everything immediately
        import time
        start_time = time.time()
        providers = self._discover_function_providers()
        definitions = self._collect_function_provider_definitions(providers)
        self.function_array = definitions
        self.tools_array = self._build_tools_array(definitions)
        self._create_callable_wrappers(definitions)
        end_time = time.time()
        terminal_output.print(
            f"[FunctionSpace] Loaded {len(self.tools_array)} routines from '{self.directory}' in {end_time - start_time:.4f} seconds",
            markup=False,
        )

    # ------------------------------------------------------------------
    # DISCOVER EXECUTABLE FUNCTION PROVIDERS
    # ------------------------------------------------------------------
    def _discover_function_providers(self) -> List[Path]:
        """
        Locate all executable function_providers in the directory.
        Skips JSON/backup/metadata files.
        """
 
        providers = []
        for file in sorted(self.directory.iterdir()):
            # skip non-providers
            if file.suffix in {".json", ".backup"}:
                continue
            if file.name in {
                "functions.json",
                "model_prices_and_context_window.json",
                "model_prices_and_context_window.json.backup",
            }:
                continue
            if file.is_file() and os.access(file, os.X_OK):
                providers.append(file)
        return providers
    # ------------------------------------------------------------------
    # LOAD DEFINITIONS FROM EACH FUNCTION PROVIDER
    # ------------------------------------------------------------------
    def _collect_function_provider_definitions(
        self, function_providers: List[Path]
    ) -> List[Dict[str, Any]]:

        all_defs: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for fp in function_providers:
            defs = self._get_definitions_from_function_provider(fp)
            for d in defs:
                name = d.get("name")
                if name and name not in seen:
                    d["_executable"] = str(fp)
                    all_defs.append(d)
                    seen.add(name)

        return all_defs

    def _get_definitions_from_function_provider(self, fp: Path) -> List[Dict[str, Any]]:
        """
        Execute provider with --list-functions to retrieve its definition array.
        """
        try:
            result = subprocess.run(
                [f"./{fp.name}", "--list-functions"],
                cwd=self.directory,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return []
        except Exception:
            return []

    # ------------------------------------------------------------------
    # BUILD TOOLS ARRAY FOR MODELS
    # ------------------------------------------------------------------
    def _build_tools_array(self, definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tools = []
        for d in definitions:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": d["name"],
                        "description": d["description"],
                        "parameters": d["parameters"],
                    },
                }
            )
        return tools

    # ------------------------------------------------------------------
    # CREATE CALLABLE WRAPPERS
    # ------------------------------------------------------------------
    def _create_callable_wrappers(self, definitions: List[Dict[str, Any]]):
        self.functions.clear()
        for d in definitions:
            name = d["name"]
            executable = d["_executable"]
            self.functions[name] = self._make_wrapper(name, executable)

    def _make_wrapper(self, func_name: str, executable: str):
        """Produce Python-callable wrapper for external function execution."""
        def wrapper(**kwargs):
            return self.call(func_name, kwargs)
        return wrapper

    # ------------------------------------------------------------------
    # PUBLIC EXECUTION API
    # ------------------------------------------------------------------
    def call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a function.
        """
        
        # Execute as an external function (subprocess)
        executable = None
        for d in self.function_array:
            if d["name"] == function_name:
                executable = d.get("_executable")
                break

        if executable is None:
            raise Exception(f"Unknown function '{function_name}'")

        executable_path = Path(executable)

        try:
            result = subprocess.run(
                [str(executable_path), function_name],
                cwd=PROJECT_DIR,
                input=json.dumps(arguments),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            raise Exception(result.stderr.strip() or "Unknown error")
        except Exception as e:
            raise Exception(f"Error executing function '{function_name}': {e}")


# ----------------------------------------------------------------------
# ASSIGN EAGER SINGLETONS NOW THAT CLASS IS FULLY DEFINED
# ----------------------------------------------------------------------
FunctionSpace.functions = FunctionSpace.get("prompts/functions")

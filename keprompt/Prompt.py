import argparse
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table

from keprompt import CustomEncoder

console = Console()

@dataclass
class Prompt:
    """Data class representing a prompt."""
    name: str
    description: str = ""
    parameters: dict = None
    source: str = ""
    path: str = ""

    def to_dict(self) -> dict:
        """Convert Prompt to dictionary for JSON serialization."""
        return asdict(self)

    def __str__(self) -> str:
        """String representation of Prompt."""
        return f"Prompt({self.name})"


class PromptManager:
    """Handles prompt commands using Prompt dataclass."""
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.prompts:List[Prompt] = []  # List[Prompt]

    def to_dict(self):
        return {'args': str(self.args), 'prompts': self.prompts}

    def load_prompts(self, pattern="*"):
        """Load prompts matching pattern into Prompt objects."""
        from .keprompt import glob_prompt
        prompt_files = glob_prompt(pattern)
        for file_path in prompt_files:
            prompt = self._parse_prompt_file(str(file_path))
            if prompt:
                self.prompts.append(prompt)

    # def _parse_prompt_file(self, prompt_file: str):
    #     """Parse a prompt file into a Prompt dataclass."""
    #     try:
    #         with open(prompt_file, 'r') as f:
    #             lines = f.readlines()
    #         metadata = {}
    #         if lines and lines[0].strip().startswith('.prompt '):
    #             try:
    #                 json_content = "{" + lines[0].strip()[8:] + "}"
    #                 metadata = json.loads(json_content)
    #             except Exception:
    #                 pass
    #         source = ''.join(lines)
    #         return Prompt(
    #             name=metadata.get("name", os.path.basename(prompt_file)),
    #             description=metadata.get("description", ""),
    #             parameters=metadata.get("params", {}),
    #             source=source,
    #             path=prompt_file
    #         )
    #     except Exception as e:
    #         console.print(f"[red]Failed to parse prompt {prompt_file}: {e}[/red]")
    #         return None

    def execute(self) -> Dict[str, Any]:
        """Execute the command based on the provided arguments"""
        # Normalize aliases
        cmd = self.args.prompt_command
        if cmd == "list":
            cmd = "get"
        
        # Support only the \"get\" verb for prompts (list / filter)
        if cmd == "get":
            # Use the optional name filter if supplied, otherwise match all prompts
            pattern = getattr(self.args, "name_filter", None) or "*"
            # Reload prompts based on the pattern
            self.prompts = []  # clear any previous load
            self.load_prompts(pattern)

            # Convert Prompt dataclass instances to plain dictionaries for JSON output
            response = self.make_response()
            return response

        # If other verbs are requested, return a clear error
        return {
            "success": True,
            "data": [f"Unsupported command '{self.args.command}' for PromptManager"],
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def _parse_prompt_file(prompt_file: str) -> Prompt:
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

            return Prompt(
                name=metadata.get("name", os.path.basename(prompt_file)),
                path=prompt_file,
                description=metadata.get("description", ""),
                parameters=metadata.get("params", {}),
                source=source
            )
        except Exception as e:
            return Prompt(
                name=os.path.basename(prompt_file),
                path=prompt_file,
                description=f"Failed to parse file: {str(e)}",
                parameters={},
                source=""
            )



    def pretty_print(self) -> None:

        table = Table(title="Prompt Files")
        table.add_column("Prompt", style="cyan", no_wrap=True)
        table.add_column("Attribute", style="green")
        table.add_column("Value", style="green")

        for p in self.prompts:

            f = p.name
            for k, v in p.to_dict().items():
                if k == "source": continue

                if isinstance(v, str):
                    table.add_row(f, k, f"{v}")
                else:
                    table.add_row(f, k, f"{v}")

                f = ""

            table.add_row("","","")
        return table




    def make_response(self):
        """Return output in pretty table if requested, else plain text/dict."""
        if getattr(self.args, "pretty", False):
            return self.pretty_print()
        # default: text (no JSON mode) — ensure JSON‑serializable structure
        return {"success": True, "prompts": [p.to_dict() for p in self.prompts]}

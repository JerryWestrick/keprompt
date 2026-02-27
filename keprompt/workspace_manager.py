"""Workspace initialization for KePrompt."""
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


class WorkspaceManager:
    """Handles workspace init command."""

    @classmethod
    def register_cli(cls, parent_subparsers: argparse._SubParsersAction, parent_parser: argparse.ArgumentParser) -> None:
        parser = parent_subparsers.add_parser(
            "init",
            aliases=["workspace"],
            parents=[parent_parser],
            help="Initialize workspace (create dirs, copy defaults, init database)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files in prompts/functions/",
        )

    def __init__(self, args: argparse.Namespace = None):
        self.args = args
        self.force = getattr(args, "force", False) if args else False

    def execute(self) -> dict[str, Any]:
        results = []

        # 1. Create directories
        for dir_path in (Path("prompts"), Path("prompts/functions")):
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                results.append({"action": "created_dir", "path": str(dir_path)})
                console.print(f"[green]Created directory:[/] {dir_path}/")
            else:
                results.append({"action": "exists_dir", "path": str(dir_path)})
                console.print(f"[dim]Directory already exists:[/] {dir_path}/")

        # 2. Copy default prompt files
        defaults_dir = Path(__file__).parent / "defaults"
        prompts_dir = Path("prompts")

        for src_file in sorted(defaults_dir.glob("*.prompt")):
            dest_file = prompts_dir / src_file.name
            if dest_file.exists() and not self.force:
                results.append({"action": "skipped", "file": str(dest_file)})
                console.print(f"[yellow]Skipped (exists):[/] {dest_file}")
            else:
                already_existed = dest_file.exists()
                shutil.copy2(src_file, dest_file)
                action = "overwritten" if already_existed else "copied"
                results.append({"action": action, "file": str(dest_file)})
                label = "Overwritten" if already_existed else "Copied"
                console.print(f"[green]{label}:[/] {dest_file}")

        # 3. Copy default function files
        defaults_dir = Path(__file__).parent / "defaults" / "functions"
        target_dir = Path("prompts/functions")

        if defaults_dir.exists():
            for src_file in sorted(defaults_dir.iterdir()):
                if src_file.is_file():
                    dest_file = target_dir / src_file.name
                    if dest_file.exists() and not self.force:
                        results.append({"action": "skipped", "file": str(dest_file)})
                        console.print(f"[yellow]Skipped (exists):[/] {dest_file}")
                    else:
                        already_existed = dest_file.exists()
                        shutil.copy2(src_file, dest_file)
                        action = "overwritten" if already_existed else "copied"
                        results.append({"action": action, "file": str(dest_file)})
                        label = "Overwritten" if already_existed else "Copied"
                        console.print(f"[green]{label}:[/] {dest_file}")
        else:
            results.append({"action": "warning", "message": "Default functions directory not found"})
            console.print("[yellow]Warning: default functions directory not found[/]")

        # 4. Initialize database
        from .db_cli import init_database
        try:
            init_database()
            results.append({"action": "database_initialized"})
        except SystemExit:
            results.append({"action": "database_error"})

        # 5. Update models (keprompt models update)
        try:
            from .model_updater import update_models
            update_models()
            results.append({"action": "models_updated"})
        except Exception as e:
            results.append({"action": "models_update_error", "message": str(e)})
            console.print(f"[yellow]Warning: models update failed: {e}[/]")

        # 6. Reload functions (keprompt functions update)
        try:
            from .keprompt_function_space import FunctionSpace
            fs = FunctionSpace.get("prompts/functions")
            count = len(fs.tools_array)
            results.append({"action": "functions_updated", "count": count})
            console.print(f"[green]Functions loaded:[/] {count} functions")
        except Exception as e:
            results.append({"action": "functions_update_error", "message": str(e)})
            console.print(f"[yellow]Warning: functions update failed: {e}[/]")

        console.print("\n[bold green]Workspace initialized.[/]")

        return {
            "success": True,
            "data": results,
            "timestamp": datetime.now().isoformat(),
        }

import argparse
import logging
import os
import sys

from rich.console import Console

from keprompt.api import handle_json_command
from .CustomEncoder import CustomEncoder
from rich.logging import RichHandler
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich_argparse import RichHelpFormatter

from .ModelManager import ModelManager
from .version import __version__

from .terminal_output import terminal_output

console = Console()
console.size = console.size

logging.getLogger().setLevel(logging.WARNING)

FORMAT = "%(message)s"


logging.basicConfig(level=logging.WARNING,  format=FORMAT,datefmt="[%X]",handlers=[RichHandler(console=console, rich_tracebacks=True)])
log = logging.getLogger(__file__)
__all__ = ["main"]

def normalize_command_aliases(args: argparse.Namespace, parser: argparse.ArgumentParser) -> argparse.Namespace:
    """
    Normalize all command aliases to their canonical forms using parser introspection.
    
    IMPORTANT: We extract ALL aliases but this creates conflicts when different
    managers use the same command name differently.

    For the first release, we're disabling alias normalization to avoid bugs.
    Managers will need to handle aliases themselves in their execute() methods.
    """
    # Alias normalization disabled for first release to avoid cross-manager conflicts
    # Each manager must handle its own aliases in execute()
    return args


def get_cmd_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Parse command‑line arguments for the object‑first CLI.

    Example usages:
        keprompt prompt get                     # list all prompts
        keprompt prompt get --name my_prompt    # filter prompts by name
        keprompt models get --provider OpenRouter
        keprompt chat reply <id> --answer "Hello"
    
    Returns:
        Tuple of (parser, parsed_args) for use in alias normalization
    """
    # Create parent parser with shared flags (can appear after subcommand)
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("-d", "--dump", action="store_true", help="Output cmd args")
    format_group = parent.add_mutually_exclusive_group()
    format_group.add_argument("--json", action="store_true", help="Output as JSON (machine-readable)")
    format_group.add_argument("--pretty", action="store_true", help="Output as pretty tables (human-readable)")
    
    # Main parser (only global options here)
    parser = argparse.ArgumentParser(
        prog="keprompt",
        description="Prompt Engineering Tool – object‑first CLI",
        formatter_class=RichHelpFormatter,
        epilog=(
            "[bold yellow]⚡ Quick Start:[/]\n"
            "  keprompt prompts get\n"
            "  keprompt models get --provider OpenRouter\n"
            "  keprompt chats create --prompt math-tutor\n"
        ),
    )

    parser.add_argument("--version", action="version", version=f"keprompt {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register CLI commands via managers (clean architecture)
    from .Prompt import PromptManager
    from .ModelManager import ModelManager
    from .chat_manager import ChatManager
    from .database import DatabaseManager
    from .api import ProviderManager, FunctionManager
    from .workspace_manager import WorkspaceManager

    PromptManager.register_cli(subparsers, parent)
    ModelManager.register_cli(subparsers, parent)
    ChatManager.register_cli(subparsers, parent)
    DatabaseManager.register_cli(subparsers, parent)
    ProviderManager.register_cli(subparsers, parent)
    FunctionManager.register_cli(subparsers, parent)
    WorkspaceManager.register_cli(subparsers, parent)


    # Allow verb-first syntax: "keprompt new chat ..." → "keprompt chat new ..."
    _swap_verb_object_if_needed()

    args = parser.parse_args()
    return parser, args


# Known objects and verbs for verb-first syntax support
_KNOWN_OBJECTS = {
    'chat', 'chats', 'conversation', 'conversations',
    'model', 'models',
    'prompt', 'prompts',
    'database', 'databases',
    'provider', 'providers',
    'function', 'functions',
    'init', 'workspace',
}

_KNOWN_VERBS = {
    'new', 'create',
    'get', 'list', 'show', 'view',
    'reply', 'answer', 'send', 'update',
    'delete', 'rm',
}


# Normalize verb aliases to canonical forms
_VERB_ALIASES = {
    'list': 'get', 'show': 'get', 'view': 'get',
    'new': 'create',
    'answer': 'reply', 'send': 'reply',
    'rm': 'delete',
}


def _swap_verb_object_if_needed():
    """If user wrote 'keprompt new chat ...', swap to 'keprompt chat new ...'."""
    if len(sys.argv) < 3:
        return
    first, second = sys.argv[1], sys.argv[2]
    if first in _KNOWN_VERBS and first not in _KNOWN_OBJECTS and second in _KNOWN_OBJECTS:
        sys.argv[1], sys.argv[2] = second, first

    # Normalize verb aliases: list→get, new→create, etc.
    if len(sys.argv) >= 3 and sys.argv[2] in _VERB_ALIASES:
        sys.argv[2] = _VERB_ALIASES[sys.argv[2]]

    # Convert single-dash long args to double-dash so argparse abbreviation works:
    #   -provider=OpenRouter → --provider=OpenRouter
    #   -prov=OpenRouter     → --prov=OpenRouter
    #   -p=OpenRouter        → --p=OpenRouter
    # Leave true short flags alone: -d, -h (single char, no =)
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg.startswith('-') and not arg.startswith('--'):
            # Has '=' or more than 1 char after dash → meant as long option
            after_dash = arg[1:]
            if '=' in after_dash or len(after_dash) > 1:
                sys.argv[i] = '-' + arg

from pathlib import Path

def prompt_pattern(prompt_name: str) -> str:

    if '*' in prompt_name:
        prompt_pattern = Path('prompts') / f"{prompt_name}.prompt"
    else:
        prompt_pattern = Path('prompts') / f"{prompt_name}*.prompt"
    return prompt_pattern

def glob_prompt(prompt_name: str) -> list[Path]:
    prompt_p = prompt_pattern(prompt_name)
    return sorted(Path('.').glob(str(prompt_p)))



def main():
    # create prompts directory if it doesn't exist'
    if not os.path.exists('prompts'):
        os.makedirs('prompts')
    

    parser, args = get_cmd_args()
    
    # Normalize all command aliases to canonical forms using parser introspection
    args = normalize_command_aliases(args, parser)

    # Determine an output format from flags
    # Priority: explicit flags > auto-detect from TTY
    stdout_is_tty = sys.stdout.isatty()
    
    if args.json:
        output_format = "json"
        setattr(args, "pretty", False)
    elif args.pretty:
        output_format = "table"
        setattr(args, "pretty", True)
    else:
        # Auto-detect: TTY = pretty tables, pipe = JSON
        output_format = "table" if stdout_is_tty else "json"
        setattr(args, "pretty", stdout_is_tty)

    # Configure terminal output routing as early as possible.
    # This flushes any buffered import-time output into either stdout (pretty)
    # or into the JSON envelope `stdout` field (json).
    terminal_output.configure("capture" if output_format == "json" else "stdout")

    console = Console()
    if args.dump:
        console.print(f"[bold cyan]keprompt[/] [dim]v{__version__}[/] - [bold green]Prompt Engineering Tool[/]")
        console.print(args)
        return

    try:
        response = handle_json_command(args)

        # Use OutputFormatter for both JSON and pretty output
        from .output_formatter import OutputFormatter
        from rich.table import Table
        
        if output_format == "json":
            from datetime import datetime
            
            # Determine success and error
            success = True
            error_obj = None
            data_payload = None

            if isinstance(response, dict):
                success = response.get("success", True)
                error_obj = response.get("error") if not success else None
                data_payload = response.get("data", response)
            elif isinstance(response, (list, tuple)):
                data_payload = response
            else:
                # Non-serializable types (e.g., Table). Provide string representation.
                data_payload = str(response)

            # Promote chat-specific top-level fields when present
            ai_response = response.get("ai_response") if isinstance(response, dict) else None
            chat_id = response.get("chat_id") if isinstance(response, dict) else None

            envelope = {
                "success": success,
                "data": data_payload if success else None,
                "error": error_obj if not success else None,
                "stdout": terminal_output.get_stdout() or None,
                "meta": {
                    "schema_version": 1,
                    "command": f"{args.command}",
                    "args": vars(args),
                    # If command returns variables (e.g., chat create/new), expose
                    # them in meta for machine consumers.
                    "variables": (data_payload.get("variables") if isinstance(data_payload, dict) else None),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "version": __version__,
                },
            }

            # Include ai_response and chat_id at top level when present
            # (chat new / chat reply responses)
            if ai_response is not None:
                envelope["ai_response"] = ai_response
            if chat_id is not None:
                envelope["chat_id"] = chat_id

            # Use OutputFormatter for JSON serialization (handles Peewee, datetime, etc.)
            json_output = OutputFormatter.format(envelope, format_type="json")
            sys.stdout.write(json_output + "\n")
            sys.stdout.flush()

            if not success:
                # Also mirror a concise error to stderr and exit non-zero
                err_console = Console(file=sys.stderr)
                err_msg = error_obj if isinstance(error_obj, str) else envelope['error']
                err_console.print(f"[red]Error:[/] {err_msg}")
                if chat_id:
                    err_console.print(f"[dim]Chat saved as[/] [cyan]{chat_id}[/] [dim]— inspect with:[/] keprompt chat get {chat_id}")
                sys.exit(1)
            return

        # Pretty/table output path - use OutputFormatter
        # If response is already a Rich Table (legacy), print it directly
        if isinstance(response, Table):
            console.print(response)
        elif isinstance(response, dict) and response.get("success") is False:
            err_console = Console(file=sys.stderr)
            err_console.print(f"[red]Error:[/] {response.get('error', 'Unknown error')}")
            if response.get("chat_id"):
                err_console.print(f"[dim]Chat saved as[/] [cyan]{response['chat_id']}[/] [dim]— inspect with:[/] keprompt chat get {response['chat_id']}")
            sys.exit(1)
        else:
            # Convert JSON response to Rich table using OutputFormatter
            # OutputFormatter will extract object_type from the response dict
            formatted_output = OutputFormatter.format(response, format_type="pretty")
            console.print(formatted_output)
    except Exception as e:
        # Standardize error handling
        err_envelope = {
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL", "message": str(e)},
            "stdout": terminal_output.get_stdout() or None,
            "meta": {"schema_version": 1, "command": f"{getattr(args, 'command', '?')}", "version": __version__},
        }
        if 'output_format' in locals() and output_format == 'json':
            import json as _json
            sys.stdout.write(_json.dumps(err_envelope, indent=2, cls=CustomEncoder) + "\n")
        else:
            err_console = Console(file=sys.stderr)
            err_console.print(err_envelope)
        sys.exit(1)


if __name__ == "__main__":
    main()

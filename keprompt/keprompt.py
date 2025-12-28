import argparse
import getpass
import logging
import os
import sys

from rich.console import Console

from keprompt.api import handle_json_command
from .config import get_config
from .CustomEncoder import CustomEncoder
from rich.logging import RichHandler
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich_argparse import RichHelpFormatter

from .ModelManager import ModelManager
from .keprompt_utils import print_simple_table, format_model_count_data
from .version import __version__

console = Console()
console.size = console.size

logging.getLogger().setLevel(logging.WARNING)

FORMAT = "%(message)s"


logging.basicConfig(level=logging.WARNING,  format=FORMAT,datefmt="[%X]",handlers=[RichHandler(console=console, rich_tracebacks=True)])
log = logging.getLogger(__file__)
__all__ = ["main"]

def matches_pattern(text: str, pattern: str) -> bool:
    """Case-insensitive pattern matching"""
    if not pattern:
        return True
    return pattern.lower() in text.lower()

def print_companies():
    """Print all available companies (model creators)"""
    columns = [
        {'name': 'Company', 'style': 'cyan', 'no_wrap': True},
        {'name': 'Model Count', 'style': 'green', 'justify': 'right'}
    ]

    rows = format_model_count_data(ModelManager.models, 'company')
    print_simple_table("Available Companies (Model Creators)", columns, rows)

def print_providers():
    """Print all available providers (API services)"""
    columns = [
        {'name': 'Provider', 'style': 'cyan', 'no_wrap': True},
        {'name': 'Model Count', 'style': 'green', 'justify': 'right'}
    ]
    
    rows = format_model_count_data(ModelManager.models, 'provider')
    print_simple_table("Available Providers (API Services)", columns, rows)

def print_models(model_pattern: str = "", company_pattern: str = "", provider_pattern: str = ""):
    # Filter models based on patterns
    filtered_models = {
        name: model for name, model in ModelManager.models.items()
        if matches_pattern(name, model_pattern) and
           matches_pattern(model.company, company_pattern) and  
           matches_pattern(model.provider, provider_pattern)
    }
    
    if not filtered_models:
        console.print("[bold red]No models match the specified filters.[/bold red]")
        return
    
    # Build title with active filters
    title_parts = ["Available Models"]
    if model_pattern:
        title_parts.append(f"Model: *{model_pattern}*")
    if company_pattern:
        title_parts.append(f"Company: *{company_pattern}*")
    if provider_pattern:
        title_parts.append(f"Provider: *{provider_pattern}*")
    
    title = " | ".join(title_parts)
    
    table = Table(title=title)
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Company", style="cyan", no_wrap=True)
    table.add_column("Model", style="green")
    table.add_column("Max Token", style="magenta", justify="right")
    table.add_column("$/mT In", style="green", justify="right")
    table.add_column("$/mT Out", style="green", justify="right")
    table.add_column("Input", style="blue", no_wrap=True)
    table.add_column("Output", style="blue", no_wrap=True)
    table.add_column("Functions", style="yellow", no_wrap=True)
    table.add_column("Cutoff", style="dim", no_wrap=True)
    table.add_column("Description", style="white")

    # Sort by Provider, then Company, then model name
    sortable_keys = [f"{filtered_models[model_name].provider}:{filtered_models[model_name].company}:{model_name}" for model_name in filtered_models.keys()]
    sortable_keys.sort()

    last_provider = ''
    last_company = ''
    for k in sortable_keys:
        provider, company, model_name = k.split(':', maxsplit=2)
        model = filtered_models[model_name]
        
        # Show provider and company only when they change
        display_provider = provider if provider != last_provider else ""
        display_company = company if company != last_company or provider != last_provider else ""
        
        table.add_row(
            display_provider,
            display_company,
            model_name,
            str(model.max_tokens),
            f"{model.input_cost*1_000_000:06.4f}",
            f"{model.output_cost*1_000_000:06.4f}",
            "Text+Vision" if model.supports.get("vision", False) else "Text",
            "Text",
            "Yes" if model.supports.get("function_calling", False) else "No",
            "2024-04",
            model.description
        )
        
        last_provider = provider
        last_company = company

    console.print(table)

def print_prompt_names(prompt_files: list[str]) -> None:

    table = Table(title="Prompt Files")
    table.add_column("Prompt", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")

    for prompt_file in prompt_files:
        try:
            with open(prompt_file, 'r') as file:
                first_line = file.readline().strip()  # Read entire first line without stripping
        except Exception as e:
            first_line = f"Error reading file: {str(e)}"

        table.add_row(os.path.basename(prompt_file), first_line)

    console.print(table)

def create_dropdown(options: list[str], prompt_text: str = "Select an option") -> str:
    # Display numbered options
    for i, option in enumerate(options, 1):
        console.print(f"{i}. {option}", style="cyan")

    # Get user input with validation
    while True:
        choice = RichPrompt.ask(
            prompt_text,
            choices=[str(i) for i in range(1, len(options) + 1)],
            show_choices=False
        )

        return options[int(choice) - 1]

def get_new_api_key() -> None:

    companies = sorted(ModelManager.handlers.keys())
    company = create_dropdown(companies, "AI Company?")
    # api_key = console.input(f"[bold green]Please enter your [/][bold cyan]{company} API key: [/]")
    api_key = getpass.getpass(f"Please enter your {company} API key: ")
    config = get_config()
    config.set_api_key(company, api_key)

def normalize_command_aliases(args: argparse.Namespace) -> argparse.Namespace:
    """
    Normalize all command aliases to their canonical forms.
    This provides uniform aliasing throughout the system.
    
    Alias mappings:
    - chat_command: get (list, show, view), create (start, new), update (reply, answer, send), delete (rm)
    - prompt_command: get (list)
    - models_command: get (list, show)
    - functions_command: get (list, show)
    - database_command: get (list, show)
    """


    console.print(args)

    # Chat command aliases
    if hasattr(args, 'chat_command') and args.chat_command:
        alias_map = {
            'list': 'get',
            'show': 'get',
            'view': 'get',
            'start': 'create',
            'new': 'create',
            'reply': 'update',
            'answer': 'update',
            'send': 'update',
            'rm': 'delete',
        }
        if args.chat_command in alias_map:
            args.chat_command = alias_map[args.chat_command]
    
    # Prompt command aliases
    if hasattr(args, 'prompt_command') and args.prompt_command:
        if args.prompt_command in ('list', 'show'):
            args.prompt_command = 'get'
    
    # Models command aliases
    if hasattr(args, 'models_command') and args.models_command:
        if args.models_command in ('list', 'show'):
            args.models_command = 'get'
    
    # Functions command aliases
    if hasattr(args, 'functions_command') and args.functions_command:
        if args.functions_command in ('list', 'show'):
            args.functions_command = 'get'
    
    # Database command aliases
    if hasattr(args, 'database_command') and args.database_command:
        if args.database_command in ('list', 'show'):
            args.database_command = 'get'
    
    return args


def get_cmd_args() -> argparse.Namespace:
    """
    Parse command‑line arguments for the object‑first CLI.

    Example usages:
        keprompt prompt get                     # list all prompts
        keprompt prompt get --name my_prompt    # filter prompts by name
        keprompt models get --provider OpenRouter
        keprompt chat reply <id> --answer "Hello"
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
    from .api import ProviderManager, FunctionManager, ServerManager

    PromptManager.register_cli(subparsers, parent)
    ModelManager.register_cli(subparsers, parent)
    ChatManager.register_cli(subparsers, parent)
    DatabaseManager.register_cli(subparsers, parent)
    ProviderManager.register_cli(subparsers, parent)
    FunctionManager.register_cli(subparsers, parent)
    ServerManager.register_cli(subparsers, parent)


    args = parser.parse_args()
    return args

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



def create_global_variables():
    """Create global variables dictionary with explicit hard-coded defaults"""
    return {
        # Variable substitution delimiters
        'Prefix': '<<',
        'Postfix': '>>',
        
        # Future expansion possibilities
        'Debug': False,
        'Verbose': False,
        # Add other system defaults here
    }

def main():
    # create prompts directory if it doesn't exist'
    if not os.path.exists('prompts'):
        os.makedirs('prompts')
    

    args = get_cmd_args()
    
    # Normalize all command aliases to canonical forms
    args = normalize_command_aliases(args)

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

    console = Console()
    if args.dump:
        console.print(f"[bold cyan]keprompt[/] [dim]v{__version__}[/] - [bold green]Prompt Engineering Tool[/]")
        console.print(args)
        return

    try:
        response = handle_json_command(args)

        # Build standardized envelope for machine output
        if output_format == "json":
            from datetime import datetime
            import json as _json

            # Determine success and error
            success = True
            error_obj = None
            data_payload = None

            if isinstance(response, dict):
                success = response.get("success", True)
                error_obj = response.get("error") if not success else None
                data_payload = response.get("data", response)
            elif isinstance(response, (list, tuple)):
                # Lists/tuples can be serialized directly with CustomEncoder
                data_payload = response
            else:
                # Non-serializable types (e.g., Table). Provide string representation.
                data_payload = str(response)

            envelope = {
                "success": success,
                "data": data_payload if success else None,
                "error": error_obj if not success else None,
                "meta": {
                    "schema_version": 1,
                    "command": f"{args.command}",
                    "args": vars(args),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "version": __version__,
                },
            }
            sys.stdout.write(_json.dumps(envelope, indent=2, cls=CustomEncoder) + "\n")
            sys.stdout.flush()
            if not success:
                # Also mirror a concise error to stderr and exit non-zero
                err_console = Console(file=sys.stderr)
                err_console.print(f"[red]Error:[/] {error_obj if isinstance(error_obj, str) else envelope['error']}")
                sys.exit(1)
            return

        # Human/table output path
        if isinstance(response, dict):
            # Keep legacy behavior but avoid non-serializable Namespace in output
            response.setdefault('success', True)
            response['command'] = vars(args)
            console.print(response)
        else:
            console.print(response)
    except Exception as e:
        # Standardize error handling
        err_envelope = {
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL", "message": str(e)},
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

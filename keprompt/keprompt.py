import argparse
import getpass
import logging
import os
import re
import sys

import keyring
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.table import Table

from .AiRegistry import AiRegistry
from .keprompt_functions import DefinedToolsArray
from .keprompt_vm import VM, print_prompt_code, print_statement_types
from .version import __version__

console = Console()
console.size = console.size

logging.getLogger().setLevel(logging.WARNING)

FORMAT = "%(message)s"
# logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(console=console)])

logging.basicConfig(level=logging.WARNING,  format=FORMAT,datefmt="[%X]",handlers=[RichHandler(console=console, rich_tracebacks=True)])
log = logging.getLogger(__file__)


def print_functions():
    table = Table(title="Available Functions")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description/Parameters", style="green")
    # Sort by LLM name, then model.
    sortable_keys = [f"{AiRegistry.models[model_name].company}:{model_name}" for model_name in AiRegistry.models.keys()]
    sortable_keys.sort()

    for tool in DefinedToolsArray:
        function = tool['function']
        name = function['name']
        description = function['description']

        table.add_row(name, description,)
        for k,v in function['parameters']['properties'].items():
            table.add_row("", f"[bold blue]{k:10}[/]: {v['description']}")

        table.add_row("","")

    console.print(table)

def print_models():
    table = Table(title="Available Models")
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

    # Sort by LLM name, then model.
    sortable_keys = [f"{AiRegistry.models[model_name].company}:{model_name}" for model_name in AiRegistry.models.keys()]
    sortable_keys.sort()

    last_company = ''
    for k in sortable_keys:
        company, model_name = k.split(':', maxsplit=1)
        model = AiRegistry.get_model(model_name)
        if company != last_company:
            table.add_row(
                company,
                model_name,
                str(model.context),
                f"{model.input*1_000_000:06.4f}",
                f"{model.output*1_000_000:06.4f}",
                model.modality_in,
                model.modality_out,
                model.functions,
                model.cutoff,
                model.description
            )
            last_company = company
        else:
            table.add_row(
                "",
                model_name,
                str(model.context),
                f"{model.input*1_000_000:06.4f}",
                f"{model.output*1_000_000:06.4f}",
                model.modality_in,
                model.modality_out,
                model.functions,
                model.cutoff,
                model.description
            )

    console.print(table)

def print_prompt_names(prompt_files: list[str]) -> None:

    table = Table(title="Prompt Files")
    table.add_column("Prompt", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")

    for prompt_file in prompt_files:
        try:
            with open(prompt_file, 'r') as file:
                first_line = file.readline().strip()[2:]  # Read first line
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
        choice = Prompt.ask(
            prompt_text,
            choices=[str(i) for i in range(1, len(options) + 1)],
            show_choices=False
        )

        return options[int(choice) - 1]

def get_new_api_key() -> None:

    companies = sorted(AiRegistry.handlers.keys())
    company = create_dropdown(companies, "AI Company?")
    # api_key = console.input(f"[bold green]Please enter your [/][bold cyan]{company} API key: [/]")
    api_key = getpass.getpass(f"Please enter your {company} API key: ")
    keyring.set_password("keprompt", username=company, password=api_key)

def print_prompt_lines(prompts_files: list[str]) -> None:
    table = Table(title="Prompt Code")
    table.add_column("Prompt", style="cyan bold", no_wrap=True)
    table.add_column("Lno", style="blue bold", no_wrap=True)
    table.add_column("Prompt Line", style="dark_green bold")

    for prompt_file in prompts_files:
        # console.print(f"{prompt_file}")
        try:
            title = os.path.basename(prompt_file)
            with open(prompt_file, 'r') as file:
                lines = file.readlines()
                for lno, line in enumerate(lines):
                    table.add_row(title, f"{lno:03}", line.strip())
                    title = ''

        except Exception as e:
            console.print(f"[bold red]Error parsing file {prompt_file} : {str(e)}[/bold red]")
            console.print_exception()
            sys.exit(1)
        table.add_row('───────────────', '───', '──────────────────────────────────────────────────────────────────────')
    console.print(table)

def get_cmd_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt Engineering Tool.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit')
    parser.add_argument('--param', nargs=2, action='append',metavar=('key', 'value'),help='Add key/value pairs')
    parser.add_argument('-m', '--models', action='store_true', help='List company models information and exit')
    parser.add_argument('-s', '--statements', action='store_true', help='List supported prompt statement types and exit')
    parser.add_argument('-f', '--functions', action='store_true', help='List functions available to AI and exit')
    parser.add_argument('-p', '--prompts', nargs='?', const='*', help='List Prompts')
    parser.add_argument('-c', '--code', nargs='?', const='*', help='List code in Prompts')
    parser.add_argument('-l', '--list', nargs='?', const='*', help='List Prompt file')
    parser.add_argument('-e', '--execute', nargs='?', const='*', help='Execute one or more Prompts')
    parser.add_argument('-k', '--key', action='store_true', help='Ask for (new) Company Key')
    parser.add_argument('--log', metavar='IDENTIFIER', nargs='?', const='', help='Enable structured logging to prompts/logs-<identifier>/ directory (if no identifier provided, uses prompt name)')
    parser.add_argument('--debug', action='store_true', help='Enable structured logging + rich output to STDERR')
    parser.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')
    parser.add_argument('--init', action='store_true', help='Initialize prompts and functions directories')
    parser.add_argument('--check-builtins', action='store_true', help='Check for built-in function updates')
    parser.add_argument('--update-builtins', action='store_true', help='Update built-in functions')

    return parser.parse_args()

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
    # Ensure 'prompts' directory exists
    if not os.path.exists('prompts'):
        os.makedirs('prompts')

    if not os.path.exists('logs'):
        os.makedirs('logs')

    args = get_cmd_args()
    debug = args.debug
    

    if args.version:
        # Print the version and exit
        console.print(f"[bold cyan]keprompt[/] [bold green]version[/] [bold magenta]{__version__}[/]")
        return

    # Start with hard-coded defaults
    global_variables = create_global_variables()
    
    # Override with command line parameters
    if args.param:
        for key, value in args.param:
            global_variables[key] = value

    # Add in main() after args parsing:
    if args.remove:
        pattern = r'.*\.~\d{2}~\.[^.]+$'
        for root, _, files in os.walk('.'):
            for file in files:
                if re.match(pattern, file):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        if debug:
                            log.info(f"Removed {file_path}")
                    except OSError as e:
                        log.error(f"Error removing {file_path}: {e}")
        return

    if args.models:
        # Print the models table and exit
        print_models()
        return

    if args.statements:
        print_statement_types()
        return

    if args.statements:
        # Print supported prompt language statement types and exit
        console.print("[bold cyan]Supported Prompt Statement Types:[/]")
        console.print("[green]- Input[/]")
        console.print("[green]- Output[/]")
        console.print("[green]- Decision[/]")
        console.print("[green]- Loop[/]")

    if args.functions:
        # Print list of functions and exit
        print_functions()
        return

    if args.init:
        # Initialize directories and built-in functions
        from .function_loader import FunctionLoader
        loader = FunctionLoader()
        loader.ensure_functions_directory()
        console.print("[bold green]Initialization complete![/bold green]")
        return

    if args.check_builtins:
        # Check for built-in function updates
        from .function_loader import FunctionLoader
        import subprocess
        
        loader = FunctionLoader()
        builtin_path = loader.functions_dir / loader.builtin_name
        
        if not builtin_path.exists():
            console.print("[bold red]Built-in functions not found. Run 'keprompt --init' first.[/bold red]")
            return
            
        try:
            result = subprocess.run([str(builtin_path), "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                console.print(f"[bold cyan]Current built-ins version:[/bold cyan] {result.stdout.strip()}")
                console.print("[bold green]Built-ins are up to date.[/bold green]")
            else:
                console.print("[bold yellow]Could not determine built-ins version.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]Error checking built-ins version: {e}[/bold red]")
        return

    if args.update_builtins:
        # Update built-in functions
        from .function_loader import FunctionLoader
        import shutil
        
        loader = FunctionLoader()
        builtin_path = loader.functions_dir / loader.builtin_name
        
        if not loader.functions_dir.exists():
            console.print("[bold red]Functions directory not found. Run 'keprompt --init' first.[/bold red]")
            return
            
        # Create backup
        if builtin_path.exists():
            backup_path = builtin_path.with_suffix('.backup')
            shutil.copy2(builtin_path, backup_path)
            console.print(f"[bold yellow]Backed up current built-ins to {backup_path}[/bold yellow]")
            
        # Install new built-ins
        loader._install_builtin_functions()
        console.print("[bold green]Built-in functions updated successfully![/bold green]")
        return

    if args.key:
        get_new_api_key()

    if args.prompts:
        glob_files = glob_prompt(args.prompts)
        if debug: log.info(f"--prompts '{args.prompts}' returned {len(glob_files)} files: {glob_files}")

        if glob_files:
            print_prompt_names(glob_files)
        else:
            pname = prompt_pattern(args.prompts)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return

    if args.list:
        glob_files = glob_prompt(args.list)
        if debug: log.info(f"--list '{args.list}' returned {len(glob_files)} files: {glob_files}")

        if glob_files:
            print_prompt_lines(glob_files)
        else:
            pname = prompt_pattern(args.list)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return

    if args.code:
        glob_files = glob_prompt(args.code)
        if debug: log.info(f"--code '{args.code}' returned {len(glob_files)} files: {glob_files}")

        if glob_files:
            print_prompt_code(glob_files)
        else:
            pname = prompt_pattern(args.code)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return

    if args.execute:
        glob_files = glob_prompt(args.execute)

        if glob_files:
            for prompt_file in glob_files:
                # Determine logging mode and identifier
                from .keprompt_logger import LogMode
                
                log_identifier = None
                if args.debug:
                    log_mode = LogMode.DEBUG
                    # Use prompt name as default identifier for debug mode
                    log_identifier = os.path.splitext(os.path.basename(prompt_file))[0]
                elif args.log is not None:  # --log was specified (with or without identifier)
                    log_mode = LogMode.LOG
                    if args.log:  # --log <identifier> was provided
                        log_identifier = args.log
                    else:  # --log without identifier, use prompt name
                        log_identifier = os.path.splitext(os.path.basename(prompt_file))[0]
                else:
                    log_mode = LogMode.PRODUCTION
                
                step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier)
                step.parse_prompt()
                step.execute()
        else:
            pname = prompt_pattern(args.execute)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return




if __name__ == "__main__":
    main()

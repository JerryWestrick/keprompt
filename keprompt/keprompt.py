import argparse
import glob
import os
import re
import sys
import keyring
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
import logging
from rich.logging import RichHandler
from keprompt.version import __version__

from keprompt.keprompt_kestep import  KeStep, print_step_code, models_config
from keprompt.keprompt_api_config import api_config
from keprompt.keprompt_functions import DefinedToolsArray



console = Console()


logging.getLogger().setLevel(logging.WARNING)

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

log = logging.getLogger(__file__)

def print_functions():
    table = Table(title="Available Functions")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description/Parameters", style="green")
    # Sort by LLM name, then model.
    sortable_keys = [f"{models_config[model]['company']}:{model}" for model in models_config.keys()]
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

    # Sort by LLM name, then model.
    sortable_keys = [f"{models_config[model]['company']}:{model}" for model in models_config.keys()]
    sortable_keys.sort()

    last_company = ''
    for k in sortable_keys:
        company, model_name = k.split(':', maxsplit=1)
        model = models_config.get(model_name)
        if company != last_company:
            table.add_row(company,
                          model_name,
                          str(model['context']),
                          f"{model['input']*1_000_000:06.4f}",
                          f"{model['output']*1_000_000:06.4f}"
                          )
            last_company = company
        else:
            table.add_row("", model_name, str(model['context']), f"{model['input']*1_000_000:06.4f}",
                      f"{model['output']*1_000_000:06.4f}")

    console.print(table)

def print_step_names(step_files: list[str]) -> None:
    table = Table(title="Step Files")

    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")

    for step_file in step_files:
        try:
            with open(step_file, 'r') as file:
                first_line = file.readline().strip()[2:]  # Read first line
        except Exception as e:
            first_line = f"Error reading file: {str(e)}"

        table.add_row(os.path.basename(step_file), first_line)

    console.print(table)

def create_dropdown(options, prompt_text="Select an option"):
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
    companies = list(api_config.keys())
    companies.sort()
    company = create_dropdown(companies, "AI Company?")
    api_key = console.input(f"[bold green]Please enter your [/][bold cyan]{company} API key: [/]")
    keyring.set_password("kestep", username=company, password=api_key)

def print_step_lines(step_files: list[str]) -> None:
    table = Table(title="Prompt Code")
    table.add_column("Step", style="cyan bold", no_wrap=True)
    table.add_column("Lno", style="blue bold", no_wrap=True)
    table.add_column("Prompt Line", style="dark_green bold")

    for step_file in step_files:
        # console.print(f"{step_file}")
        try:
            title = os.path.basename(step_file)
            with open(step_file, 'r') as file:
                lines = file.readlines()
                for lno, line in enumerate(lines):
                    table.add_row(title, f"{lno:03}", line.strip())
                    title = ''

        except Exception as e:
            console.print(f"[bold red]Error parsing file {step_file} : {str(e)}[/bold red]")
            console.print_exception()
            sys.exit(1)
        table.add_row('───────────────', '───', '──────────────────────────────────────────────────────────────────────')
    console.print(table)

def get_cmd_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kestep command line tool.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit')
    parser.add_argument('-m', '--models', action='store_true', help='List company models information and exit')
    parser.add_argument('-f', '--functions', action='store_true', help='List functions available to AI and exit')
    parser.add_argument('-s', '--steps', nargs='?', const='*', help='List Steps')
    parser.add_argument('-c', '--code', nargs='?', const='*', help='List code in Steps')
    parser.add_argument('-l', '--list', nargs='?', const='*', help='List Step file')
    parser.add_argument('-e', '--execute', nargs='?', const='*', help='Execute one or more Steps')
    parser.add_argument('-k', '--key', action='store_true', help='Ask for (new) Company Key')
    parser.add_argument('-d', '--debug', action='store_true', help='Print message to LLM, for debugging purposes.')
    parser.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')

    return parser.parse_args()

def glob_step(step_name) -> list[str] :
    step_pattern = os.path.join('steps/', f"{step_name}*.prompt")
    return sorted(glob.glob(step_pattern))  # Sort the files


def main():
    # Ensure 'steps' directory exists
    if not os.path.exists('steps'):
        os.makedirs('steps')

    if not os.path.exists('logs'):
        os.makedirs('logs')

    args = get_cmd_args()
    debug = args.debug

    if args.version:
        # Print the version and exit
        console.print(f"[bold cyan]keprompt[/] [bold green]version[/] [bold magenta]{__version__}[/]")
        return

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

    if args.functions:
        # Print list of functions and exit
        print_functions()
        return

    if args.key:
        get_new_api_key()

    if args.steps:
        step_files = glob_step(args.steps)
        if debug: log.info(f"--list '{args.steps}' returned {len(step_files)} files: {step_files}")

        if step_files:
            print_step_names(step_files)
        else:
            log.error(f"[bold red]No list files found for ({args.list})[/bold red]", extra={"markup": True})
        return

    if args.list:
        step_files = glob_step(args.list)
        if debug: log.info(f"--code '{args.list}' returned {len(step_files)} files: {step_files}")

        if step_files:
            print_step_lines(step_files)
        else:
            
            log.error(f"[bold red]No step files found ({args.list})[/bold red]", extra={"markup": True})
        return

    if args.code:
        step_files = glob_step(args.code)
        if debug: log.info(f"--code '{args.code}' returned {len(step_files)} files: {step_files}")

        if step_files:
            print_step_code(step_files)
        else:
            log.error(f"[bold red]No step files found ({args.step})[/bold red]", extra={"markup": True})
        return

    if args.execute:
        step_files = glob_step(args.execute)
        if debug: log.info(f"--execute '{args.list}' returned {len(step_files)} files: {step_files}")

        if step_files:
            for step_file in step_files:
                step = KeStep(step_file, args.debug)
                step.parse_prompt()
                step.execute()
        else:
            log.error(f"[bold red]No execute files found for ({args.execute})[/bold red]", extra={"markup": True})
        return


if __name__ == "__main__":
    main()

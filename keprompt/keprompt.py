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

def matches_pattern(text: str, pattern: str) -> bool:
    """Case-insensitive pattern matching"""
    if not pattern:
        return True
    return pattern.lower() in text.lower()

def print_companies():
    """Print all available companies (model creators)"""
    companies = sorted(set(model.company for model in AiRegistry.models.values()))
    
    table = Table(title="Available Companies (Model Creators)")
    table.add_column("Company", style="cyan", no_wrap=True)
    table.add_column("Model Count", style="green", justify="right")
    
    for company in companies:
        model_count = sum(1 for model in AiRegistry.models.values() if model.company == company)
        table.add_row(company, str(model_count))
    
    console.print(table)

def print_providers():
    """Print all available providers (API services)"""
    providers = sorted(set(model.provider for model in AiRegistry.models.values()))
    
    table = Table(title="Available Providers (API Services)")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Model Count", style="green", justify="right")
    
    for provider in providers:
        model_count = sum(1 for model in AiRegistry.models.values() if model.provider == provider)
        table.add_row(provider, str(model_count))
    
    console.print(table)

def print_models(model_pattern: str = "", company_pattern: str = "", provider_pattern: str = ""):
    # Filter models based on patterns
    filtered_models = {
        name: model for name, model in AiRegistry.models.items()
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
            str(model.context),
            f"{model.input*1_000_000:06.4f}",
            f"{model.output*1_000_000:06.4f}",
            model.modality_in,
            model.modality_out,
            model.functions,
            model.cutoff,
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
    parser.add_argument('-m', '--models', nargs='?', const='', help='List models (optionally filter by model name pattern)')
    parser.add_argument('--company', help='Filter models by company name pattern')
    parser.add_argument('--provider', help='Filter models by provider name pattern')
    parser.add_argument('-s', '--statements', action='store_true', help='List supported prompt statement types and exit')
    parser.add_argument('-f', '--functions', action='store_true', help='List functions available to AI and exit')
    parser.add_argument('-p', '--prompts', nargs='?', const='*', help='List Prompts')
    parser.add_argument('-c', '--code', nargs='?', const='*', help='List code in Prompts')
    parser.add_argument('-l', '--list', nargs='?', const='*', help='List Prompt files, or specify: company/companies, provider/providers')
    parser.add_argument('-e', '--execute', nargs='?', const='*', help='Execute one or more Prompts')
    parser.add_argument('-k', '--key', action='store_true', help='Ask for (new) Company Key')
    parser.add_argument('--log', metavar='IDENTIFIER', nargs='?', const='', help='Enable structured logging to prompts/logs-<identifier>/ directory (if no identifier provided, uses prompt name)')
    parser.add_argument('--debug', action='store_true', help='Enable structured logging + rich output to STDERR')
    parser.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')
    parser.add_argument('--init', action='store_true', help='Initialize prompts and functions directories')
    parser.add_argument('--check-builtins', action='store_true', help='Check for built-in function updates')
    parser.add_argument('--update-builtins', action='store_true', help='Update built-in functions')
    parser.add_argument('--update-models', metavar='PROVIDER', help='Update model definitions for specified provider (e.g., OpenRouter) or "All" for all providers')
    parser.add_argument('--conversation', metavar='NAME', help='Load/save conversation state')
    parser.add_argument('--answer', metavar='TEXT', help='Continue conversation with user response')

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

    if args.models is not None or args.company or args.provider:
        # Print the models table and exit
        print_models(
            model_pattern=args.models or "",
            company_pattern=args.company or "",
            provider_pattern=args.provider or ""
        )
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

    if args.update_models:
        # Update model definitions for specified provider or all providers
        provider_input = args.update_models
        
        if provider_input.lower() == 'all':
            # Update all providers
            providers = sorted(AiRegistry.handlers.keys())
            console.print(f"[bold cyan]Updating models for all {len(providers)} providers...[/bold cyan]")
            
            success_count = 0
            for provider_name in providers:
                try:
                    handler_class = AiRegistry.get_handler(provider_name)
                    console.print(f"[bold cyan]Updating models for {provider_name}...[/bold cyan]")
                    handler_class.create_models_json(provider_name)
                    console.print(f"[bold green]Successfully updated models for {provider_name}![/bold green]")
                    success_count += 1
                except Exception as e:
                    console.print(f"[bold red]Error updating models for {provider_name}: {e}[/bold red]")
            
            console.print(f"[bold cyan]Update complete: {success_count}/{len(providers)} providers updated successfully[/bold cyan]")
        else:
            # Update single provider
            provider_name = provider_input
            try:
                # Get the handler class for the provider
                handler_class = AiRegistry.get_handler(provider_name)
                
                # Call the create_models_json method
                console.print(f"[bold cyan]Updating models for {provider_name}...[/bold cyan]")
                handler_class.create_models_json(provider_name)
                console.print(f"[bold green]Successfully updated models for {provider_name}![/bold green]")
                
            except ValueError as e:
                console.print(f"[bold red]Error: {e}[/bold red]")
                console.print(f"[yellow]Available providers: {', '.join(sorted(AiRegistry.handlers.keys()))}[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Error updating models for {provider_name}: {e}[/bold red]")
        return

    if args.key:
        get_new_api_key()

    # Handle conversation mode
    if args.conversation:
        # Ensure 'conversations' directory exists
        if not os.path.exists('conversations'):
            os.makedirs('conversations')
        
        conversation_name = args.conversation
        
        # Determine logging mode and identifier
        from .keprompt_logger import LogMode
        
        log_identifier = None
        if args.debug:
            log_mode = LogMode.DEBUG
            log_identifier = conversation_name
        elif args.log is not None:  # --log was specified (with or without identifier)
            log_mode = LogMode.LOG
            if args.log:  # --log <identifier> was provided
                log_identifier = args.log
            else:  # --log without identifier, use conversation name
                log_identifier = conversation_name
        else:
            log_mode = LogMode.PRODUCTION
        
        if args.answer:
            # Continue existing conversation with user answer
            from .keprompt_vm import make_statement
            from .AiPrompt import AiTextPart
            
            step = VM(None, global_variables, log_mode=log_mode, log_identifier=log_identifier)  # No prompt file
            loaded = step.load_conversation(conversation_name)
            
            if not loaded:
                console.print(f"[bold red]Error: Conversation '{conversation_name}' not found[/bold red]")
                sys.exit(1)
            
            # Log the user answer in execution log
            step.logger.log_user_answer(args.answer)
            
            # Add user answer to conversation messages
            step.prompt.add_message(vm=step, role='user', content=[AiTextPart(vm=step, text=args.answer)])
            
            # Create statements for continuation
            step.statements = []
            step.statements.append(make_statement(step, 0, '.exec', ''))
            step.statements.append(make_statement(step, 1, '.print', '<<last_response>>'))
            step.statements.append(make_statement(step, 2, '.exit', ''))
            
            # Execute the continuation
            step.execute()
            
            # Save updated conversation
            step.save_conversation(conversation_name)
            
        elif args.execute:
            # Start new conversation with prompt file
            glob_files = glob_prompt(args.execute)
            
            if glob_files:
                for prompt_file in glob_files:
                    step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier)
                    step.parse_prompt()
                    step.execute()
                    
                    # Save conversation after execution
                    step.save_conversation(conversation_name)
            else:
                pname = prompt_pattern(args.execute)
                log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        else:
            # No --answer or --execute specified with --conversation
            console.print("[bold red]Error: --conversation requires either --answer or --execute[/bold red]")
            sys.exit(1)
        
        return

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
        # Check if user wants to list companies or providers
        if args.list.lower() in ['company', 'companies']:
            print_companies()
            return
        elif args.list.lower() in ['provider', 'providers']:
            print_providers()
            return
        else:
            # Existing prompt file listing logic
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

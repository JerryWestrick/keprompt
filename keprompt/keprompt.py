import argparse
import getpass
import logging
import os
import re
import sys

from rich.console import Console
from .config import get_config
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

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
    config = get_config()
    config.set_api_key(company, api_key)

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

class RichHelpFormatter(argparse.HelpFormatter):
    """Custom help formatter that uses Rich for colorized output"""
    
    def __init__(self, prog):
        super().__init__(prog, max_help_position=40, width=100)
        self._console = Console()
    
    def format_help(self):
        # Get the standard help text
        help_text = super().format_help()
        
        # Use Rich to display it with colors
        self._console.print()
        self._console.print(f"[bold cyan]keprompt[/] [dim]v{__version__}[/] - [bold green]Prompt Engineering Tool[/]")
        self._console.print()
        
        # Add Quick Start section at the top
        self._console.print(f"[bold yellow]⚡ Quick Start for the Impatient:[/]")
        self._console.print(f"  [dim]1. Find a prompt:       [/][blue]keprompt -p simple[/]")
        self._console.print(f"  [green]   Shows prompts matching prompts/*simple*.prompt with their allowed parameters and default values[/]")
        self._console.print(f"  [dim]2. Run the prompt:      [/][blue]keprompt -e simple --param llm openai/gpt-4o-mini[/]")
        self._console.print(f"  [green]   → Note the Session ID in output: \"Session: 06e760ed\"[/]")
        self._console.print(f"  [dim]3. Continue chatting:   [/][blue]keprompt --session 06e760ed --answer \"Who is William Tell?\"[/]")
        self._console.print(f"  [green]   Uses the session ID and --answer to continue the conversation[/]")
        self._console.print(f"  [dim]4. View/debug session:  [/][blue]keprompt --view-session 06e760ed[/]")
        self._console.print(f"  [green]   To view/debug the interaction with the LLM[/]")
        self._console.print()
        
        # Split help into sections
        lines = help_text.split('\n')
        current_section = None
        
        for line in lines:
            if line.startswith('usage:'):
                self._console.print(f"[bold yellow]Usage:[/]")
                usage_line = line.replace('usage: __main__.py', 'keprompt')
                self._console.print(f"  [dim]{usage_line[7:]}[/]")  # Remove 'usage: '
                self._console.print()
            elif line.strip() == 'Prompt Engineering Tool.':
                continue  # Skip this as we already showed it
            elif line.strip() == 'options:':
                self._console.print(f"[bold yellow]Options:[/]")
                self._console.print(f"  [cyan]-h, --help[/]            Show this help message and exit")
                self._console.print()
            elif line.endswith(':') and not line.startswith('  '):
                # This is a section header - add blank line before
                section_name = line.rstrip(':')
                self._console.print()  # Blank line before each group
                
                if section_name == 'Start a New Session':
                    self._console.print(f"[bold green]🚀 {section_name}:[/]")
                elif section_name == 'Continue an Existing Session':
                    self._console.print(f"[bold green]🔄 {section_name}:[/]")
                elif section_name == 'Session History & Review':
                    self._console.print(f"[bold green]📋 {section_name}:[/]")
                elif section_name == 'Prompt Management':
                    self._console.print(f"[bold green]📝 {section_name}:[/]")
                elif section_name == 'Available Functions':
                    self._console.print(f"[bold green]⚙️  {section_name}:[/]")
                elif section_name == 'LLM API Providers':
                    self._console.print(f"[bold green]🤖 {section_name}:[/]")
                elif section_name == 'Database Operations':
                    self._console.print(f"[bold green]🗄️  {section_name}:[/]")
                elif section_name == 'System Management & Updates':
                    self._console.print(f"[bold green]🔧 {section_name}:[/]")
                elif section_name == 'Development & Debugging':
                    self._console.print(f"[bold green]🐛 {section_name}:[/]")
                elif section_name == 'General':
                    self._console.print(f"[bold green]ℹ️  {section_name}:[/]")
                
                current_section = section_name
            elif line.startswith('  -') or line.startswith('  --'):
                # This is an argument line
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    arg_part = parts[0].strip()
                    desc_part = parts[1] if len(parts) > 1 else ""
                    self._console.print(f"  [cyan]{arg_part}[/] {desc_part}")
                else:
                    self._console.print(f"  [cyan]{line.strip()}[/]")
                
            elif line.startswith('                        '):
                # This is a continuation of the description
                self._console.print(f"                        [dim]{line.strip()}[/]")
            elif line.strip():
                # Any other non-empty line
                self._console.print(line)
        
        self._console.print()
        self._console.print("[dim]For more information, visit: https://github.com/JerryWestrick/keprompt[/]")
        
        # Return empty string since we've already printed everything
        return ""

def print_rich_help():
    """Print help using Rich formatting"""
    parser = argparse.ArgumentParser(
        description="Prompt Engineering Tool.",
        formatter_class=RichHelpFormatter,
        add_help=False  # We'll handle help ourselves
    )
    
    # Add all the same arguments as get_cmd_args() but don't parse
    # 1. Start a New Session
    new_session_group = parser.add_argument_group('Start a New Session')
    new_session_group.add_argument('-e', '--execute', nargs='?', const='*', help='Execute one or more Prompts')
    new_session_group.add_argument('--param', nargs=2, action='append',metavar=('key', 'value'),help='Add key/value pairs (for use with --execute)')
    
    # 2. Continue an Existing Session
    continue_session_group = parser.add_argument_group('Continue an Existing Session')
    continue_session_group.add_argument('--session', metavar='SESSION_ID', help='Load/save session state by session ID')
    continue_session_group.add_argument('--answer', metavar='TEXT', help='New user response for session (--session SESSION_ID)')
    
    # 3. Session History & Review
    session_group = parser.add_argument_group('Session History & Review')
    session_group.add_argument('--list-sessions', action='store_true', help='List all available sessions')
    session_group.add_argument('--recent-sessions', type=int, nargs='?', const=20, help='List recent sessions')
    session_group.add_argument('--view-session', nargs='?', const='', metavar='SESSION_ID', help='View session history and details (pre-select SESSION_ID)')
    
    # 4. Prompt Management
    prompt_group = parser.add_argument_group('Prompt Management')
    prompt_group.add_argument('-p', '--prompts', nargs='?', const='*', help='List Prompts')
    prompt_group.add_argument('-c', '--code', nargs='?', const='*', help='List code in Prompts')
    prompt_group.add_argument('-l', '--list', nargs='?', const='*', help='List Prompt files, or specify: companies, providers')
    prompt_group.add_argument('-s', '--statements', action='store_true', help='List supported prompt statement types and exit')
    
    # 5. Available Functions
    functions_group = parser.add_argument_group('Available Functions')
    functions_group.add_argument('-f', '--functions', action='store_true', help='List functions available to AI and exit')
    
    # 6. LLM API Providers
    providers_group = parser.add_argument_group('LLM API Providers')
    providers_group.add_argument('-m', '--models', nargs='?', const='', help='List models (optionally filter by model name pattern)')
    providers_group.add_argument('--company', help='Filter models by company name pattern')
    providers_group.add_argument('--provider', help='Filter models by provider name pattern')
    providers_group.add_argument('-k', '--key', action='store_true', help='Ask for (new) Company Key')
    
    # 7. Database Operations
    database_group = parser.add_argument_group('Database Operations')
    database_group.add_argument('--init-db', action='store_true', help='Initialize database and create tables')
    database_group.add_argument('--delete-db', action='store_true', help='Delete entire database (Tom\'s nuclear option)')
    database_group.add_argument('--truncate-db', action='store_true', help='Clean up old sessions (Dick\'s managed cleanup)')
    database_group.add_argument('--max-days', type=int, help='Maximum age in days for --truncate-db')
    database_group.add_argument('--max-count', type=int, help='Maximum number of sessions for --truncate-db')
    database_group.add_argument('--max-gb', type=float, help='Maximum database size in GB for --truncate-db')
    database_group.add_argument('--db-stats', action='store_true', help='Show database statistics')
    
    # 8. System Management & Updates
    system_group = parser.add_argument_group('System Management & Updates')
    system_group.add_argument('--init', action='store_true', help='Initialize prompts and functions directories')
    system_group.add_argument('--update-models', metavar='PROVIDER', help='Update models for a provider or "All" for all providers')
    system_group.add_argument('--check-builtins', action='store_true', help='Check for built-in function updates')
    system_group.add_argument('--update-builtins', action='store_true', help='Update built-in functions')
    system_group.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')
    
    # 9. Development & Debugging
    debug_group = parser.add_argument_group('Development & Debugging')
    debug_group.add_argument('--debug', action='store_true', help='Enable structured logging + rich output to STDERR')
    debug_group.add_argument('--vm-debug', action='store_true', help='Enable detailed VM statement execution debugging')
    debug_group.add_argument('--debug-session', action='store_true', help='Save execution to timestamped debug session for analysis')
    
    # 10. General
    general_group = parser.add_argument_group('General')
    general_group.add_argument('-v', '--version', action='store_true', help='Show version information and exit')
    
    # Print the help
    parser.print_help()

def get_cmd_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt Engineering Tool.")
    
    # 1. Start a New Session
    new_session_group = parser.add_argument_group('Start a New Session')
    new_session_group.add_argument('-e', '--execute', nargs='?', const='*', help='Execute one or more Prompts')
    new_session_group.add_argument('--param', nargs=2, action='append',metavar=('key', 'value'),help='Add key/value pairs (for use with --execute)')
    
    # 2. Continue an Existing Session
    continue_session_group = parser.add_argument_group('Continue an Existing Session')
    continue_session_group.add_argument('--session', metavar='SESSION_ID', help='Load/save session state by session ID')
    continue_session_group.add_argument('--answer', metavar='TEXT', help='Continue session with user response (use with --session SESSION_ID)')
    
    # 3. Session History & Review
    session_group = parser.add_argument_group('Session History & Review')
    session_group.add_argument('--list-sessions', action='store_true', help='List all available sessions')
    session_group.add_argument('--recent-sessions', type=int, nargs='?', const=20, help='List recent sessions')
    session_group.add_argument('--view-session', nargs='?', const='', metavar='SESSION_ID', help='View session history and details (optionally specify session ID)')
    
    # 4. Prompt Management
    prompt_group = parser.add_argument_group('Prompt Management')
    prompt_group.add_argument('-p', '--prompts', nargs='?', const='*', help='List Prompts')
    prompt_group.add_argument('-c', '--code', nargs='?', const='*', help='List code in Prompts')
    prompt_group.add_argument('-l', '--list', nargs='?', const='*', help='List Prompt files, or specify: company/companies, provider/providers')
    prompt_group.add_argument('-s', '--statements', action='store_true', help='List supported prompt statement types and exit')
    
    # 5. Available Functions
    functions_group = parser.add_argument_group('Available Functions')
    functions_group.add_argument('-f', '--functions', action='store_true', help='List functions available to AI and exit')
    
    # 6. LLM API Providers
    providers_group = parser.add_argument_group('LLM API Providers')
    providers_group.add_argument('-m', '--models', nargs='?', const='', help='List models (optionally filter by model name pattern)')
    providers_group.add_argument('--company', help='Filter models by company name pattern')
    providers_group.add_argument('--provider', help='Filter models by provider name pattern')
    providers_group.add_argument('-k', '--key', action='store_true', help='Ask for (new) Company Key')
    
    # 7. Database Operations
    database_group = parser.add_argument_group('Database Operations')
    database_group.add_argument('--init-db', action='store_true', help='Initialize database and create tables')
    database_group.add_argument('--delete-db', action='store_true', help='Delete entire database (Tom\'s nuclear option)')
    database_group.add_argument('--truncate-db', action='store_true', help='Clean up old sessions (Dick\'s managed cleanup)')
    database_group.add_argument('--max-days', type=int, help='Maximum age in days for --truncate-db')
    database_group.add_argument('--max-count', type=int, help='Maximum number of sessions for --truncate-db')
    database_group.add_argument('--max-gb', type=float, help='Maximum database size in GB for --truncate-db')
    database_group.add_argument('--db-stats', action='store_true', help='Show database statistics')
    
    # 8. System Management & Updates
    system_group = parser.add_argument_group('System Management & Updates')
    system_group.add_argument('--init', action='store_true', help='Initialize prompts and functions directories')
    system_group.add_argument('--update-models', metavar='PROVIDER', help='Update model definitions for specified provider (e.g., OpenRouter) or "All" for all providers')
    system_group.add_argument('--check-builtins', action='store_true', help='Check for built-in function updates')
    system_group.add_argument('--update-builtins', action='store_true', help='Update built-in functions')
    system_group.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')
    
    # 9. Development & Debugging
    debug_group = parser.add_argument_group('Development & Debugging')
    debug_group.add_argument('--debug', action='store_true', help='Enable structured logging + rich output to STDERR')
    debug_group.add_argument('--vm-debug', action='store_true', help='Enable detailed VM statement execution debugging')
    debug_group.add_argument('--debug-session', action='store_true', help='Save execution to timestamped debug session for analysis')
    
    # 10. General
    general_group = parser.add_argument_group('General')
    general_group.add_argument('-v', '--version', action='store_true', help='Show version information and exit')

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
    # Check for help first, before creating directories
    if len(sys.argv) > 1 and (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        print_rich_help()
        return
    
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
        from .model_updater import update_models
        update_models(args.update_models)
        return

    if args.key:
        get_new_api_key()

    # Handle database management commands
    if args.delete_db:
        from .db_cli import delete_database
        delete_database()
        return

    if args.truncate_db:
        from .db_cli import truncate_database
        truncate_database(
            max_days=args.max_days,
            max_count=args.max_count,
            max_gb=args.max_gb
        )
        return

    if args.db_stats:
        from .db_cli import show_database_stats
        show_database_stats()
        return

    if args.recent_sessions is not None:
        from .db_cli import list_recent_conversations
        list_recent_conversations(limit=args.recent_sessions)
        return

    if args.init_db:
        from .db_cli import init_database
        init_database()
        return

    # Handle conversation viewing commands
    if args.list_sessions:
        from .db_cli import list_recent_conversations
        list_recent_conversations(limit=100)
        return

    if args.view_session is not None:
        # Check if textual is available for TUI mode
        try:
            from .session_viewer import view_session_tui
            session_id = args.view_session or ""
            view_session_tui(session_id)  # Pass session ID or empty string for all
        except ImportError:
            # Fall back to Rich-based viewer if textual is not available
            console.print("[yellow]Textual not available, using basic viewer[/yellow]")
            console.print("[red]Rich-based viewer requires a specific session name[/red]")
        return

    # Handle conversation mode
    if args.session:
        
        conversation_name = args.session
        
        # Determine logging mode and identifier
        from .keprompt_logger import LogMode
        
        log_identifier = None
        if args.debug:
            log_mode = LogMode.DEBUG
        else:
            log_mode = LogMode.PRODUCTION
        
        log_identifier = conversation_name
        
        if args.answer:
            # Continue existing conversation with user answer
            from .keprompt_vm import make_statement
            from .AiPrompt import AiTextPart
            
            step = VM(None, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_session)  # No prompt file
            loaded = step.load_session(conversation_name)
            
            if not loaded:
                console.print(f"[bold red]Error: Conversation '{conversation_name}' not found[/bold red]")
                sys.exit(1)
            
            # Reuse the existing session ID instead of generating a new one
            step.prompt_uuid = conversation_name
            
            # For conversation continuations, try to inherit prompt metadata from the conversation
            # Look for the original prompt name in the variables to get metadata
            original_filename = step.vdict.get('filename')
            if original_filename and isinstance(original_filename, str) and original_filename.endswith('.prompt'):
                # Try to extract prompt metadata from the original file
                try:
                    with open(original_filename, 'r') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('.prompt '):
                            # Parse the .prompt statement to get metadata
                            import json
                            json_content = "{" + first_line[8:] + "}"  # Remove '.prompt ' and wrap in braces
                            prompt_data = json.loads(json_content)
                            step.prompt_name = prompt_data.get("name", "")
                            step.prompt_version = prompt_data.get("version", "")
                            step.expected_params = prompt_data.get("params", {})
                except:
                    # If we can't read the original file, continue without metadata
                    pass
            
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
            # step.save_session(conversation_name)
            
        elif args.execute:
            # Start new conversation with prompt file
            glob_files = glob_prompt(args.execute)
            
            if glob_files:
                for prompt_file in glob_files:
                    step = VM(str(prompt_file), global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_session)
                    step.parse_prompt()
                    step.execute()
                    
                    # Save conversation after execution
                    step.save_session(conversation_name)
            else:
                pname = prompt_pattern(args.execute)
                log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        else:
            # No --answer or --execute specified with --session
            console.print("[bold red]Error: --session requires either --answer or --execute[/bold red]")
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
                else:
                    log_mode = LogMode.PRODUCTION
                    log_identifier = os.path.splitext(os.path.basename(prompt_file))[0]
                
                # If --debug-session is enabled, automatically save to session
                if args.debug_session:
                    # Create debug session name with timestamp
                    import time
                    prompt_name = os.path.splitext(os.path.basename(prompt_file))[0]
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    debug_session_name = f"{prompt_name}_debug_{timestamp}"
                    
                    console.print(f"[cyan]--debug-session enabled: Saving execution to session '{debug_session_name}'[/cyan]")
                    
                    step = VM(str(prompt_file), global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_session)
                    step.parse_prompt()
                    step.execute()
                    
                    # Save the session for analysis
                    step.save_session(debug_session_name)
                    
                    console.print(f"[green]Debug session saved! View with: keprompt --view-session {debug_session_name}[/green]")
                else:
                    step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_session)
                    step.parse_prompt()
                    step.execute()
        else:
            pname = prompt_pattern(args.execute)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return




if __name__ == "__main__":
    main()

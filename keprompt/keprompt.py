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
from .keprompt_utils import print_simple_table, format_model_count_data, handle_error
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
    columns = [
        {'name': 'Company', 'style': 'cyan', 'no_wrap': True},
        {'name': 'Model Count', 'style': 'green', 'justify': 'right'}
    ]
    
    rows = format_model_count_data(AiRegistry.models, 'company')
    print_simple_table("Available Companies (Model Creators)", columns, rows)

def print_providers():
    """Print all available providers (API services)"""
    columns = [
        {'name': 'Provider', 'style': 'cyan', 'no_wrap': True},
        {'name': 'Model Count', 'style': 'green', 'justify': 'right'}
    ]
    
    rows = format_model_count_data(AiRegistry.models, 'provider')
    print_simple_table("Available Providers (API Services)", columns, rows)

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
            handle_error(f"parsing file {prompt_file}: {str(e)}", exit_code=1, show_exception=True)
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
        self._console.print(f"[bold yellow]🔗 New JSON API Commands:[/]")
        self._console.print(f"  [dim]• Get resources:        [/][blue]keprompt get models --provider OpenRouter[/]")
        self._console.print(f"  [dim]• Create session:       [/][blue]keprompt create session --prompt simple[/]")
        self._console.print(f"  [dim]• Continue session:     [/][blue]keprompt update session <id> --answer \"Hello\"[/]")
        self._console.print()
        self._console.print(f"[bold yellow]🔧 VM Namespace (New):[/]")
        self._console.print(f"  [green]Prompts can now access VM state: [/][blue]<<VM.session_id>>, <<VM.model_name>>, <<VM.total_cost>>[/]")
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
                elif section_name == 'JSON API Commands (New)':
                    self._console.print(f"[bold green]🔗 {section_name}:[/]")
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
    """Print help using Rich formatting - New JSON API Commands Only"""
    console = Console()
    
    console.print()
    console.print(f"[bold cyan]keprompt[/] [dim]v{__version__}[/] - [bold green]Prompt Engineering Tool[/]")
    console.print()
    
    # Usage
    console.print(f"[bold yellow]Usage:[/]")
    console.print(f"  [dim]keprompt <verb> <resource> [options][/]")
    console.print(f"  [dim]keprompt --help | --version[/]")
    console.print()
    
    # Quick Start
    console.print(f"[bold yellow]⚡ Quick Start:[/]")
    console.print(f"  [dim]1. List prompts:        [/][blue]keprompt get prompts[/]")
    console.print(f"  [dim]2. Run a prompt:        [/][blue]keprompt create session --prompt simple[/]")
    console.print(f"  [dim]3. Continue session:    [/][blue]keprompt update session <id> --answer \"Hello\"[/]")
    console.print(f"  [dim]4. List sessions:       [/][blue]keprompt get sessions[/]")
    console.print(f"  [dim]5. View session:        [/][blue]keprompt get session <id>[/]")
    console.print()
    
    # Resource Discovery Commands
    console.print(f"[bold green]📋 Resource Discovery:[/]")
    console.print(f"  [cyan]keprompt get prompts [pattern][/]")
    console.print(f"    List prompts with metadata and source code")
    console.print(f"  [cyan]keprompt get models [--name pattern] [--provider name] [--company name][/]")
    console.print(f"    List available AI models with filtering")
    console.print(f"  [cyan]keprompt get providers[/]")
    console.print(f"    List all API service providers")
    console.print(f"  [cyan]keprompt get companies[/]")
    console.print(f"    List all model creators/companies")
    console.print(f"  [cyan]keprompt get functions[/]")
    console.print(f"    List all available functions for AI")
    console.print()
    
    # Session Management Commands
    console.print(f"[bold green]🔄 Session Management:[/]")
    console.print(f"  [cyan]keprompt get sessions[/]")
    console.print(f"    List all available sessions")
    console.print(f"  [cyan]keprompt get session <session_id>[/]")
    console.print(f"    Get detailed session history and data")
    console.print(f"  [cyan]keprompt create session --prompt <name> [--param key value]...[/]")
    console.print(f"    Create new session by executing a prompt")
    console.print(f"  [cyan]keprompt update session <session_id> --answer <message>[/]")
    console.print(f"    Continue conversation in existing session")
    console.print(f"  [cyan]keprompt delete session <session_id>[/]")
    console.print(f"    Delete a session and its history")
    console.print()
    
    # System Management Commands
    console.print(f"[bold green]🔧 System Management:[/]")
    console.print(f"  [cyan]keprompt create workspace[/]")
    console.print(f"    Initialize prompts and functions directories")
    console.print(f"  [cyan]keprompt update models [provider][/]")
    console.print(f"    Update model definitions for provider or all")
    console.print(f"  [cyan]keprompt get builtins[/]")
    console.print(f"    Check built-in functions status")
    console.print(f"  [cyan]keprompt update builtins[/]")
    console.print(f"    Update built-in functions")
    console.print()
    
    # Database Management Commands
    console.print(f"[bold green]🗄️  Database Management:[/]")
    console.print(f"  [cyan]keprompt get database[/]")
    console.print(f"    Show database statistics and information")
    console.print(f"  [cyan]keprompt create database[/]")
    console.print(f"    Initialize database and create tables")
    console.print(f"  [cyan]keprompt delete database[/]")
    console.print(f"    Delete entire database (nuclear option)")
    console.print(f"  [cyan]keprompt update database [--max-days N] [--max-count N] [--max-gb N][/]")
    console.print(f"    Clean up old sessions with optional limits")
    console.print()
    
    # VM Namespace
    console.print(f"[bold green]✨ VM Namespace (New Feature):[/]")
    console.print(f"  Prompts can now access VM execution state:")
    console.print(f"  [blue]<<VM.session_id>>[/] - Unique session identifier")
    console.print(f"  [blue]<<VM.model_name>>[/] - Current model name")
    console.print(f"  [blue]<<VM.provider>>[/] - API provider")
    console.print(f"  [blue]<<VM.total_cost>>[/] - Total execution cost")
    console.print(f"  [blue]<<VM.interaction_no>>[/] - Number of API calls")
    console.print(f"  [blue]<<VM.toks_in>>, <<VM.toks_out>>[/] - Token counts")
    console.print(f"  [dim]And many more VM properties for dynamic prompts[/]")
    console.print()
    
    # General Options
    console.print(f"[bold green]ℹ️  General Options:[/]")
    console.print(f"  [cyan]-h, --help[/]     Show this help message and exit")
    console.print(f"  [cyan]-v, --version[/]  Show version information and exit")
    console.print()
    
    # Examples
    console.print(f"[bold yellow]📚 Examples:[/]")
    console.print(f"  [dim]# List all prompts[/]")
    console.print(f"  [blue]keprompt get prompts[/]")
    console.print()
    console.print(f"  [dim]# Run a prompt with parameters[/]")
    console.print(f"  [blue]keprompt create session --prompt math-tutor --param model gpt-4o[/]")
    console.print()
    console.print(f"  [dim]# Continue a conversation[/]")
    console.print(f"  [blue]keprompt update session abc123 --answer \"What is 2+2?\"[/]")
    console.print()
    console.print(f"  [dim]# List models from specific provider[/]")
    console.print(f"  [blue]keprompt get models --provider OpenRouter[/]")
    console.print()
    
    console.print(f"[dim]For more information, visit: https://github.com/JerryWestrick/keprompt[/]")
    console.print()

def get_cmd_args() -> argparse.Namespace:
    """Minimal argument parser - most functionality moved to JSON API"""
    parser = argparse.ArgumentParser(description="Prompt Engineering Tool.")
    
    # Only keep essential arguments
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit')
    
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
    
    # Check for new REST-style commands first
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['get', 'create', 'update', 'delete']:
        from .json_api import handle_json_command
        exit_code = handle_json_command(sys.argv[1:])
        sys.exit(exit_code)
    
    # Ensure 'prompts' directory exists
    if not os.path.exists('prompts'):
        os.makedirs('prompts')

    if not os.path.exists('logs'):
        os.makedirs('logs')

    args = get_cmd_args()

    if args.version:
        # Print the version and exit
        console.print(f"[bold cyan]keprompt[/] [bold green]version[/] [bold magenta]{__version__}[/]")
        return

    # If no JSON API command and no version, show migration message
    console.print()
    console.print(f"[bold yellow]🚀 keprompt has been upgraded![/]")
    console.print()
    console.print(f"[bold green]Old command format has been replaced with a clean JSON API.[/]")
    console.print()
    console.print(f"[bold cyan]New Commands:[/]")
    console.print(f"  [dim]• List prompts:          [/][blue]keprompt get prompts[/]")
    console.print(f"  [dim]• List models:           [/][blue]keprompt get models[/]")
    console.print(f"  [dim]• Run a prompt:         [/][blue]keprompt create session --prompt simple[/]")
    console.print(f"  [dim]• Continue session:     [/][blue]keprompt update session <id> --answer \"Hello\"[/]")
    console.print(f"  [dim]• List sessions:        [/][blue]keprompt get sessions[/]")
    console.print(f"  [dim]• View session:         [/][blue]keprompt get session <id>[/]")
    console.print()
    console.print(f"[bold yellow]For complete help:[/] [blue]keprompt --help[/]")
    console.print()
    console.print(f"[bold green]✨ New VM Namespace:[/] Prompts can now access [blue]<<VM.session_id>>, <<VM.model_name>>, <<VM.total_cost>>[/]")
    console.print()




if __name__ == "__main__":
    main()

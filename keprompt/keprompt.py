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
    parser.add_argument('--vm-debug', action='store_true', help='Enable detailed VM statement execution debugging')
    parser.add_argument('--debug-conversation', action='store_true', help='Save execution to timestamped debug conversation for analysis')
    parser.add_argument('-r', '--remove', action='store_true', help='remove all .~nn~. files from sub directories')
    parser.add_argument('--init', action='store_true', help='Initialize prompts and functions directories')
    parser.add_argument('--check-builtins', action='store_true', help='Check for built-in function updates')
    parser.add_argument('--update-builtins', action='store_true', help='Update built-in functions')
    parser.add_argument('--update-models', metavar='PROVIDER', help='Update model definitions for specified provider (e.g., OpenRouter) or "All" for all providers')
    parser.add_argument('--conversation', metavar='NAME', help='Load/save conversation state')
    parser.add_argument('--answer', metavar='TEXT', help='Continue conversation with user response')
    parser.add_argument('--view-conversation', metavar='NAME', help='View conversation history and details')
    parser.add_argument('--list-conversations', action='store_true', help='List all available conversations')

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

def list_conversations():
    """List all available conversations with summary information"""
    import json
    import sqlite3
    from datetime import datetime
    
    conversations_dir = Path('conversations')
    if not conversations_dir.exists():
        console.print("[bold yellow]No conversations directory found.[/bold yellow]")
        return
    
    conversation_files = list(conversations_dir.glob('*.conversation'))
    if not conversation_files:
        console.print("[bold yellow]No conversations found.[/bold yellow]")
        return
    
    # Create table for conversation list
    table = Table(title="Available Conversations")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Model", style="green", no_wrap=True)
    table.add_column("Messages", style="blue", justify="right")
    table.add_column("Last Updated", style="magenta")
    table.add_column("Total Cost", style="yellow", justify="right")
    
    # Get cost data from database if available
    cost_data = {}
    try:
        if os.path.exists('prompts/costs.db'):
            conn = sqlite3.connect('prompts/costs.db')
            cursor = conn.execute("""
                SELECT prompt_semantic_name, COUNT(*) as calls, SUM(estimated_costs) as total_cost
                FROM cost_tracking 
                WHERE prompt_semantic_name IS NOT NULL AND prompt_semantic_name != ''
                GROUP BY prompt_semantic_name
            """)
            for row in cursor.fetchall():
                cost_data[row[0]] = {'calls': row[1], 'total_cost': row[2]}
            conn.close()
    except:
        pass  # Continue without cost data if database unavailable
    
    for conv_file in sorted(conversation_files):
        try:
            with open(conv_file, 'r') as f:
                data = json.load(f)
            
            name = conv_file.stem
            vm_state = data.get('vm_state', {})
            messages = data.get('messages', [])
            
            model = vm_state.get('model_name', 'Unknown')
            message_count = len(messages)
            created = vm_state.get('created', 'Unknown')
            
            # Try to get semantic name for cost lookup
            variables = data.get('variables', {})
            semantic_name = None
            
            # Try to extract semantic name from original filename
            original_filename = variables.get('filename', '')
            if original_filename and isinstance(original_filename, str) and original_filename.endswith('.prompt'):
                try:
                    with open(original_filename, 'r') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('.prompt '):
                            json_content = "{" + first_line[8:] + "}"
                            prompt_data = json.loads(json_content)
                            semantic_name = prompt_data.get("name", "")
                except:
                    pass
            
            # Get cost information
            total_cost = "N/A"
            if semantic_name and semantic_name in cost_data:
                total_cost = f"${cost_data[semantic_name]['total_cost']:.6f}"
            
            table.add_row(name, model, str(message_count), created, total_cost)
            
        except Exception as e:
            table.add_row(conv_file.stem, "Error", "?", "?", f"Error: {str(e)}")
    
    console.print(table)

def view_conversation(conversation_name: str):
    """View detailed conversation history and information with execution analysis"""
    import json
    import sqlite3
    from datetime import datetime
    from collections import Counter
    
    conv_file = Path(f'conversations/{conversation_name}.conversation')
    if not conv_file.exists():
        console.print(f"[bold red]Conversation '{conversation_name}' not found.[/bold red]")
        return
    
    try:
        with open(conv_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error reading conversation: {e}[/bold red]")
        return
    
    vm_state = data.get('vm_state', {})
    messages = data.get('messages', [])
    variables = data.get('variables', {})
    
    # Check if this is a debug conversation
    is_debug_conversation = '_debug_' in conversation_name
    
    # Display conversation summary
    console.print(f"\n[bold cyan]Conversation: {conversation_name}[/bold cyan]")
    if is_debug_conversation:
        console.print("[yellow]🔍 Debug Conversation - Execution Analysis Available[/yellow]")
    console.print("─" * 60)
    
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Field", style="cyan", width=15)
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Model:", vm_state.get('model_name', 'Unknown'))
    summary_table.add_row("Company:", vm_state.get('company', 'Unknown'))
    summary_table.add_row("Messages:", str(len(messages)))
    summary_table.add_row("Interactions:", str(vm_state.get('interaction_no', 0)))
    summary_table.add_row("Created:", vm_state.get('created', 'Unknown'))
    
    # Analyze function calls if this is a debug conversation
    if is_debug_conversation:
        function_calls = []
        duplicate_calls = []
        
        for message in messages:
            if message.get('role') == 'assistant':
                content = message.get('content', [])
                for part in content:
                    if part.get('type') == 'tool':
                        func_name = part.get('name', 'unknown')
                        func_args = part.get('arguments', {})
                        call_signature = f"{func_name}({func_args})"
                        function_calls.append((func_name, func_args, call_signature))
        
        # Find duplicates
        call_counts = Counter(call[2] for call in function_calls)
        duplicates = {call: count for call, count in call_counts.items() if count > 1}
        
        if function_calls:
            summary_table.add_row("Function Calls:", str(len(function_calls)))
            summary_table.add_row("Unique Calls:", str(len(call_counts)))
            if duplicates:
                summary_table.add_row("Duplicate Calls:", f"{len(duplicates)} patterns")
    
    # Try to get semantic name and cost information
    semantic_name = None
    original_filename = variables.get('filename', '')
    if original_filename and isinstance(original_filename, str) and original_filename.endswith('.prompt'):
        summary_table.add_row("Original Prompt:", os.path.basename(original_filename))
        try:
            with open(original_filename, 'r') as f:
                first_line = f.readline().strip()
                if first_line.startswith('.prompt '):
                    json_content = "{" + first_line[8:] + "}"
                    prompt_data = json.loads(json_content)
                    semantic_name = prompt_data.get("name", "")
                    if semantic_name:
                        summary_table.add_row("Semantic Name:", semantic_name)
                        summary_table.add_row("Version:", prompt_data.get("version", ""))
        except:
            pass
    
    # Get cost information from database
    if semantic_name:
        try:
            if os.path.exists('prompts/costs.db'):
                conn = sqlite3.connect('prompts/costs.db')
                cursor = conn.execute("""
                    SELECT COUNT(*) as calls, SUM(estimated_costs) as total_cost, 
                           SUM(tokens_in) as total_tokens_in, SUM(tokens_out) as total_tokens_out
                    FROM cost_tracking 
                    WHERE prompt_semantic_name = ?
                """, (semantic_name,))
                row = cursor.fetchone()
                if row and row[0] > 0:
                    summary_table.add_row("Total Calls:", str(row[0]))
                    summary_table.add_row("Total Cost:", f"${row[1]:.6f}")
                    summary_table.add_row("Total Tokens In:", str(row[2]))
                    summary_table.add_row("Total Tokens Out:", str(row[3]))
                conn.close()
        except:
            pass
    
    console.print(summary_table)
    console.print()
    
    # Show detailed duplicate analysis for debug conversations
    if is_debug_conversation and function_calls:
        console.print("[bold yellow]🔍 Function Call Analysis:[/bold yellow]")
        console.print("─" * 60)
        
        if duplicates:
            console.print("[bold red]⚠️  Duplicate Function Calls Detected:[/bold red]")
            dup_table = Table(show_header=True)
            dup_table.add_column("Function Call", style="cyan")
            dup_table.add_column("Count", style="red", justify="right")
            dup_table.add_column("Impact", style="yellow")
            
            for call_sig, count in duplicates.items():
                # Determine impact
                if 'readfile' in call_sig:
                    impact = "Redundant file reads"
                elif 'writefile' in call_sig:
                    impact = "Duplicate file writes"
                elif 'execcmd' in call_sig:
                    impact = "Repeated commands"
                else:
                    impact = "Unnecessary execution"
                
                dup_table.add_row(call_sig, str(count), impact)
            
            console.print(dup_table)
            console.print()
        
        # Show function call sequence
        console.print("[bold cyan]📋 Function Call Sequence:[/bold cyan]")
        seq_table = Table(show_header=True)
        seq_table.add_column("#", style="dim", width=3)
        seq_table.add_column("Function", style="green")
        seq_table.add_column("Arguments", style="blue")
        seq_table.add_column("Status", style="white")
        
        for idx, (func_name, func_args, call_sig) in enumerate(function_calls, 1):
            # Check if this is a duplicate
            status = "🔄 DUPLICATE" if call_counts[call_sig] > 1 else "✅ Unique"
            
            # Format arguments for display
            args_str = str(func_args)
            if len(args_str) > 50:
                args_str = args_str[:47] + "..."
            
            seq_table.add_row(str(idx), func_name, args_str, status)
        
        console.print(seq_table)
        console.print()
    
    # Display conversation messages
    console.print("[bold cyan]Conversation History:[/bold cyan]")
    console.print("─" * 60)
    
    for i, message in enumerate(messages, 1):
        role = message.get('role', 'unknown')
        content = message.get('content', [])
        
        # Role styling
        role_style = {
            'user': '[bold blue]User[/bold blue]',
            'assistant': '[bold green]Assistant[/bold green]',
            'system': '[bold magenta]System[/bold magenta]',
            'tool': '[bold yellow]Tool[/bold yellow]'
        }.get(role, f'[bold white]{role.title()}[/bold white]')
        
        console.print(f"\n{i:2d}. {role_style}:")
        
        # Display content
        for part in content:
            part_type = part.get('type', 'unknown')
            
            if part_type == 'text':
                text = part.get('text', '')
                # Clean up LaTeX formatting for better readability
                text = text.replace('\\(', '').replace('\\)', '')
                text = text.replace('\\[', '\n    ').replace('\\]', '\n    ')
                text = text.replace('\\displaystyle', '')
                text = text.replace('\\frac{', '(').replace('}{', ')/(').replace('}', ')')
                text = text.replace('\\;', ' ')
                text = text.replace('\\qquad', '   ')
                
                # Split long text into readable chunks
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        # Wrap very long lines
                        if len(line) > 80:
                            words = line.split(' ')
                            current_line = "    "
                            for word in words:
                                if len(current_line + word) > 80:
                                    console.print(current_line.rstrip(), style="white")
                                    current_line = "    " + word + " "
                                else:
                                    current_line += word + " "
                            if current_line.strip():
                                console.print(current_line.rstrip(), style="white")
                        else:
                            console.print(f"    {line}", style="white")
                
            elif part_type == 'tool':
                tool_name = part.get('name', 'unknown')
                tool_args = part.get('arguments', {})
                console.print(f"    [dim]🔧 Called: {tool_name}({tool_args})[/dim]")
                
            elif part_type == 'tool_result':
                result_content = part.get('content', '')
                console.print(f"    [dim]📤 Result: {result_content}[/dim]")
                
            else:
                console.print(f"    [dim]({part_type}: {part})[/dim]")
    
    # Display current variables (if any interesting ones)
    interesting_vars = {k: v for k, v in variables.items() 
                       if k not in ['Prefix', 'Postfix', 'Debug', 'Verbose'] and not k.startswith('_')}
    
    if interesting_vars:
        console.print(f"\n[bold cyan]Current Variables:[/bold cyan]")
        console.print("─" * 60)
        var_table = Table(show_header=False, box=None)
        var_table.add_column("Variable", style="cyan", width=20)
        var_table.add_column("Value", style="white")
        
        for key, value in interesting_vars.items():
            # Truncate long values
            str_value = str(value)
            if len(str_value) > 80:
                str_value = str_value[:77] + "..."
            var_table.add_row(key, str_value)
        
        console.print(var_table)

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

    # Handle conversation viewing commands
    if args.list_conversations:
        list_conversations()
        return

    if args.view_conversation:
        # Check if textual is available for TUI mode
        try:
            from .conversation_viewer import view_conversation_tui
            view_conversation_tui(args.view_conversation)
        except ImportError:
            # Fall back to Rich-based viewer if textual is not available
            console.print("[yellow]Textual not available, using basic viewer[/yellow]")
            view_conversation(args.view_conversation)
        return

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
            
            step = VM(None, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_conversation)  # No prompt file
            loaded = step.load_conversation(conversation_name)
            
            if not loaded:
                console.print(f"[bold red]Error: Conversation '{conversation_name}' not found[/bold red]")
                sys.exit(1)
            
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
            step.save_conversation(conversation_name)
            
        elif args.execute:
            # Start new conversation with prompt file
            glob_files = glob_prompt(args.execute)
            
            if glob_files:
                for prompt_file in glob_files:
                    step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_conversation)
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
                
                # If --debug-conversation is enabled, automatically save to conversation
                if args.debug_conversation:
                    # Ensure 'conversations' directory exists
                    if not os.path.exists('conversations'):
                        os.makedirs('conversations')
                    
                    # Create debug conversation name with timestamp
                    import time
                    prompt_name = os.path.splitext(os.path.basename(prompt_file))[0]
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    debug_conversation_name = f"{prompt_name}_debug_{timestamp}"
                    
                    console.print(f"[cyan]--debug-conversation enabled: Saving execution to conversation '{debug_conversation_name}'[/cyan]")
                    
                    step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_conversation)
                    step.parse_prompt()
                    step.execute()
                    
                    # Save the conversation for analysis
                    step.save_conversation(debug_conversation_name)
                    
                    console.print(f"[green]Debug conversation saved! View with: keprompt --view-conversation {debug_conversation_name}[/green]")
                else:
                    step = VM(prompt_file, global_variables, log_mode=log_mode, log_identifier=log_identifier, vm_debug=args.vm_debug, exec_debug=args.debug_conversation)
                    step.parse_prompt()
                    step.execute()
        else:
            pname = prompt_pattern(args.execute)
            log.error(f"[bold red]No Prompt files found with {pname}[/bold red]", extra={"markup": True})
        return




if __name__ == "__main__":
    main()

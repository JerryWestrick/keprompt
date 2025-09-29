"""
Utility functions to reduce code duplication across the keprompt codebase.
Simple, focused functions that the next programmer can easily understand.
"""

from rich.console import Console
from rich.table import Table
import sys
from typing import List, Dict, Any, Optional

console = Console()


def truncate_for_display(text: str, max_length: int) -> str:
    """
    Truncate text for display purposes with consistent ellipsis handling.
    
    Args:
        text: The text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text with '...' if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def create_simple_table(title: str, columns: List[Dict[str, Any]]) -> Table:
    """
    Create a Rich table with consistent styling.
    
    Args:
        title: Table title
        columns: List of column definitions with 'name', 'style', and optional 'justify', 'no_wrap'
        
    Returns:
        Configured Rich Table object
    """
    table = Table(title=title)
    
    for col in columns:
        table.add_column(
            col['name'], 
            style=col.get('style', 'white'),
            justify=col.get('justify', 'left'),
            no_wrap=col.get('no_wrap', False)
        )
    
    return table


def print_simple_table(title: str, columns: List[Dict[str, Any]], rows: List[List[str]]) -> None:
    """
    Print a table with data using consistent formatting.
    
    Args:
        title: Table title
        columns: Column definitions (same format as create_simple_table)
        rows: List of row data (each row is a list of strings)
    """
    table = create_simple_table(title, columns)
    
    for row in rows:
        table.add_row(*row)
    
    console.print(table)


def handle_error(message: str, exit_code: Optional[int] = None, show_exception: bool = False) -> None:
    """
    Handle errors consistently across the application.
    
    Args:
        message: Error message to display
        exit_code: If provided, exit with this code. If None, don't exit.
        show_exception: Whether to show the full exception traceback
    """
    console.print(f"[bold red]Error: {message}[/bold red]")
    
    if show_exception:
        console.print_exception()
    
    if exit_code is not None:
        sys.exit(exit_code)


def format_model_count_data(models_dict: Dict[str, Any], group_by_field: str) -> List[List[str]]:
    """
    Format model data for count tables (companies/providers).
    
    Args:
        models_dict: Dictionary of models
        group_by_field: Field to group by ('company' or 'provider')
        
    Returns:
        List of [name, count] rows for table display
    """
    groups = sorted(set(getattr(model, group_by_field) for model in models_dict.values()))
    
    rows = []
    for group in groups:
        count = sum(1 for model in models_dict.values() if getattr(model, group_by_field) == group)
        rows.append([group, str(count)])
    
    return rows


def standardize_variable_names(old_name: str) -> str:
    """
    Convert old inconsistent variable names to standardized versions.
    
    Args:
        old_name: The old variable name
        
    Returns:
        Standardized variable name
    """
    name_mappings = {
        'parms': 'params',
        'lno': 'line_number',
        'msg_no': 'message_number',
        'stmt_no': 'statement_number'
    }
    
    return name_mappings.get(old_name, old_name)

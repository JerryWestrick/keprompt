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



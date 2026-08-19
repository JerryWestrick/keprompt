"""
Database CLI commands for KePrompt.

Provides command-line interface for database management operations.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.table import Table

from .config import get_config
from .chat_manager import ChatManager
from .database import get_database, initialize_database, get_db_manager


console = Console()


def delete_database() -> None:
    """Delete the entire database (Tom's nuclear option)."""
    config = get_config()
    db_url = config.get_database_url()
    
    # For SQLite, delete the file
    if db_url.startswith('sqlite:///'):
        db_path = db_url[10:]  # Remove 'sqlite:///'
        db_file = Path(db_path)
        
        if db_file.exists():
            try:
                db_file.unlink()
                console.print(f"[bold green]✅ Database deleted: {db_path}[/bold green]")
            except OSError as e:
                console.print(f"[bold red]❌ Error deleting database: {e}[/bold red]")
                sys.exit(1)
        else:
            console.print(f"[yellow]⚠️  Database file not found: {db_path}[/yellow]")
    
    else:
        # For other databases, we can't delete the database itself, just clear tables
        console.print("[yellow]⚠️  Non-SQLite database detected. Use --truncate-db instead to clear data.[/yellow]")
        console.print(f"Database URL: {db_url}")


def truncate_database(max_days: int = None, max_count: int = None, max_gb: float = None) -> None:
    """Truncate database based on criteria (cleanup old chats)."""
    chat_manager = ChatManager()
    dbm = get_db_manager()

    console.print("[cyan]🧹 Starting database cleanup...[/cyan]")

    # Show current stats
    stats = dbm.get_database_stats()
    console.print(f"Current database: {stats['chat_count']} chats, "
                 f"{stats['cost_records']} cost records, "
                 f"{stats['database_size_mb']} MB")

    # Perform cleanup
    try:
        result = chat_manager.cleanup_chats(
            max_days=max_days,
            max_count=max_count,
            max_size_gb=max_gb
        )

        console.print(f"[bold green]✅ Cleanup complete![/bold green]")
        console.print(f"Deleted: {result['deleted_chats']} chats, "
                     f"{result['deleted_costs']} cost records")

        # Show new stats
        new_stats = dbm.get_database_stats()
        console.print(f"Remaining: {new_stats['chat_count']} chats, "
                     f"{new_stats['cost_records']} cost records, "
                     f"{new_stats['database_size_mb']} MB")

    except Exception as e:
        console.print(f"[bold red]❌ Error during cleanup: {e}[/bold red]")
        sys.exit(1)


def show_database_stats() -> None:
    """Show database statistics."""
    config = get_config()
    dbm = get_db_manager()

    try:
        stats = dbm.get_database_stats()

        # Create stats table
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        table.add_row("Database URL", config.get_database_url())
        table.add_row("Chats", str(stats['chat_count']))
        table.add_row("Cost Records", str(stats['cost_records']))
        table.add_row("Database Size", f"{stats['database_size_mb']} MB")

        if stats['database_size_bytes'] > 0:
            table.add_row("Database File", f"{stats['database_size_bytes']:,} bytes")

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]❌ Error getting database stats: {e}[/bold red]")
        sys.exit(1)


def init_database() -> None:
    """Initialize database and create tables."""
    config = get_config()
    db_url = config.get_database_url()
    
    try:
        console.print(f"[cyan]Initializing database: {db_url}[/cyan]")
        db = initialize_database(db_url)
        console.print("[bold green]✅ Database initialized successfully![/bold green]")
        
        # Show initial stats
        show_database_stats()
        
    except Exception as e:
        console.print(f"[bold red]❌ Error initializing database: {e}[/bold red]")
        sys.exit(1)

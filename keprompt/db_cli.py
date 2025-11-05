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


def list_recent_conversations(limit: int = 20) -> None:
    """List recent chats."""
    chat_manager = ChatManager()

    try:
        chats = chat_manager.list_chats(limit=limit)

        if not chats:
            console.print("[yellow]No chats found.[/yellow]")
            return

        # Create chats table
        table = Table(title=f"Recent Chats (Last {len(chats)})")
        table.add_column("Chat ID", style="cyan", no_wrap=True)
        table.add_column("Prompt Name", style="green")
        table.add_column("Prompt Version", style="magenta")
        table.add_column("Created", style="blue")
        table.add_column("Total Cost", style="yellow", justify="right")

        for conv in chats:
            # Handle created_timestamp which comes as ISO string from manager
            created_timestamp = conv['created_timestamp']
            if isinstance(created_timestamp, str):
                # Parse ISO format string back to datetime for formatting
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(created_timestamp.replace('Z', '+00:00'))
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    created_str = created_timestamp  # Use as-is if parsing fails
            else:
                # If it's already a datetime object
                created_str = created_timestamp.strftime("%Y-%m-%d %H:%M")

            prompt_name = conv['prompt_name'] or "Unknown"
            prompt_version = conv['prompt_version'] or "Unknown"
            cost_display = f"${conv['total_cost']:.6f}" if conv['total_cost'] else "$0.000000"

            table.add_row(
                conv['chat_id'],
                prompt_name,
                prompt_version,
                created_str,
                cost_display
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]❌ Error listing chats: {e}[/bold red]")
        sys.exit(1)


def view_conversation_summary(chat_id: str) -> None:
    """View chat summary."""
    chat_manager = ChatManager()

    try:
        data = chat_manager.get_chat(chat_id)

        if not data:
            console.print(f"[bold red]❌ Chat not found: {chat_id}[/bold red]")
            sys.exit(1)

        chat = data['chat']
        costs = data['costs']

        # Summary table
        table = Table(title=f"Chat Summary: {chat_id}")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("Chat ID", chat.chat_id)
        table.add_row("Created", chat.created_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Prompt", chat.prompt_name or "Unknown")
        table.add_row("Version", chat.prompt_version or "Unknown")
        table.add_row("Filename", chat.prompt_filename or "Unknown")
        table.add_row("Total Cost", f"${float(chat.total_cost):.6f}")
        table.add_row("API Calls", str(chat.total_api_calls))
        table.add_row("Tokens In", str(chat.total_tokens_in))
        table.add_row("Tokens Out", str(chat.total_tokens_out))
        table.add_row("Messages", str(len(data['messages'])))

        console.print(table)

        # Cost breakdown
        if costs:
            console.print("\n[bold cyan]Cost Breakdown:[/bold cyan]")
            cost_table = Table()
            cost_table.add_column("Msg#", style="blue", justify="right")
            cost_table.add_column("Call ID", style="cyan")
            cost_table.add_column("Model", style="green")
            cost_table.add_column("Tokens In", style="yellow", justify="right")
            cost_table.add_column("Tokens Out", style="yellow", justify="right")
            cost_table.add_column("Cost", style="red", justify="right")
            cost_table.add_column("Time", style="magenta", justify="right")

            for cost in costs:
                cost_table.add_row(
                    str(cost.msg_no),
                    cost.call_id,
                    cost.model,
                    str(cost.tokens_in),
                    str(cost.tokens_out),
                    f"${float(cost.estimated_costs):.6f}",
                    f"{float(cost.elapsed_time):.2f}s"
                )

            console.print(cost_table)

    except Exception as e:
        console.print(f"[bold red]❌ Error viewing chat: {e}[/bold red]")
        sys.exit(1)


def delete_conversation(chat_id: str) -> None:
    """Delete a specific chat."""
    chat_manager = ChatManager()

    try:
        success = chat_manager.delete_chat(chat_id)

        if success:
            console.print(f"[bold green]✅ Chat deleted: {chat_id}[/bold green]")
        else:
            console.print(f"[bold red]❌ Chat not found: {chat_id}[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]❌ Error deleting chat: {e}[/bold red]")
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

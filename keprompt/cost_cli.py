"""
CLI commands for cost tracking and reporting.

This module provides command-line utilities for viewing and analyzing
cost tracking data stored in the SQLite database.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table


def get_costs_db_path() -> Path:
    """Get the path to the costs database."""
    return Path("prompts/chats.db")


def check_database_exists() -> bool:
    """Check if the costs database exists."""
    return get_costs_db_path().exists()


def get_recent_costs(limit: int = 10) -> list:
    """Get recent cost entries from the database."""
    db_path = get_costs_db_path()
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT COALESCE(prompt_semantic_name, 'unknown') as prompt_name, 
               model, provider, tokens_in, tokens_out,
               estimated_costs, timestamp, 'unknown' as project
        FROM cost_tracking 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def get_cost_summary(days: int = 7) -> dict:
    """Get cost summary for the specified number of days."""
    db_path = get_costs_db_path()
    if not db_path.exists():
        return {}
    
    # Calculate date threshold
    threshold = datetime.now() - timedelta(days=days)
    threshold_str = threshold.isoformat()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_calls,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(estimated_costs) as total_cost,
            COUNT(DISTINCT COALESCE(prompt_semantic_name, 'unknown')) as unique_prompts,
            COUNT(DISTINCT model) as unique_models
        FROM cost_tracking 
        WHERE timestamp >= ?
    """, (threshold_str,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        return {
            "total_calls": row[0],
            "total_tokens_in": row[1] or 0,
            "total_tokens_out": row[2] or 0,
            "total_cost": row[3] or 0.0,
            "unique_prompts": row[4] or 0,
            "unique_models": row[5] or 0,
            "days": days
        }
    
    return {"days": days, "total_calls": 0}


def get_costs_by_prompt(days: int = 7) -> list:
    """Get cost breakdown by prompt for the specified number of days."""
    db_path = get_costs_db_path()
    if not db_path.exists():
        return []
    
    threshold = datetime.now() - timedelta(days=days)
    threshold_str = threshold.isoformat()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT 
            COALESCE(prompt_semantic_name, 'unknown') as display_name,
            COUNT(*) as call_count,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(estimated_costs) as total_cost,
            AVG(estimated_costs) as avg_cost
        FROM cost_tracking 
        WHERE timestamp >= ?
        GROUP BY display_name
        ORDER BY total_cost DESC
    """, (threshold_str,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def get_costs_by_model(days: int = 7) -> list:
    """Get cost breakdown by model for the specified number of days."""
    db_path = get_costs_db_path()
    if not db_path.exists():
        return []
    
    threshold = datetime.now() - timedelta(days=days)
    threshold_str = threshold.isoformat()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT 
            model,
            provider,
            COUNT(*) as call_count,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(estimated_costs) as total_cost,
            AVG(estimated_costs) as avg_cost
        FROM cost_tracking 
        WHERE timestamp >= ?
        GROUP BY model, provider
        ORDER BY total_cost DESC
    """, (threshold_str,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def print_recent_costs(limit: int = 10):
    """Print recent cost entries in a formatted table."""
    console = Console()
    
    if not check_database_exists():
        console.print("[red]No cost tracking database found at prompts/chats.db[/red]")
        console.print("Run a prompt to start tracking costs.")
        return
    
    # Updated query to use semantic name and include version
    db_path = get_costs_db_path()
    conn = sqlite3.connect(str(db_path))
    
    query = """
    SELECT 
        'unknown' as project,
        COALESCE(prompt_semantic_name, 'unknown') as display_name,
        COALESCE(prompt_version_tracking, 'unknown') as prompt_version,
        provider,
        model,
        tokens_in,
        tokens_out,
        estimated_costs,
        strftime('%m-%d %H:%M', timestamp) as time
    FROM cost_tracking 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    cursor = conn.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        console.print("[yellow]No cost entries found.[/yellow]")
        return
    
    # Create table with updated column order: Project, Prompt, Version, Provider, Model, TokIn, TokOut, Cost, Time
    table = Table(title="Recent Cost Entries")
    table.add_column("Project", style="cyan", no_wrap=True)
    table.add_column("Prompt", style="green", no_wrap=True)
    table.add_column("Version", style="blue", no_wrap=True)
    table.add_column("Provider", style="magenta", no_wrap=True)
    table.add_column("Model", style="yellow", no_wrap=True)
    table.add_column("TokIn", style="cyan", justify="right")
    table.add_column("TokOut", style="cyan", justify="right")
    table.add_column("Cost", style="red", justify="right")
    table.add_column("Time", style="dim", no_wrap=True)
    
    for row in rows:
        project, display_name, version, provider, model, tokens_in, tokens_out, cost, time = row
        table.add_row(
            project or "unknown",
            display_name or "unknown",
            version or "unknown",
            provider,
            model,
            str(tokens_in),
            str(tokens_out),
            f"${cost:.6f}",
            time
        )
    
    console.print(table)


def print_cost_summary(days: int = 7):
    """Print cost summary for the specified number of days."""
    console = Console()
    
    if not check_database_exists():
        console.print("[red]No cost tracking database found at prompts/chats.db[/red]")
        return
    
    summary = get_cost_summary(days)
    
    if summary.get("total_calls", 0) == 0:
        console.print(f"[yellow]No cost data found for the last {days} days[/yellow]")
        return
    
    table = Table(title=f"Cost Summary - Last {days} Days")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total API Calls", str(summary["total_calls"]))
    table.add_row("Total Input Tokens", f"{summary['total_tokens_in']:,}")
    table.add_row("Total Output Tokens", f"{summary['total_tokens_out']:,}")
    table.add_row("Total Cost", f"${summary['total_cost']:.6f}")
    table.add_row("Unique Prompts", str(summary["unique_prompts"]))
    table.add_row("Unique Models", str(summary["unique_models"]))
    
    if summary["total_calls"] > 0:
        avg_cost = summary["total_cost"] / summary["total_calls"]
        table.add_row("Average Cost per Call", f"${avg_cost:.6f}")
    
    console.print(table)


def print_costs_by_prompt(days: int = 7):
    """Print cost breakdown by prompt."""
    console = Console()
    
    if not check_database_exists():
        console.print("[red]No cost tracking database found at prompts/chats.db[/red]")
        return
    
    costs = get_costs_by_prompt(days)
    
    if not costs:
        console.print(f"[yellow]No cost data found for the last {days} days[/yellow]")
        return
    
    table = Table(title=f"Costs by Prompt - Last {days} Days")
    table.add_column("Prompt", style="cyan")
    table.add_column("Calls", justify="right", style="blue")
    table.add_column("Tokens In", justify="right", style="yellow")
    table.add_column("Tokens Out", justify="right", style="yellow")
    table.add_column("Total Cost", justify="right", style="red")
    table.add_column("Avg Cost", justify="right", style="green")
    
    for row in costs:
        prompt_name, call_count, tokens_in, tokens_out, total_cost, avg_cost = row
        table.add_row(
            prompt_name,
            str(call_count),
            f"{tokens_in:,}" if tokens_in else "0",
            f"{tokens_out:,}" if tokens_out else "0",
            f"${total_cost:.6f}" if total_cost else "$0.000000",
            f"${avg_cost:.6f}" if avg_cost else "$0.000000"
        )
    
    console.print(table)


def print_costs_for_prompt(prompt_name: str, days: int = 30):
    """Print cost details for a specific prompt."""
    console = Console()
    
    if not check_database_exists():
        console.print("[red]No cost tracking database found at prompts/chats.db[/red]")
        return
    
    db_path = get_costs_db_path()
    conn = sqlite3.connect(str(db_path))
    
    # Calculate date threshold
    threshold = datetime.now() - timedelta(days=days)
    threshold_str = threshold.isoformat()
    
    # Query for specific prompt using semantic name or filename
    query = """
    SELECT 
        COALESCE(prompt_semantic_name, prompt_name) as display_name, 
        prompt_version,
        provider,
        model,
        tokens_in,
        tokens_out,
        estimated_costs,
        strftime('%m-%d %H:%M', timestamp) as time,
        chat_id
    FROM cost_tracking 
    WHERE (COALESCE(prompt_semantic_name, prompt_name) LIKE ? OR prompt_name LIKE ?)
      AND timestamp >= ?
    ORDER BY timestamp DESC
    """
    
    cursor = conn.execute(query, (f"%{prompt_name}%", f"%{prompt_name}%", threshold_str))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        console.print(f"[yellow]No cost data found for prompt '{prompt_name}' in the last {days} days[/yellow]")
        console.print("Try using a partial name or check available prompts with: python -m keprompt.cost_cli by-prompt")
        return
    
    # Calculate totals
    total_calls = len(rows)
    total_tokens_in = sum(row[4] for row in rows if row[4])
    total_tokens_out = sum(row[5] for row in rows if row[5])
    total_cost = sum(row[6] for row in rows if row[6])
    
    # Create summary table
    summary_table = Table(title=f"Cost Summary for '{prompt_name}' - Last {days} Days")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Calls", str(total_calls))
    summary_table.add_row("Total Input Tokens", f"{total_tokens_in:,}")
    summary_table.add_row("Total Output Tokens", f"{total_tokens_out:,}")
    summary_table.add_row("Total Cost", f"${total_cost:.6f}")
    if total_calls > 0:
        summary_table.add_row("Average Cost per Call", f"${total_cost/total_calls:.6f}")
    
    console.print(summary_table)
    console.print()
    
    # Create detailed table
    detail_table = Table(title="Detailed Cost Entries")
    detail_table.add_column("Prompt", style="green", no_wrap=True)
    detail_table.add_column("Version", style="blue", no_wrap=True)
    detail_table.add_column("Provider", style="magenta", no_wrap=True)
    detail_table.add_column("Model", style="yellow", no_wrap=True)
    detail_table.add_column("TokIn", style="cyan", justify="right")
    detail_table.add_column("TokOut", style="cyan", justify="right")
    detail_table.add_column("Cost", style="red", justify="right")
    detail_table.add_column("Time", style="dim", no_wrap=True)
    
    for row in rows:
        display_name, version, provider, model, tokens_in, tokens_out, cost, time, chat_id = row
        detail_table.add_row(
            display_name or "unknown",
            version or "unknown",
            provider,
            model,
            str(tokens_in) if tokens_in else "0",
            str(tokens_out) if tokens_out else "0",
            f"${cost:.6f}" if cost else "$0.000000",
            time
        )
    
    console.print(detail_table)


def print_costs_by_model(days: int = 7):
    """Print cost breakdown by model."""
    console = Console()
    
    if not check_database_exists():
        console.print("[red]No cost tracking database found at prompts/chats.db[/red]")
        return
    
    costs = get_costs_by_model(days)
    
    if not costs:
        console.print(f"[yellow]No cost data found for the last {days} days[/yellow]")
        return
    
    table = Table(title=f"Costs by Model - Last {days} Days")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="blue")
    table.add_column("Calls", justify="right", style="blue")
    table.add_column("Tokens In", justify="right", style="yellow")
    table.add_column("Tokens Out", justify="right", style="yellow")
    table.add_column("Total Cost", justify="right", style="red")
    table.add_column("Avg Cost", justify="right", style="green")
    
    for row in costs:
        model, provider, call_count, tokens_in, tokens_out, total_cost, avg_cost = row
        table.add_row(
            model,
            provider,
            str(call_count),
            f"{tokens_in:,}" if tokens_in else "0",
            f"{tokens_out:,}" if tokens_out else "0",
            f"${total_cost:.6f}" if total_cost else "$0.000000",
            f"${avg_cost:.6f}" if avg_cost else "$0.000000"
        )
    
    console.print(table)


def export_costs_csv(filename: str, days: int = 30):
    """Export cost data to CSV file."""
    import csv
    
    db_path = get_costs_db_path()
    if not db_path.exists():
        print("No cost tracking database found at prompts/chats.db", file=sys.stderr)
        return False
    
    threshold = datetime.now() - timedelta(days=days)
    threshold_str = threshold.isoformat()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT prompt_name, version, timestamp, tokens_in, tokens_out, estimated_costs,
               model, provider, cost_in, cost_out, chat_id, call_id,
               project, parameters, success, error_message,
               context_length, temperature, max_tokens,
               hostname, environment, git_commit, execution_mode
        FROM cost_tracking 
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
    """, (threshold_str,))
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'prompt_name', 'version', 'timestamp', 'tokens_in', 'tokens_out', 'estimated_costs',
            'model', 'provider', 'cost_in', 'cost_out', 'chat_id', 'call_id',
            'project', 'parameters', 'success', 'error_message',
            'context_length', 'temperature', 'max_tokens',
            'hostname', 'environment', 'git_commit', 'execution_mode'
        ])
        
        # Write data
        for row in cursor:
            writer.writerow(row)
    
    conn.close()
    print(f"Cost data exported to {filename}")
    return True


def main():
    """Main CLI entry point for cost tracking commands."""
    parser = argparse.ArgumentParser(description="KePrompt Cost Tracking CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Recent costs command
    recent_parser = subparsers.add_parser('recent', help='Show recent cost entries')
    recent_parser.add_argument('--limit', type=int, default=10, help='Number of entries to show (default: 10)')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show cost summary')
    summary_parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    
    # By prompt command
    prompt_parser = subparsers.add_parser('by-prompt', help='Show costs by prompt')
    prompt_parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    
    # By model command
    model_parser = subparsers.add_parser('by-model', help='Show costs by model')
    model_parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    
    # Prompt command - show costs for specific prompt
    prompt_detail_parser = subparsers.add_parser('prompt', help='Show costs for a specific prompt')
    prompt_detail_parser.add_argument('name', help='Prompt name (supports partial matching)')
    prompt_detail_parser.add_argument('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export cost data to CSV')
    export_parser.add_argument('filename', help='Output CSV filename')
    export_parser.add_argument('--days', type=int, default=30, help='Number of days to export (default: 30)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'recent':
        print_recent_costs(args.limit)
    elif args.command == 'summary':
        print_cost_summary(args.days)
    elif args.command == 'by-prompt':
        print_costs_by_prompt(args.days)
    elif args.command == 'by-model':
        print_costs_by_model(args.days)
    elif args.command == 'prompt':
        print_costs_for_prompt(args.name, args.days)
    elif args.command == 'export':
        export_costs_csv(args.filename, args.days)


if __name__ == '__main__':
    main()

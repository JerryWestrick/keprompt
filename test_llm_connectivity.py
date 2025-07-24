#!/usr/bin/env python3
"""
Simple test program to check if all defined LLMs are callable.
Tests each model with a simple "Hi!" prompt and reports success/failure.
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich import box

def get_all_models():
    """Get all available models from keprompt."""
    try:
        # Import keprompt modules to get model list
        sys.path.insert(0, str(Path(__file__).parent))
        from keprompt.AiRegistry import AiRegistry
        
        models = []
        for model_name in sorted(AiRegistry.models.keys()):
            model = AiRegistry.get_model(model_name)
            models.append({
                'name': model_name,
                'company': model.company,
                'description': model.description
            })
        return models
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def extract_error_message(output):
    """Extract meaningful error message from keprompt output."""
    lines = output.split('\n')
    
    # Look for "Error executing statement above :" pattern
    for i, line in enumerate(lines):
        if "Error executing statement above :" in line:
            # Get the error message after the colon
            error_start = line.find("Error executing statement above :") + len("Error executing statement above :")
            error_msg = line[error_start:].strip()
            
            # If the error continues on next lines, capture them too
            full_error = error_msg
            for j in range(i + 1, min(i + 10, len(lines))):  # Look at next few lines
                next_line = lines[j].strip()
                if not next_line or next_line.startswith('│') or next_line.startswith('╰'):
                    break
                full_error += " " + next_line
            
            return full_error
    
    # Look for API error patterns
    for line in lines:
        if "API error:" in line:
            return line.split("API error:")[-1].strip()
        elif "Error:" in line and not line.startswith('│'):
            return line.split("Error:")[-1].strip()
    
    # Look for other error indicators
    error_indicators = ["error", "failed", "exception", "invalid"]
    for line in lines:
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in error_indicators):
            if not line.startswith('│') and len(line.strip()) > 10:
                return line.strip()
    
    return None

def test_model_connectivity(model_name):
    """Test if a model is callable with a simple Hi prompt."""
    try:
        # Run from the keprompt root directory
        keprompt_root = Path(__file__).parent
        test_dir = keprompt_root / "test"
        
        # Set PYTHONPATH to include keprompt directory
        env = os.environ.copy()
        env['PYTHONPATH'] = str(keprompt_root) + ':' + env.get('PYTHONPATH', '')
        
        cmd = [
            sys.executable, "-m", "keprompt", 
            "-e", "hi", 
            "--param", "llm", model_name,
            "--no-log"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        # Check for success - return code 0 and no error messages in output
        stdout_output = result.stdout.strip()
        stderr_output = result.stderr.strip()
        
        # Extract error message from stdout (where keprompt writes errors)
        error_message = extract_error_message(stdout_output)
        
        # Also check stderr for system-level errors
        if not error_message and stderr_output:
            error_message = stderr_output
        
        # Determine success based on return code and presence of error messages
        success = (result.returncode == 0 and 
                  error_message is None and
                  len(stdout_output) > 0)
        
        return {
            'model': model_name,
            'success': success,
            'error': error_message,
            'returncode': result.returncode,
            'stdout': stdout_output[:200] + "..." if len(stdout_output) > 200 else stdout_output  # Keep first 200 chars for debugging
        }
        
    except subprocess.TimeoutExpired:
        return {
            'model': model_name,
            'success': False,
            'error': 'Timeout after 60 seconds',
            'returncode': -1,
            'stdout': ''
        }
    except Exception as e:
        return {
            'model': model_name,
            'success': False,
            'error': str(e),
            'returncode': -1,
            'stdout': ''
        }

def test_company_models(company_name, company_models, progress, task_id):
    """Test all models for a specific company in a separate thread."""
    company_results = []
    
    for model_info in company_models:
        model_name = model_info['name']
        
        # Update progress description for this company
        progress.update(task_id, description=f"Testing {company_name}::{model_name}")
        
        # Test the model
        result = test_model_connectivity(model_name)
        result['company'] = company_name
        result['description'] = model_info['description']
        company_results.append(result)
        
        # Advance progress for this company
        progress.advance(task_id)
    
    return company_results

def create_summary_table(results):
    """Create a rich table showing summary by company."""
    table = Table(title="LLM Connectivity Test Results", box=box.ROUNDED)
    table.add_column("Company", style="cyan", no_wrap=True)
    table.add_column("Total", justify="center")
    table.add_column("Success", justify="center", style="green")
    table.add_column("Failed", justify="center", style="red")
    table.add_column("Success Rate", justify="center")
    
    # Group by company
    by_company = {}
    for result in results:
        company = result['company']
        if company not in by_company:
            by_company[company] = {'total': 0, 'success': 0, 'failed': 0}
        by_company[company]['total'] += 1
        if result['success']:
            by_company[company]['success'] += 1
        else:
            by_company[company]['failed'] += 1
    
    # Add rows to table
    for company in sorted(by_company.keys()):
        stats = by_company[company]
        success_rate = (stats['success'] / stats['total']) * 100
        table.add_row(
            company,
            str(stats['total']),
            str(stats['success']),
            str(stats['failed']),
            f"{success_rate:.1f}%"
        )
    
    return table

def create_detailed_table(results):
    """Create a detailed table showing all model results."""
    console = Console()
    terminal_width = console.size.width
    
    table = Table(title="Detailed Results", box=box.SIMPLE, width=terminal_width)
    table.add_column("Company", style="cyan", width=12)
    table.add_column("Model", style="yellow", width=25)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Error", style="red", no_wrap=False)  # Allow wrapping and use remaining width
    
    for result in results:
        status = "[green]✓ SUCCESS[/green]" if result['success'] else "[red]✗ FAILED[/red]"
        error = result['error'] or ""
        
        table.add_row(
            result['company'],
            result['model'],
            status,
            error
        )
    
    return table

def main():
    """Main function to test all LLM connectivity."""
    console = Console()
    
    # Header
    console.print(Panel.fit(
        "[bold blue]LLM Connectivity Test (Multithreaded)[/bold blue]\n"
        "Testing if all defined LLMs are callable with a simple 'Hi!' prompt\n"
        "[dim]Running one thread per company for parallel testing[/dim]",
        border_style="blue"
    ))
    
    models = get_all_models()
    
    if not models:
        console.print("[red]No models found![/red]")
        return
    
    # For testing, limit to first few models if --test flag is used
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    if test_mode:
        console.print("[yellow]Running in test mode - testing first 3 models only[/yellow]")
        models = models[:3]
    
    # Group models by company
    by_company = {}
    for model_info in models:
        company = model_info['company']
        if company not in by_company:
            by_company[company] = []
        by_company[company].append(model_info)
    
    console.print(f"\n[bold]Found {len(models)} models across {len(by_company)} companies to test[/bold]")
    for company, company_models in by_company.items():
        console.print(f"  • {company}: {len(company_models)} models")
    console.print()
    
    results = []
    
    # Test models by company with multithreading
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        # Create progress tasks for each company
        company_tasks = {}
        for company, company_models in by_company.items():
            task_id = progress.add_task(f"Testing {company}...", total=len(company_models))
            company_tasks[company] = task_id
        
        # Use ThreadPoolExecutor to run companies in parallel
        with ThreadPoolExecutor(max_workers=len(by_company)) as executor:
            # Submit all company testing tasks
            future_to_company = {
                executor.submit(test_company_models, company, company_models, progress, company_tasks[company]): company
                for company, company_models in by_company.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    company_results = future.result()
                    results.extend(company_results)
                except Exception as exc:
                    console.print(f"[red]Company {company} generated an exception: {exc}[/red]")
                    # Add failed results for this company's models
                    for model_info in by_company[company]:
                        results.append({
                            'model': model_info['name'],
                            'company': company,
                            'description': model_info['description'],
                            'success': False,
                            'error': f"Thread exception: {exc}",
                            'returncode': -1,
                            'stdout': ''
                        })
    
    # Calculate summary stats
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    success_rate = (successful / len(results)) * 100
    
    # Display summary panel
    summary_text = f"""[bold]Total models tested:[/bold] {len(results)}
[bold green]Successful:[/bold green] {successful}
[bold red]Failed:[/bold red] {failed}
[bold]Success rate:[/bold] {success_rate:.1f}%"""
    
    console.print("\n")
    console.print(Panel(summary_text, title="Summary", border_style="green" if failed == 0 else "yellow"))
    
    # Display summary table
    console.print("\n")
    console.print(create_summary_table(results))
    
    # Display detailed results if there are failures
    if failed > 0:
        console.print("\n")
        console.print(create_detailed_table(results))
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"llm_connectivity_test_{timestamp}.txt"
    
    with open(results_file, 'w') as f:
        f.write(f"LLM Connectivity Test Results\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*50}\n\n")
        
        f.write(f"Summary:\n")
        f.write(f"  Total models: {len(results)}\n")
        f.write(f"  Successful: {successful}\n")
        f.write(f"  Failed: {failed}\n")
        f.write(f"  Success rate: {success_rate:.1f}%\n\n")
        
        f.write(f"Results by Company:\n")
        f.write(f"{'-'*50}\n")
        
        # Group by company
        by_company = {}
        for result in results:
            company = result['company']
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(result)
        
        for company in sorted(by_company.keys()):
            f.write(f"\n{company}:\n")
            for result in by_company[company]:
                status = "✓" if result['success'] else "✗"
                f.write(f"  {status} {result['model']}\n")
                if not result['success'] and result['error']:
                    f.write(f"    Error: {result['error']}\n")
    
    console.print(f"\n[dim]Detailed results saved to: {results_file}[/dim]")

if __name__ == "__main__":
    main()

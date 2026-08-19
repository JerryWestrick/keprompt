"""
Model updater for keprompt - handles updating model definitions from LiteLLM or resetting to defaults
"""
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests


console = Console(stderr=True)

def update_models(target: str = None, api_key: str = None) -> None:
    """
    Update models by downloading LiteLLM's model database.
    
    The target parameter is deprecated and ignored. This function now:
    - Downloads https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
    - Backs up existing file if present
    - Saves to prompts/functions/model_prices_and_context_window.json
    
    Args:
        target: (DEPRECATED) Previously used to specify provider. Now ignored.
        api_key: (DEPRECATED) Previously used for OpenRouter API. Now ignored.
    """
    
    # Show deprecation warning if target/provider was specified
    if target and target.lower() not in ["", "all"]:
        console.print(f"[yellow]Warning: --provider flag is deprecated and ignored.[/yellow]")
        console.print("[yellow]Model updates now use the centralized LiteLLM database.[/yellow]")
    
    # Download and save the LiteLLM model database
    download_litellm_model_database()

def reset_to_defaults() -> None:
    """
    DEPRECATED: Individual provider JSON files are no longer used.
    Use 'keprompt models update' to download the centralized model database instead.
    """
    console.print("[yellow]Warning: reset_to_defaults is deprecated.[/yellow]")
    console.print("[yellow]Individual provider JSON files are no longer used.[/yellow]")
    console.print("[cyan]Use 'keprompt models update' to download the centralized model database.[/cyan]")

def download_litellm_model_database() -> None:
    """
    Download LiteLLM model database and save to prompts/functions.
    
    This function:
    - Downloads from GitHub (https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json)
    - Creates backup of existing file if present
    - Saves to prompts/functions/model_prices_and_context_window.json
    
    Raises:
        Exception: If download fails, with user-friendly error message
    """
    backup_path = Path("prompts/functions/model_prices_and_context_window.json.backup")
    target_path = Path("prompts/functions/model_prices_and_context_window.json")
    
    # Ensure prompts/functions directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    console.print("[cyan]Downloading LiteLLM model database from GitHub...[/cyan]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            
            url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Backup existing file if present
            if target_path.is_file():
                shutil.copy2(target_path, backup_path)
                console.print(f"[dim]Created backup: {backup_path}[/dim]")
            
            # Write to prompts/functions
            with open(target_path, 'w') as tf:
                json.dump(data, tf, indent=2)
            
            progress.update(task, completed=True)
            console.print(f"[green]✓ Successfully downloaded {len(data)} models from LiteLLM[/green]")
            console.print(f"[green]✓ Saved to: {target_path}[/green]")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download model database: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse model database JSON: {str(e)}")
    except IOError as e:
        raise Exception(f"Failed to save model database to file: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error downloading model database: {str(e)}")

# Legacy functions kept for backward compatibility but deprecated
# These are no longer used since we now use the centralized model database


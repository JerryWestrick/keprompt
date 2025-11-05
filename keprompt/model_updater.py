"""
Model updater for keprompt - handles updating model definitions from LiteLLM or resetting to defaults
"""
import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests

from .ModelManager import ModelManager, AiModel

console = Console()

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

def update_all_from_litellm() -> None:
    """
    DEPRECATED: Individual provider updates are no longer supported.
    Use update_models() to download the centralized model database instead.
    """
    console.print("[yellow]Warning: Individual provider updates are deprecated.[/yellow]")
    console.print("[cyan]Use 'keprompt models update' to download the centralized model database.[/cyan]")
    download_litellm_model_database()

def update_provider_from_litellm(provider_name: str) -> None:
    """
    DEPRECATED: Individual provider updates are no longer supported.
    Use update_models() to download the centralized model database instead.
    """
    console.print(f"[yellow]Warning: Updating individual provider '{provider_name}' is deprecated.[/yellow]")
    console.print("[yellow]Individual provider JSON files are no longer used.[/yellow]")
    console.print("[cyan]Downloading centralized model database instead...[/cyan]")
    download_litellm_model_database()

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

def get_supported_providers() -> List[str]:
    """
    DEPRECATED: Individual provider JSON files are no longer used.
    Returns empty list for backward compatibility.
    """
    return []

def update_provider_from_data(provider_name: str, litellm_data: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Individual provider updates are no longer supported.
    Returns False for backward compatibility.
    """
    console.print(f"[yellow]Warning: update_provider_from_data is deprecated.[/yellow]")
    return False

def filter_models_for_provider(provider_name: str, litellm_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    DEPRECATED: Individual provider filtering is no longer needed.
    Returns empty dict for backward compatibility.
    """
    return {}

def update_openrouter_from_api(api_key: str = None) -> None:
    """Update OpenRouter models using the provider's native API"""
    if not api_key:
        console.print("[red]Error: API key required for OpenRouter-API update[/red]")
        console.print("[yellow]Usage: update_models('OpenRouter-API', api_key='your-key')[/yellow]")
        return
    
    # Create a mock prompt object to instantiate the provider
    from .AiOpenRouter import AiOpenRouter
    
    class MockPrompt:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.model = "mock"
            self.vm = None
    
    try:
        mock_prompt = MockPrompt(api_key)
        provider = AiOpenRouter(mock_prompt)
        
        # Call the provider's update_models method
        success = provider.update_models()
        
        if success:
            console.print("[green]✓ Successfully updated OpenRouter models from API[/green]")
        else:
            console.print("[red]Failed to update OpenRouter models[/red]")
            
    except Exception as e:
        console.print(f"[red]Error updating OpenRouter from API: {e}[/red]")

def write_provider_json(provider_name: str, models: Dict[str, Any]) -> None:
    """
    DEPRECATED: Individual provider JSON files are no longer used.
    This function does nothing and exists only for backward compatibility.
    """
    console.print(f"[yellow]Warning: write_provider_json is deprecated and does nothing.[/yellow]")
    console.print("[yellow]Individual provider JSON files are no longer used.[/yellow]")

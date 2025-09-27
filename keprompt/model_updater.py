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

from .AiRegistry import AiRegistry, AiModel

console = Console()

def update_models(target: str) -> None:
    """
    Update models based on target:
    - "Reset": Copy all JSONs from keprompt/defaults/models/ to prompts/models/
    - "All": Update all providers from LiteLLM
    - Provider name: Update specific provider from LiteLLM
    """
    
    if target.lower() == "reset":
        reset_to_defaults()
    elif target.lower() == "all":
        update_all_from_litellm()
    else:
        update_provider_from_litellm(target)

def reset_to_defaults() -> None:
    """Reset all model files to bundled defaults"""
    console.print("[cyan]Resetting models to bundled defaults...[/cyan]")
    
    defaults_dir = Path("keprompt/defaults/models")
    prompts_dir = Path("prompts/models")
    
    if not defaults_dir.exists():
        console.print("[red]Error: Defaults directory not found![/red]")
        return
    
    # Ensure prompts/models directory exists
    prompts_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all JSON files from defaults to prompts/models
    copied_files = []
    for json_file in defaults_dir.glob("*.json"):
        if json_file.name != "model_prices_and_context_window.json":  # Skip legacy file
            dest_file = prompts_dir / json_file.name
            shutil.copy2(json_file, dest_file)
            copied_files.append(json_file.name)
    
    console.print(f"[green]✓ Reset complete! Copied {len(copied_files)} provider files:[/green]")
    for filename in sorted(copied_files):
        console.print(f"  - {filename}")

def update_all_from_litellm() -> None:
    """Update all providers from LiteLLM database"""
    console.print("[cyan]Updating all providers from LiteLLM database...[/cyan]")
    
    # Get LiteLLM data
    litellm_data = download_litellm_data()
    if not litellm_data:
        console.print("[red]Failed to download LiteLLM data[/red]")
        return
    
    # Get list of our supported providers
    supported_providers = get_supported_providers()
    
    updated_count = 0
    for provider in supported_providers:
        try:
            if update_provider_from_data(provider, litellm_data):
                updated_count += 1
        except Exception as e:
            console.print(f"[red]Error updating {provider}: {e}[/red]")
    
    console.print(f"[green]✓ Updated {updated_count}/{len(supported_providers)} providers successfully[/green]")

def update_provider_from_litellm(provider_name: str) -> None:
    """Update specific provider from LiteLLM database"""
    console.print(f"[cyan]Updating {provider_name} from LiteLLM database...[/cyan]")
    
    # Validate provider
    supported_providers = get_supported_providers()
    if provider_name not in supported_providers:
        console.print(f"[red]Error: Unknown provider '{provider_name}'[/red]")
        console.print(f"[yellow]Supported providers: {', '.join(supported_providers)}[/yellow]")
        return
    
    # Get LiteLLM data
    litellm_data = download_litellm_data()
    if not litellm_data:
        console.print("[red]Failed to download LiteLLM data[/red]")
        return
    
    # Update the provider
    if update_provider_from_data(provider_name, litellm_data):
        console.print(f"[green]✓ Successfully updated {provider_name}[/green]")
    else:
        console.print(f"[red]Failed to update {provider_name}[/red]")

def download_litellm_data() -> Dict[str, Any]:
    """Download LiteLLM model database with caching"""
    cache_file = Path(tempfile.gettempdir()) / "litellm_models.json"
    
    # Check if cached file exists and is recent (less than 24 hours old)
    if cache_file.exists():
        file_age = cache_file.stat().st_mtime
        import time
        if time.time() - file_age < 24 * 3600:  # 24 hours
            console.print("[dim]Using cached LiteLLM data...[/dim]")
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass  # Fall through to download
    
    # Download fresh data
    console.print("[cyan]Downloading LiteLLM model database...[/cyan]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            
            # LiteLLM model database URL
            url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            progress.update(task, completed=True)
            console.print(f"[green]✓ Downloaded {len(data)} models from LiteLLM[/green]")
            return data
            
    except Exception as e:
        console.print(f"[red]Error downloading LiteLLM data: {e}[/red]")
        return {}

def get_supported_providers() -> List[str]:
    """Get list of providers we support"""
    return ["OpenAI", "Anthropic", "Google", "MistralAI", "DeepSeek", "XAI", "OpenRouter"]

def update_provider_from_data(provider_name: str, litellm_data: Dict[str, Any]) -> bool:
    """Update a specific provider using LiteLLM data"""
    try:
        # Filter models for this provider
        provider_models = filter_models_for_provider(provider_name, litellm_data)
        
        if not provider_models:
            console.print(f"[yellow]No models found for {provider_name} in LiteLLM data[/yellow]")
            return False
        
        # Convert to keprompt format
        converted_models = {}
        for model_name, model_data in provider_models.items():
            try:
                ai_model = AiModel.from_litellm_dict(model_name, model_data)
                converted_models[model_name] = {
                    "provider": provider_name,  # Use our provider name, not LiteLLM's
                    "company": ai_model.company,
                    "model": ai_model.model,
                    "input_cost": ai_model.input_cost,
                    "output_cost": ai_model.output_cost,
                    "max_tokens": ai_model.max_tokens,
                    "cache_cost": ai_model.cache_cost,
                    "max_input_tokens": ai_model.max_input_tokens,
                    "max_output_tokens": ai_model.max_output_tokens,
                    "supports": ai_model.supports,
                    "mode": ai_model.mode,
                    "source": ai_model.source,
                    "description": ai_model.description
                }
            except Exception as e:
                console.print(f"[dim]Skipping {model_name}: {e}[/dim]")
                continue
        
        if not converted_models:
            console.print(f"[yellow]No valid models converted for {provider_name}[/yellow]")
            return False
        
        # Write to JSON file
        write_provider_json(provider_name, converted_models)
        console.print(f"[green]✓ Updated {provider_name} with {len(converted_models)} models[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Error updating {provider_name}: {e}[/red]")
        return False

def filter_models_for_provider(provider_name: str, litellm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter LiteLLM data for a specific provider"""
    filtered = {}
    
    # Provider mapping from our names to LiteLLM provider names
    provider_mapping = {
        "OpenAI": ["openai"],
        "Anthropic": ["anthropic"],
        "Google": ["gemini", "vertex_ai"],
        "MistralAI": ["mistral"],
        "DeepSeek": ["deepseek"],
        "XAI": ["xai"],
        "OpenRouter": ["openrouter"]
    }
    
    litellm_providers = provider_mapping.get(provider_name, [provider_name.lower()])
    
    for model_name, model_data in litellm_data.items():
        litellm_provider = model_data.get("litellm_provider", "").lower()
        
        # Check if this model belongs to our target provider
        if litellm_provider in litellm_providers:
            # Even if the provider matches, check if we need to clean the model name
            if "/" in model_name:
                parts = model_name.split("/", 1)
                if len(parts) == 2:
                    provider_prefix = parts[0].lower()
                    clean_model_name = parts[1]
                    
                    # Clean the name if it has the provider prefix
                    if (provider_name == "MistralAI" and provider_prefix == "mistral") or \
                       (provider_name == "Anthropic" and provider_prefix == "anthropic") or \
                       (provider_name == "Google" and provider_prefix in ["google", "gemini"]) or \
                       (provider_name == "DeepSeek" and provider_prefix == "deepseek") or \
                       (provider_name == "XAI" and provider_prefix == "xai") or \
                       (provider_name == "OpenAI" and provider_prefix == "openai"):
                        filtered[clean_model_name] = model_data
                    else:
                        filtered[model_name] = model_data
                else:
                    filtered[model_name] = model_data
            else:
                filtered[model_name] = model_data
        
        # Handle models with "/" in name - strip provider prefix for clean API names
        elif "/" in model_name:
            # Check if this model should be cleaned for our target provider
            # e.g., "openrouter/openai/gpt-oss-120b" → "openai/gpt-oss-120b" (OpenRouter)
            # e.g., "mistral/mistral-tiny" → "mistral-tiny" (MistralAI)
            parts = model_name.split("/", 1)  # Split on first "/" only
            if len(parts) == 2:
                provider_prefix = parts[0].lower()
                clean_model_name = parts[1]  # Take everything after first "/"
                
                # Check if this model belongs to our target provider based on prefix
                should_include = False
                if provider_name == "OpenRouter":
                    # OpenRouter accepts models from any provider
                    should_include = True
                elif provider_name == "MistralAI" and provider_prefix == "mistral":
                    # MistralAI models: mistral/mistral-tiny → mistral-tiny
                    should_include = True
                elif provider_name == "Anthropic" and provider_prefix == "anthropic":
                    # Anthropic models: anthropic/claude-3 → claude-3
                    should_include = True
                elif provider_name == "Google" and provider_prefix in ["google", "gemini"]:
                    # Google models: google/gemini-pro → gemini-pro
                    should_include = True
                elif provider_name == "DeepSeek" and provider_prefix == "deepseek":
                    # DeepSeek models: deepseek/deepseek-chat → deepseek-chat
                    should_include = True
                elif provider_name == "XAI" and provider_prefix == "xai":
                    # XAI models: xai/grok-beta → grok-beta
                    should_include = True
                elif provider_name == "OpenAI" and provider_prefix == "openai":
                    # OpenAI models: openai/gpt-4 → gpt-4
                    should_include = True
                
                if should_include:
                    # Only add if we don't already have this model (deduplication)
                    # If we do have it, keep the one with better pricing (lower input cost)
                    if clean_model_name not in filtered:
                        model_data_copy = model_data.copy()
                        filtered[clean_model_name] = model_data_copy
                    else:
                        # Compare pricing and keep the better one
                        existing_input_cost = filtered[clean_model_name].get("input_cost_per_token", float('inf'))
                        new_input_cost = model_data.get("input_cost_per_token", float('inf'))
                        
                        if new_input_cost < existing_input_cost:
                            # New model has better pricing, replace it
                            model_data_copy = model_data.copy()
                            filtered[clean_model_name] = model_data_copy
    
    return filtered

def write_provider_json(provider_name: str, models: Dict[str, Any]) -> None:
    """Write provider models to JSON file"""
    from datetime import datetime
    
    prompts_dir = Path("prompts/models")
    prompts_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = prompts_dir / f"{provider_name}.json"
    
    data = {
        "metadata": {
            "provider": provider_name,
            "last_updated": datetime.now().isoformat(),
            "total_models": len(models),
            "source": "LiteLLM"
        },
        "models": models
    }
    
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)

import argparse
import json
import traceback
from datetime import datetime
from typing import Type, List

from rich.table import Table

from . import CustomEncoder
from .AiProvider import AiProvider
from dataclasses import dataclass, field, asdict
from typing import Dict, Any
from pathlib import Path



@dataclass
class AiModel:
    # Core identification (required fields)
    provider: str           # API service (OpenAI, Anthropic, XAI, OpenRouter)
    company: str           # Model creator (OpenAI, Anthropic, XAI, etc.)
    model: str             # full model name
    
    # Pricing (required fields)
    input_cost: float      # cost per input token
    output_cost: float     # cost per output token
    
    # Context limits (required fields)
    max_tokens: int        # maximum context window
    
    # Optional fields with defaults
    cache_cost: float = 0.0  # cost per cached input token
    max_input_tokens: int = 0   # maximum input tokens
    max_output_tokens: int = 0  # maximum output tokens
    
    # Capabilities dictionary
    supports: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    mode: str = "chat"     # model mode (chat, completion, etc.)
    source: str = ""       # documentation link
    description: str = ""  # model description

    def __str__(self) -> str:
        """Return a useful string representation for debugging and logging."""
        return f"AiModel(name='{self.model}', provider='{self.provider}', company='{self.company}', input_cost={self.input_cost}, output_cost={self.output_cost}, max_tokens={self.max_tokens})"

    # def __repr__(self) -> str:
    #     """Return a detailed representation for debugging."""
    #     return (f"AiModel(provider='{self.provider}', company='{self.company}', model='{self.model}', "
    #             f"input_cost={self.input_cost}, output_cost={self.output_cost}, max_tokens={self.max_tokens}, "
    #             f"supports={self.supports}, mode='{self.mode}')")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AiModel':
        # Handle both old and new format during transition
        if 'input' in data:
            # Old format - convert to new format
            supports = {}
            if 'functions' in data:
                supports['function_calling'] = data['functions'].lower() == 'yes'
            
            return cls(
                provider=data.get('provider', ''),
                company=data.get('company', ''),
                model=data.get('model', ''),
                input_cost=data.get('input', 0.0),
                output_cost=data.get('output', 0.0),
                cache_cost=0.0,
                max_tokens=data.get('context', 0),
                max_input_tokens=0,
                max_output_tokens=0,
                supports=supports,
                mode=data.get('mode', 'chat'),
                source=data.get('link', ''),
                description=data.get('description', '')
            )
        else:
            # New format - filter out unknown fields
            valid_fields = {
                'provider', 'company', 'model', 'input_cost', 'output_cost', 
                'max_tokens', 'cache_cost', 'max_input_tokens', 'max_output_tokens',
                'supports', 'mode', 'source', 'description'
            }
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            return cls(**filtered_data)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input_cost) + (output_tokens * self.output_cost)
    
    def get_api_model_name(self) -> str:
        """Extract the bare model name for API calls (strips provider/ prefix)"""
        if '/' in self.model:
            # Return everything after the first slash
            return self.model.split('/', 1)[1]
        return self.model
    
    @classmethod
    def _determine_company(cls, model_name: str, provider: str) -> str:
        """Determine company from model name path"""
        elements = model_name.split('/')
        
        if len(elements) == 3:
            # Format: "provider/company/model" (e.g., "openrouter/anthropic/claude-2")
            if elements[0].lower() == provider.lower():
                return elements[1].title()  # Normalize: "anthropic" → "Anthropic"
            else:
                raise ValueError(f"Unknown provider in model path: expected '{provider}', got '{elements[0]}'")
        else:
            # Format: "model" or "provider/model" (e.g., "gpt-4o-mini" or "xai/grok-code-fast")
            return provider.title()  # Provider = Company
    
    @classmethod
    def from_litellm_dict(cls, model_name: str, data: Dict[str, Any]) -> 'AiModel':
        """Convert LiteLLM format to keprompt AiModel format"""
        provider = data.get("litellm_provider", "")
        company = cls._determine_company(model_name, provider)
        
        # Extract all supports_* fields into dictionary
        supports = {}
        for key, value in data.items():
            if key.startswith("supports_"):
                capability = key[9:]  # Remove "supports_" prefix
                supports[capability] = bool(value)
        
        return cls(
            provider=provider,  # Keep provider name as-is (lowercase) to match registered handlers
            company=company,
            model=f"{model_name}",  # ALWAYS store with provider prefix
            input_cost=data.get("input_cost_per_token", 0.0),
            output_cost=data.get("output_cost_per_token", 0.0),
            cache_cost=data.get("cache_read_input_token_cost", 0.0),
            max_tokens=data.get("max_tokens", 0),
            max_input_tokens=data.get("max_input_tokens", 0),
            max_output_tokens=data.get("max_output_tokens", 0),
            supports=supports,
            mode=data.get("mode", "chat"),
            source=data.get("source", ""),
            description=""  # Can be generated later
        )

    def to_dict(self) -> dict:
        """Convert Prompt to dictionary for JSON serialization."""
        return asdict(self)




class ModelManager:
    handlers: Dict[str, Type['AiProvider']] = {}
    models: Dict[str, AiModel] = {}
    _initialized:bool = False

    def __init__(self, args: argparse.Namespace):
        self.args = args


    @classmethod
    def register_handler(cls, provider_name: str, handler_class: Type['AiProvider']) -> None:
        cls.handlers[provider_name] = handler_class
        # Don't load models during registration - wait until they're needed

    @classmethod
    def _load_all_models(cls) -> None:
        """Load models from LiteLLM database, filtering by registered provider litellm_provider"""
        import os
        import json

        if cls._initialized:
            return

        # Load from LiteLLM database
        package_root = Path(__file__).resolve().parent  # .../keprompt
        project_root = package_root.parent
        litellm_db_path = project_root / "prompts" / "functions" / "model_prices_and_context_window.json"

        if not os.path.exists(litellm_db_path):
            print(f"Warning: LiteLLM database not found at {litellm_db_path}")
            return
        
        try:
            # Build a map of litellm_provider to handler
            providers = []
            for provider_name, handler_class in cls.handlers.items():
                if hasattr(handler_class, 'litellm_provider'):
                    if handler_class.litellm_provider == 'bedrock': continue
                    providers.append(handler_class.litellm_provider)

            with open(litellm_db_path, 'r') as f:
                litellm_data = json.load(f)
            
            # Load models for registered providers only
            model_data = {}
            for model_name, model_info in litellm_data.items():
                litellm_provider = model_info.get("litellm_provider", "")

                # Only load models for registered providers
                if litellm_provider not in providers:
                    continue

                # WOrkaround for missing provider in model name
                if model_name.startswith(litellm_provider):
                    pass
                else:
                    model_name = f"{litellm_provider}/{model_name}"


                # Skip non-chat models (image generation, etc.)
                mode = model_info.get("mode", "chat")
                if mode != "chat":
                    continue
                    
                try:
                    model = AiModel.from_litellm_dict(model_name, model_info)
                    # The model.model field now contains provider/model-name, use it as key
                    model_data[model.model] = model
                except Exception as e:
                    # Skip models that fail to parse
                    pass

            cls.register_models_from_dict(model_data)
            cls._initialized = True
            print(f"Loaded {len(model_data)} models from LiteLLM database")
            
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)[-1]
            source_file = tb.filename
            line_no = tb.lineno
            print(f"Warning: Failed to load models at {source_file}:{line_no} from LiteLLM database: {e}")


    @classmethod
    def create_handler(cls, prompt) -> 'AiProvider':
        """Create and return appropriate AI handler instance for given model"""
        cls._load_all_models()
        model = cls.get_model(prompt.model)
        handler_class = cls.get_handler(model.provider)
        return handler_class(prompt=prompt)

    @classmethod
    def get_handler(cls, provider_name: str) -> Type['AiProvider']:
        handler = cls.handlers.get(provider_name)
        if not handler:
            raise ValueError(f"No handler registered for {provider_name}")
        return handler

    @classmethod
    def register_models_from_dict(cls, model_definitions: Dict[str, Dict[str, Any]]) -> None:
        for name, model in model_definitions.items():
            cls.models[name] = model


    @classmethod
    def get_model(cls, model_name: str) -> AiModel:
        cls._load_all_models()
        if model_name not in cls.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        return cls.models[model_name]


    def execute(self):
        """Execute the command based on the provided arguments"""
        supported_commands = ["get", "update", "reset"]

        if self.args.models_command not in supported_commands:
            return {
                "success": False,
                "data": [f"Unsupported command '{self.args.models_command}' for ModelManager.  Expected one of {supported_commands}"],
                "timestamp": datetime.now().isoformat()
            }
        self._load_all_models()

        if self.args.models_command == "get":
            # self._load_all_models()
            models = []

            name_filter = getattr(self.args, "name", None)
            provider_filter = getattr(self.args, "provider", None)
            company_filter = getattr(self.args, "company", None)

            # Filter models based on patterns
            for name, model in self.models.items():
                if name_filter and name_filter.lower() not in name.lower(): continue
                if provider_filter and provider_filter.lower() != model.provider.lower(): continue
                if company_filter and company_filter.lower() != model.company.lower(): continue

                models.append(model)


            response = self.make_response(models=models)
            return response

        if self.args.models_command == "reset":
            # Reset models to default JSON files
            from .model_updater import reset_to_defaults
            reset_to_defaults()
            return {
                "success": True,
                "data": "Models have been reset to bundled defaults.",
                "timestamp": datetime.now().isoformat()
            }

        if self.args.models_command == "update":
            # Update models by downloading centralized LiteLLM database
            provider_filter = getattr(self.args, "provider", None)
            
            # Call the new centralized update function
            try:
                from .model_updater import update_models
                from rich.panel import Panel
                from rich.text import Text
                
                update_models(target=provider_filter)
                
                # Reload models after update
                self._initialized = False
                self._load_all_models()
                
                message = "Successfully updated model database from LiteLLM"
                if provider_filter:
                    message += f"\n\nNote: --provider '{provider_filter}' flag is deprecated and was ignored"
                
                # Return pretty format if requested
                if getattr(self.args, "pretty", False):
                    from rich.console import Console
                    console = Console()
                    panel = Panel(
                        message,
                        title="[green]✓ Model Update Complete[/green]",
                        border_style="green"
                    )
                    return panel
                
                # Return JSON format
                return {
                    "success": True,
                    "data": message,
                    "timestamp": datetime.now().isoformat()
                }
                    
            except Exception as e:
                # Return error in appropriate format
                if getattr(self.args, "pretty", False):
                    from rich.panel import Panel
                    panel = Panel(
                        str(e),
                        title="[red]✗ Model Update Failed[/red]",
                        border_style="red"
                    )
                    return panel
                
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }


    def make_response(self, models: List[AiModel] = None):
        """Create an Outputable object as response: pretty table if --pretty, else plain text dict."""
        if getattr(self.args, "pretty", False):
            title_parts = []

            name_filter = getattr(self.args, "name", None)
            provider_filter = getattr(self.args, "provider", None)
            company_filter = getattr(self.args, "company", None)

            # Filter models based on patterns
            if name_filter: title_parts.append(f"Name: {name_filter}")
            if provider_filter: title_parts.append(f"Provider: {provider_filter}")
            if company_filter: title_parts.append(f"Company: {company_filter}")

            title = f"Available Models | {' '.join(title_parts)} |"

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

            last_provider = ''
            last_company = ''
            # Sort by Provider, then Company, then model name
            for model in sorted(models, key=lambda x: (x.provider, x.company, x.model)):

                # Show provider and company only when they change
                display_provider = model.provider if model.provider != last_provider else ""
                display_company = model.company if model.company != last_company or model.provider != last_provider else ""

                table.add_row(
                    display_provider,
                    display_company,
                    model.model,
                    str(model.max_tokens),
                    f"{model.input_cost * 1_000_000:06.4f}",
                    f"{model.output_cost * 1_000_000:06.4f}",
                    "Text+Vision" if model.supports.get("vision", False) else "Text",
                    "Text",
                    "Yes" if model.supports.get("function_calling", False) else "No",
                    "2024-04",
                    model.description
                )

                last_provider = model.provider
                last_company = model.company

            return table

        # default: text — ensure JSON-serializable by converting models to dicts
        serializable = [m.to_dict() if hasattr(m, "to_dict") else asdict(m) for m in (models or [])]
        return {"success": True, "data": serializable, "timestamp": datetime.now().isoformat()}

from typing import Type
from .AiProvider import AiProvider
from dataclasses import dataclass, field
from typing import Dict, Any

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

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return (f"AiModel(provider='{self.provider}', company='{self.company}', model='{self.model}', "
                f"input_cost={self.input_cost}, output_cost={self.output_cost}, max_tokens={self.max_tokens}, "
                f"supports={self.supports}, mode='{self.mode}')")

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
            provider=provider.title(),  # Normalize provider name
            company=company,
            model=model_name,
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


class AiRegistry:
    handlers: Dict[str, Type['AiProvider']] = {}
    models: Dict[str, AiModel] = {}
    _initialized: bool = False

    @classmethod
    def register_handler(cls, provider_name: str, handler_class: Type['AiProvider']) -> None:
        cls.handlers[provider_name] = handler_class
        # Auto-load models when handler is registered
        cls._load_models_if_needed()

    @classmethod
    def _load_models_if_needed(cls) -> None:
        """Load models from JSON files if not already loaded"""
        if cls._initialized:
            return
            
        cls._load_all_models()
        cls._initialized = True

    @classmethod
    def _load_all_models(cls) -> None:
        """Load models from all available JSON files"""
        import os
        import json
        
        # Try to load from prompts/models directory first
        models_dir = "prompts/models"
        if not os.path.exists(models_dir):
            # Fallback to defaults if prompts/models doesn't exist
            models_dir = "keprompt/defaults/models"
        
        if not os.path.exists(models_dir):
            print(f"Warning: No models directory found at {models_dir}")
            return
        
        for filename in os.listdir(models_dir):
            if filename.endswith('.json') and filename != 'model_prices_and_context_window.json':
                filepath = os.path.join(models_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        file_data = json.load(f)
                    
                    # Handle nested structure with metadata and models
                    if 'models' in file_data:
                        model_data = file_data['models']
                    else:
                        # Assume flat structure
                        model_data = file_data
                    
                    cls.register_models_from_dict(model_data)
                except Exception as e:
                    print(f"Warning: Failed to load models from {filename}: {e}")

    @classmethod
    def create_handler(cls, prompt) -> 'AiProvider':
        """Create and return appropriate AI handler instance for given model"""
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
        cls.models.update({
            name: AiModel.from_dict(data)
            for name, data in model_definitions.items()
        })

    @classmethod
    def get_model(cls, model_name: str) -> AiModel:
        if model_name not in cls.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        return cls.models[model_name]

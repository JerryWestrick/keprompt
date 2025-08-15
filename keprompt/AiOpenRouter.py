from typing import Dict, List
import json
import requests
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiOpenRouter(AiProvider):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": self.prompt.model,
            "messages": messages,
            "tools": DefinedToolsArray
        }

    def get_api_url(self) -> str:
        return "https://openrouter.ai/api/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.prompt.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/JerryWestrick/keprompt",  # Optional, for rankings
            "X-Title": "KePrompt"  # Optional, shows in rankings on openrouter.ai
        }

    def to_ai_message(self, response: Dict) -> AiMessage:
        choice = response.get("choices", [{}])[0].get("message", {})
        content = []

        if choice.get("content"):
            content.append(AiTextPart(vm=self.prompt.vm, text=choice["content"]))

        for tool_call in choice.get("tool_calls", []):
            content.append(AiCall(vm=self.prompt.vm,name=tool_call["function"]["name"],arguments=tool_call["function"]["arguments"],id=tool_call["id"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        openrouter_messages = []

        for msg in messages:
            content = []
            tool_calls = []
            tool_result_messages = []

            for part in msg.content:
                if   part.type == "text":       content.append({"type": "text", "text": part.text})
                elif part.type == "image_url":  content.append({'type': 'image_url','image_url': {'url': f"data:{part.media_type};base64,{part.file_contents}"}})
                elif part.type == "call":       tool_calls.append({'id': part.id,'type': 'function','function': {'name': part.name,'arguments': json.dumps(part.arguments)}})
                elif part.type == 'result':     tool_result_messages.append({'role': "tool", 'tool_call_id': part.id,'content': part.result})
                else:                           raise ValueError(f"Unknown part type: {part.type}")

            if msg.role == "tool":
                # Add all tool result messages separately
                openrouter_messages.extend(tool_result_messages)
            else:
                message = {"role": msg.role,"content": content[0]["text"] if len(content) == 1 else content}
                if tool_calls:
                    message["tool_calls"] = tool_calls
                openrouter_messages.append(message)

        return openrouter_messages

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for OpenRouter"""
        try:
            # Try to fetch from OpenRouter API
            console.print(f"[yellow]Fetching models from OpenRouter API...[/yellow]")
            api_models = cls._fetch_from_openrouter_api()
            transformed_models = cls._transform_openrouter_models(api_models)
            console.print(f"[green]Successfully fetched {len(transformed_models)} models from API[/green]")
            cls._write_json_file(provider_name, transformed_models)
            
        except Exception as e:
            console.print(f"[yellow]API fetch failed ({e}), using fallback models[/yellow]")
            # Fallback to hardcoded models if API fails
            fallback_models = cls._get_fallback_models()
            cls._write_json_file(provider_name, fallback_models)

    @classmethod
    def _fetch_from_openrouter_api(cls) -> List[Dict]:
        """Fetch models from OpenRouter API"""
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/JerryWestrick/keprompt",
            "X-Title": "KePrompt"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data.get("data", [])

    @classmethod
    def _transform_openrouter_models(cls, api_models: List[Dict]) -> Dict[str, Dict]:
        """Transform OpenRouter API models to our registry format"""
        transformed = {}
        
        for model in api_models:
            model_id = model.get("id", "")
            if not model_id:
                continue
                
            # Extract pricing information
            pricing = model.get("pricing", {})
            input_cost = float(pricing.get("prompt", "0"))
            output_cost = float(pricing.get("completion", "0"))
            
            # Determine modalities
            modality_in = "Text"
            if model.get("architecture", {}).get("modality", "").find("image") != -1:
                modality_in = "Text+Vision"
            
            # Determine function calling support
            functions = "Yes" if model.get("top_provider", {}).get("is_moderated", False) != True else "Yes"
            
            # Extract company from model ID or owned_by
            company = "Unknown"
            if "/" in model_id:
                company = model_id.split("/")[0].title()
            elif "owned_by" in model:
                company = model["owned_by"].title()
            
            # Escape Rich markup in description
            description = model.get("description", f"{model_id} via OpenRouter")
            # Replace [ and ] with escaped versions to prevent Rich markup issues
            description = description.replace("[", "\\[").replace("]", "\\]")
            
            transformed[model_id] = {
                "provider": "OpenRouter",
                "company": company,
                "model": model_id,
                "input": input_cost,
                "output": output_cost,
                "context": model.get("context_length", 0),
                "modality_in": modality_in,
                "modality_out": "Text",
                "functions": functions,
                "description": description,
                "cutoff": "See provider docs"
            }
        
        return transformed

    @classmethod
    def _get_fallback_models(cls) -> Dict[str, Dict]:
        """Get fallback models when API is unavailable"""
        return OpenRouter_Models


# Register handler and models
AiRegistry.register_handler(provider_name="OpenRouter", handler_class=AiOpenRouter)
AiOpenRouter.register_models("OpenRouter")

# OpenRouter model definitions and pricing (used as fallback)
# Official pricing sources:
# - https://openrouter.ai/models
# - https://openrouter.ai/docs#models
# Last updated: January 2025
OpenRouter_Models = {
    # Popular OpenAI models via OpenRouter
    "openai/gpt-4o": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/gpt-4o", 
        "input": 5.0 / 1000000,  # $5.00 / 1M tokens
        "output": 15.0 / 1000000,  # $15.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "OpenAI's GPT-4o via OpenRouter", 
        "cutoff": "2023-10"
    },
    "openai/gpt-4o-mini": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/gpt-4o-mini", 
        "input": 0.15 / 1000000, 
        "output": 0.6 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "OpenAI's GPT-4o-mini via OpenRouter", 
        "cutoff": "2023-10"
    },
    "openai/o1-preview": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/o1-preview", 
        "input": 15.0 / 1000000, 
        "output": 60.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "No", 
        "description": "OpenAI's o1-preview reasoning model via OpenRouter", 
        "cutoff": "2023-10"
    },
    "openai/o1-mini": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/o1-mini", 
        "input": 3.0 / 1000000, 
        "output": 12.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "No", 
        "description": "OpenAI's o1-mini reasoning model via OpenRouter", 
        "cutoff": "2023-10"
    },
    
    "openai/gpt-oss-120b": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/gpt-oss-120b", 
        "input": 3.0 / 1000000, 
        "output": 12.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "No", 
        "description": "OpenAI's gpt-oss-120b via OpenRouter", 
        "cutoff": "2023-10"
    },
    
    "openai/gpt-oss-20b": {
        "provider": "OpenRouter",  # API service
        "company": "OpenAI",       # Model creator
        "model": "openai/gpt-oss-20b", 
        "input": 3.0 / 1000000, 
        "output": 12.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "No", 
        "description": "OpenAI's gpt-oss-20b via OpenRouter", 
        "cutoff": "2023-10"
    },
    
    # Popular Anthropic models via OpenRouter
    "anthropic/claude-3.5-sonnet": {
        "provider": "OpenRouter",  # API service
        "company": "Anthropic",    # Model creator
        "model": "anthropic/claude-3.5-sonnet", 
        "input": 3.0 / 1000000, 
        "output": 15.0 / 1000000, 
        "context": 200000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Anthropic's Claude 3.5 Sonnet via OpenRouter", 
        "cutoff": "2024-04"
    },
    "anthropic/claude-3.5-haiku": {
        "provider": "OpenRouter",  # API service
        "company": "Anthropic",    # Model creator
        "model": "anthropic/claude-3.5-haiku", 
        "input": 1.0 / 1000000, 
        "output": 5.0 / 1000000, 
        "context": 200000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Anthropic's Claude 3.5 Haiku via OpenRouter", 
        "cutoff": "2024-07"
    },
    
    # Popular Google models via OpenRouter
    "google/gemini-pro-1.5": {
        "provider": "OpenRouter",  # API service
        "company": "Google",       # Model creator
        "model": "google/gemini-pro-1.5", 
        "input": 1.25 / 1000000, 
        "output": 5.0 / 1000000, 
        "context": 2000000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Google's Gemini Pro 1.5 via OpenRouter", 
        "cutoff": "2024-04"
    },
    "google/gemini-flash-1.5": {
        "provider": "OpenRouter",  # API service
        "company": "Google",       # Model creator
        "model": "google/gemini-flash-1.5", 
        "input": 0.075 / 1000000, 
        "output": 0.3 / 1000000, 
        "context": 1000000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Google's Gemini Flash 1.5 via OpenRouter", 
        "cutoff": "2024-04"
    },
    
    # Popular open-source models via OpenRouter
    "meta-llama/llama-3.1-405b-instruct": {
        "provider": "OpenRouter",  # API service
        "company": "Meta",         # Model creator
        "model": "meta-llama/llama-3.1-405b-instruct", 
        "input": 3.0 / 1000000, 
        "output": 3.0 / 1000000, 
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Meta's Llama 3.1 405B Instruct via OpenRouter", 
        "cutoff": "2023-12"
    },
    "meta-llama/llama-3.1-70b-instruct": {
        "provider": "OpenRouter",  # API service
        "company": "Meta",         # Model creator
        "model": "meta-llama/llama-3.1-70b-instruct", 
        "input": 0.52 / 1000000, 
        "output": 0.75 / 1000000, 
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Meta's Llama 3.1 70B Instruct via OpenRouter", 
        "cutoff": "2023-12"
    },
    "meta-llama/llama-3.1-8b-instruct": {
        "provider": "OpenRouter",  # API service
        "company": "Meta",         # Model creator
        "model": "meta-llama/llama-3.1-8b-instruct", 
        "input": 0.055 / 1000000, 
        "output": 0.055 / 1000000, 
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Meta's Llama 3.1 8B Instruct via OpenRouter", 
        "cutoff": "2023-12"
    },
    
    # Mistral models via OpenRouter
    "mistralai/mistral-large": {
        "provider": "OpenRouter",  # API service
        "company": "MistralAI",    # Model creator
        "model": "mistralai/mistral-large", 
        "input": 2.0 / 1000000, 
        "output": 6.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Mistral's Large model via OpenRouter", 
        "cutoff": "2024-04"
    },
    "mistralai/mistral-medium": {
        "provider": "OpenRouter",  # API service
        "company": "MistralAI",    # Model creator
        "model": "mistralai/mistral-medium", 
        "input": 2.7 / 1000000, 
        "output": 8.1 / 1000000, 
        "context": 32000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Mistral's Medium model via OpenRouter", 
        "cutoff": "2024-04"
    },
    
    # Cohere models via OpenRouter
    "cohere/command-r-plus": {
        "provider": "OpenRouter",  # API service
        "company": "Cohere",       # Model creator
        "model": "cohere/command-r-plus", 
        "input": 2.5 / 1000000, 
        "output": 10.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Cohere's Command R+ model via OpenRouter", 
        "cutoff": "2024-04"
    },
    "cohere/command-r": {
        "provider": "OpenRouter",  # API service
        "company": "Cohere",       # Model creator
        "model": "cohere/command-r", 
        "input": 0.5 / 1000000, 
        "output": 1.5 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Cohere's Command R model via OpenRouter", 
        "cutoff": "2024-04"
    },
    
    # DeepSeek models via OpenRouter
    "deepseek/deepseek-chat": {
        "provider": "OpenRouter",  # API service
        "company": "DeepSeek",     # Model creator
        "model": "deepseek/deepseek-chat", 
        "input": 0.14 / 1000000, 
        "output": 0.28 / 1000000, 
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "DeepSeek's Chat model via OpenRouter", 
        "cutoff": "2024-04"
    },
    "deepseek/deepseek-coder": {
        "provider": "OpenRouter",  # API service
        "company": "DeepSeek",     # Model creator
        "model": "deepseek/deepseek-coder", 
        "input": 0.14 / 1000000, 
        "output": 0.28 / 1000000, 
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "DeepSeek's Coder model via OpenRouter", 
        "cutoff": "2024-04"
    },
    
    # Perplexity models via OpenRouter
    "perplexity/llama-3.1-sonar-large-128k-online": {
        "provider": "OpenRouter",  # API service
        "company": "Perplexity",   # Model creator
        "model": "perplexity/llama-3.1-sonar-large-128k-online", 
        "input": 1.0 / 1000000, 
        "output": 1.0 / 1000000, 
        "context": 127072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Perplexity's Llama 3.1 Sonar Large with online search via OpenRouter", 
        "cutoff": "2024-04"
    },
    "perplexity/llama-3.1-sonar-small-128k-online": {
        "provider": "OpenRouter",  # API service
        "company": "Perplexity",   # Model creator
        "model": "perplexity/llama-3.1-sonar-small-128k-online", 
        "input": 0.2 / 1000000, 
        "output": 0.2 / 1000000, 
        "context": 127072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Perplexity's Llama 3.1 Sonar Small with online search via OpenRouter", 
        "cutoff": "2024-04"
    }
}

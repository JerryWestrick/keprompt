from typing import Dict, List
import json
import requests
from rich.console import Console

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiOpenRouter(AiProvider):
    litellm_provider = "openrouter"
    
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": ModelManager.get_model(self.prompt.model).get_api_model_name(),
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

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from OpenRouter API response"""
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        return tokens_in, tokens_out

    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        """Calculate costs based on token usage and model pricing"""
        from .ModelManager import ModelManager
        
        try:
            model = ModelManager.get_model(self.prompt.model_lookup_key)
            cost_in = tokens_in * model.input_cost
            cost_out = tokens_out * model.output_cost
            return cost_in, cost_out
        except Exception:
            # Fallback to zero costs if model not found
            return 0.0, 0.0

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

def update_models(self) -> bool:
    """Update models from OpenRouter API"""
    try:
        from datetime import datetime
        import os
        
        console.print("[cyan]Fetching models from OpenRouter API...[/cyan]")
        
        # Fetch models from OpenRouter API
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {self.prompt.api_key}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            console.print(f"[red]Failed to fetch models: {response.status_code} {response.text}[/red]")
            return False
        
        api_data = response.json()
        
        # Convert to models.json format
        models = {}
        for model_data in api_data.get("data", []):
            model_id = model_data.get("id", "")
            if not model_id:
                continue
            
            # Extract pricing (convert from per-token to per-million-tokens if needed)
            pricing = model_data.get("pricing", {})
            input_cost = float(pricing.get("prompt", 0))
            output_cost = float(pricing.get("completion", 0))
            
            # Extract company from model ID (e.g., "openai/gpt-4" -> "Openai")
            company = "OpenRouter"
            if "/" in model_id:
                company = model_id.split("/")[0].capitalize()
            
            # Build model entry
            models[model_id] = {
                "provider": "OpenRouter",
                "company": company,
                "model": model_id,
                "input": input_cost,
                "output": output_cost,
                "context": model_data.get("context_length", 0),
                "modality_in": "Text+Vision" if model_data.get("architecture", {}).get("modality") == "multimodal" else "Text",
                "modality_out": "Text",
                "functions": "Yes" if "tools" in model_data.get("supported_generation_params", []) else "No",
                "description": model_data.get("description", ""),
                "cutoff": "See provider docs"
            }
        
        # Write to JSON file
        json_path = "prompts/models/OpenRouter.json"
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        output_data = {
            "metadata": {
                "provider": "OpenRouter",
                "last_updated": datetime.now().isoformat(),
                "total_models": len(models)
            },
            "models": models
        }
        
        import json
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]Successfully updated {len(models)} OpenRouter models to {json_path} [/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]Error updating OpenRouter models: {e}[/red]")
        return False

# Register handler only - models loaded from JSON files
ModelManager.register_handler(provider_name="openrouter", handler_class=AiOpenRouter)

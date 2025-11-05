import time
from typing import Dict, List
import json
from rich.console import Console

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedFunctions, DefinedToolsArray


console = Console()
terminal_width = console.size.width


class AiAnthropic(AiProvider):
    litellm_provider = "anthropic"

    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": ModelManager.get_model(self.prompt.model).get_api_model_name(),
            "messages": messages,
            "tools": AnthropicToolsArray,
            "max_tokens": 4096
        }

    def get_api_url(self) -> str:
        return "https://api.anthropic.com/v1/messages"

    def get_headers(self) -> Dict:
        return {
            "x-api-key": self.prompt.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    def to_ai_message(self, response: Dict) -> 'AiMessage':
        content = []
        resp_content = response.get("content", [])

        for part in resp_content:
            if part["type"] == "text":
                content.append(AiTextPart(vm=self.prompt.vm, text=part["text"]))
            elif part["type"] == "tool_use":
                content.append(AiCall(vm=self.prompt.vm, id=part["id"],name=part["name"], arguments=part["input"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)
    def to_company_messages(self, messages: List) -> List[Dict]:

        company_mesages = []
        for msg in messages:
            content = []
            if msg.role == "system":
                self.system_message = msg.content[0].text if msg.content else None
            else:
                for part in msg.content:
                    if   part.type == "text":       content.append({'type': 'text', 'text': part.text})
                    elif part.type == "image_url":  content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': part.media_type, 'data': part.file_contents}})
                    elif part.type == "call":       content.append({'type': 'tool_use', 'id': part.id, 'name': part.name, 'input': part.arguments})
                    elif part.type == 'result':     content.append({'type': 'tool_result', 'tool_use_id': part.id, 'content': part.result})
                    else: raise Exception(f"Unknown part type: {part.type}")

                role = "assistant" if msg.role == "assistant" else "user"
                company_mesages.append({"role": role, "content": content})

        return company_mesages

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from Anthropic API response"""
        usage = response.get("usage", {})
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
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

    # def update_models(self) -> bool:
    #     """Update models from Anthropic API - not yet implemented"""
    #     console.print("[yellow]Model updating not yet implemented for Anthropic provider[/yellow]")
    #     return False

# Prepare tools for Anthropic and Google integrations
AnthropicToolsArray = [
    {
        "name": tool['function']['name'],
        "description": tool['function']['description'],
        "input_schema": tool['function']['parameters'],
    }
    for tool in DefinedToolsArray
]

# Register handler only - models loaded from JSON files
ModelManager.register_handler(provider_name="anthropic", handler_class=AiAnthropic)

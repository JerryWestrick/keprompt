from typing import Dict, List
import json
from rich.console import Console

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiOpenAi(AiProvider):
    litellm_provider = "openai"
    
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": ModelManager.get_model(self.prompt.model).get_api_model_name(),
            "messages": messages,
            "tools": DefinedToolsArray
        }

    def get_api_url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.prompt.api_key}",
            "Content-Type": "application/json"
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
        openai_messages = []

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
                openai_messages.extend(tool_result_messages)
            else:
                message = {"role": msg.role,"content": content[0]["text"] if len(content) == 1 else content}
                if tool_calls:
                    message["tool_calls"] = tool_calls
                openai_messages.append(message)

        return openai_messages

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from OpenAI API response."""
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        return tokens_in, tokens_out

    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        """Calculate costs based on token usage and model pricing"""
        try:
            model = ModelManager.get_model(self.prompt.model_lookup_key)
            cost_in = tokens_in * model.input_cost
            cost_out = tokens_out * model.output_cost
            return cost_in, cost_out
        except Exception:
            # Fallback to zero costs if model not found
            return 0.0, 0.0

# Register handler only - models loaded from JSON files

    # def update_models(self) -> bool:
    #     """Update models from provider API - not yet implemented"""
    #     console.print("[yellow]Model updating not yet implemented for Open provider[/yellow]")
    #     return False

ModelManager.register_handler(provider_name="openai", handler_class=AiOpenAi)

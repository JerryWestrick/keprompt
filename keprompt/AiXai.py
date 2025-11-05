from typing import Dict, List
import json
from rich.console import Console

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiXai(AiProvider):
    litellm_provider = "xai"
    
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {"model": ModelManager.get_model(self.prompt.model).get_api_model_name(),"messages": messages,"tools": DefinedToolsArray,"tool_choice": "auto"}

    def get_api_url(self) -> str:
        return "https://api.x.ai/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.prompt.api_key}","Content-Type": "application/json"}

    def to_ai_message(self, response: Dict) -> AiMessage:
        choice = response.get("choices", [{}])[0].get("message", {})
        content = []

        if choice.get("content"):
            content.append(AiTextPart(vm=self.prompt.vm, text=choice["content"]))

        for tc in choice.get("tool_calls", []):
            content.append(AiCall(vm=self.prompt.vm,name=tc["function"]["name"],arguments=tc["function"]["arguments"],id=tc["id"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        xai_messages = []

        for msg in messages:
            if msg.role == "system":
                self.system_message = msg.content[0].text if msg.content else None
                continue

            content = []
            tool_calls = []
            tool_results = {}

            for part in msg.content:
                if   part.type == "text":       content.append({"type": "text", "text": part.text})
                elif part.type == "image_url":  content.append({'type': 'image_url','image_url': {'url': f"data:{part.media_type};base64,{part.file_contents}"}})
                elif part.type == "call":       tool_calls.append({'id': part.id,'type': 'function','function': {'name': part.name,'arguments': json.dumps(part.arguments)}})
                elif part.type == 'result':     tool_results = {'role':'tool', 'content': part.result, 'tool_call_id': part.id}
                else:                           raise ValueError(f"Unknown part type: {part.type}")

            if msg.role == "tool":
                message = tool_results
            else:
                message = {"role": msg.role,"content": content[0]["text"] if len(content) == 1 else content}

            if tool_calls:
                message["tool_calls"] = tool_calls

            xai_messages.append(message)

        return xai_messages

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from XAI API response"""
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        return tokens_in, tokens_out

    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        """Calculate costs for input and output tokens using model pricing"""
        model_info = ModelManager.get_model(self.prompt.model_lookup_key)
        if not model_info:
            return 0.0, 0.0
        
        cost_in = tokens_in * model_info.input_cost
        cost_out = tokens_out * model_info.output_cost
        return cost_in, cost_out

# Register handler only - models loaded from JSON files

    # def update_models(self) -> bool:
    #     """Update models from provider API - not yet implemented"""
    #     console.print("[yellow]Model updating not yet implemented for Xai provider[/yellow]")
    #     return False

ModelManager.register_handler(provider_name="xai", handler_class=AiXai)

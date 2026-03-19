from typing import Dict, List
import json
from rich.console import Console

from . import FunctionSpace
from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall

console = Console()
terminal_width = console.size.width


class AiCerebras(AiProvider):
    litellm_provider = "cerebras"

    def prepare_request(self, messages: List[Dict]) -> Dict:
        tools = FunctionSpace.functions.get_filtered_tools_array(self.prompt.vm.allowed_functions)
        request = {"model": ModelManager.get_model(self.prompt.model).get_api_model_name(), "messages": messages}
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        return request

    def get_api_url(self) -> str:
        return "https://api.cerebras.ai/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.prompt.api_key}","Content-Type": "application/json"}

    def to_ai_message(self, response: Dict) -> AiMessage:
        choice = response.get("choices", [{}])[0].get("message", {})
        content = []

        if choice.get("content"):
            content.append(AiTextPart(vm=self.prompt.vm, text=choice["content"]))

        for tc in choice.get("tool_calls", []):
            content.append(AiCall(vm=self.prompt.vm,name=tc["function"]["name"],arguments=tc["function"]["arguments"],id=tc["id"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content,
                        model_name=self.prompt.model, provider=self.prompt.provider)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        cerebras_messages = []

        for msg in messages:
            content = []
            tool_calls = []
            tool_result_messages = []

            for part in msg.content:
                if   part.type == "text":       content.append({"type": "text", "text": part.text})
                elif part.type == "image_url":  content.append({'type': 'image_url','image_url': {'url': f"data:{part.media_type};base64,{part.file_contents}"}})
                elif part.type == "call":       tool_calls.append({'id': part.id,'type': 'function','function': {'name': part.name,'arguments': json.dumps(part.arguments)}})
                elif part.type == 'result':     tool_result_messages.append({'role': 'tool', 'tool_call_id': part.id, 'content': part.result})
                else:                           raise ValueError(f"Unknown part type: {part.type}")

            if msg.role == "system":
                # Cerebras requires system content as a plain string
                cerebras_messages.append({"role": "system", "content": "\n".join(p["text"] for p in content)})
            elif msg.role == "tool":
                cerebras_messages.extend(tool_result_messages)
            else:
                message = {"role": msg.role, "content": content[0]["text"] if len(content) == 1 else content}
                if tool_calls:
                    message["tool_calls"] = tool_calls
                cerebras_messages.append(message)

        return cerebras_messages

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from Cerebras API response"""
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

ModelManager.register_handler(provider_name="cerebras", handler_class=AiCerebras)

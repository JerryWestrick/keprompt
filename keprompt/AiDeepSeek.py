from typing import Dict, List
import json
from rich.console import Console

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiDeepSeek(AiProvider):
    litellm_provider = "deepseek"
    
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": ModelManager.get_model(self.prompt.model).get_api_model_name(),
            "messages": messages,
            "tools": DefinedToolsArray,
            "stream": False
        }

    def get_api_url(self) -> str:
        return "https://api.deepseek.com/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.prompt.api_key}",
            "Content-Type": "application/json"
        }

    def to_ai_message(self, response: Dict) -> AiMessage:
        content = []
        choices = response.get("choices", [])
        if not choices:
            raise Exception("No response choices received from DeepSeek API")

        message = choices[0].get("message", {})
        msg_content = message.get("content", None)
        if isinstance(msg_content, str):
            if msg_content:
                content.append(AiTextPart(vm=self.prompt.vm, text=msg_content))
        else:
            for part in msg_content:
                content.append(AiTextPart(vm=self.prompt.vm, text=part["text"]))

        msg_content = message.get("tool_calls", [])
        for part in msg_content:
            fc = part["function"]
            content.append(AiCall(vm=self.prompt.vm,id=part["id"],name=fc["name"],arguments=fc["arguments"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        deepseek_messages = []

        for msg in messages:
            content = []
            tool_calls = []
            for part in msg.content:
                if   part.type == "text":       content.append({"type": "text", "text": part.text})
                elif part.type == "image_url":  content.append({'type': 'image','source': {'type': 'base64','media_type': part.media_type,'data': part.file_contents}})
                elif part.type == "call":       tool_calls.append({'type': 'function','id': part.id,'function': {'name':part.name, 'arguments':json.dumps(part.arguments)}})
                elif part.type == 'result':     deepseek_messages.append({"role": "tool", "tool_call_id": part.id, "content": part.result})
                else: raise Exception(f"Unknown part type: {part.type}")

            if msg.role == "system":
                deepseek_messages.append({"role": "user", "content": f"system: {content[0]['text']}"})
                continue

            if msg.role == "user" and content:
                cmsg = {"role": "user", "content": content }
                deepseek_messages.append(cmsg)
                continue

            if msg.role == "assistant" :
                cmsg = {"role": msg.role}
                if content:     cmsg = {"role": msg.role, "content": content}
                if tool_calls:  cmsg["tool_calls"] = tool_calls
                deepseek_messages.append(cmsg)
                continue


        return deepseek_messages

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from DeepSeek API response"""
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
    #     console.print("[yellow]Model updating not yet implemented for DeepSeek provider[/yellow]")
    #     return False

ModelManager.register_handler(provider_name="deepseek", handler_class=AiDeepSeek)

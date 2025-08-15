from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiDeepSeek(AiProvider):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": self.prompt.model,
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

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for DeepSeek (manual definitions only)"""
        console.print(f"[yellow]DeepSeek API has limited model info, using manual definitions[/yellow]")
        # Use the hardcoded models as the source
        cls._write_json_file(provider_name, DeepSeek_Models)


# Register handler and models
AiRegistry.register_handler(provider_name="DeepSeek", handler_class=AiDeepSeek)

# DeepSeek model definitions and pricing
# Official pricing sources:
# - https://api-docs.deepseek.com/quick_start/pricing
# - https://api-docs.deepseek.com
# Last updated: January 2025
DeepSeek_Models = {
    # Current Models (Standard Pricing - UTC 00:30-16:30)
    "deepseek-chat": {
        "company": "DeepSeek",
        "provider": "DeepSeek", 
        "model": "deepseek-chat", 
        "input": 0.27 / 1000000,  # $0.27 / 1M tokens (cache miss)
        "output": 1.10 / 1000000,  # $1.10 / 1M tokens
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "High-performance model for general tasks (DeepSeek-V3-0324). Supports JSON output, function calling, and FIM completion.", 
        "cutoff": "2024-03"
    },
    "deepseek-reasoner": {
        "company": "DeepSeek",
        "provider": "DeepSeek", 
        "model": "deepseek-reasoner", 
        "input": 0.55 / 1000000,  # $0.55 / 1M tokens (cache miss)
        "output": 2.19 / 1000000,  # $2.19 / 1M tokens
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Advanced reasoning model with transparent thinking process (DeepSeek-R1-0528). Output includes CoT reasoning and final answer.", 
        "cutoff": "2024-05"
    },
    
    # Specific model versions
    "deepseek-v3-0324": {
        "company": "DeepSeek",
        "provider": "DeepSeek", 
        "model": "deepseek-v3-0324", 
        "input": 0.27 / 1000000,  # $0.27 / 1M tokens (cache miss)
        "output": 1.10 / 1000000,  # $1.10 / 1M tokens
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "DeepSeek-V3 model from March 2024. Supports JSON output, function calling, chat prefix completion, and FIM completion.", 
        "cutoff": "2024-03"
    },
    "deepseek-r1-0528": {
        "company": "DeepSeek",
        "provider": "DeepSeek", 
        "model": "deepseek-r1-0528", 
        "input": 0.55 / 1000000,  # $0.55 / 1M tokens (cache miss)
        "output": 2.19 / 1000000,  # $2.19 / 1M tokens
        "context": 64000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "DeepSeek-R1 reasoning model from May 2024. Features transparent chain-of-thought reasoning with output not counting toward context limit.", 
        "cutoff": "2024-05"
    }
}

# Note: DeepSeek offers off-peak pricing discounts (50-75% off) during UTC 16:30-00:30
# Context caching available: Cache hit rates are $0.07/$0.14 per 1M tokens for chat/reasoner respectively

AiDeepSeek.register_models("DeepSeek")

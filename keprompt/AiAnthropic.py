import time
from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedFunctions, DefinedToolsArray


console = Console()
terminal_width = console.size.width


class AiAnthropic(AiCompany):

    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": self.prompt.model,
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


# Prepare tools for Anthropic and Google integrations
AnthropicToolsArray = [
    {
        "name": tool['function']['name'],
        "description": tool['function']['description'],
        "input_schema": tool['function']['parameters'],
    }
    for tool in DefinedToolsArray
]

# Anthropic model definitions and pricing
# Official pricing source: https://www.anthropic.com/pricing
# Last updated: January 2025
Anthropic_Models = {
    # Latest Claude 4 models
    "claude-opus-4": {"company": "Anthropic", "model": "claude-opus-4", "input": 0.000015, "output": 0.000075, "context": 200000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Most intelligent model for complex tasks", "cutoff": "See docs"},
    "claude-sonnet-4": {"company": "Anthropic", "model": "claude-sonnet-4", "input": 0.000003, "output": 0.000015, "context": 200000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Optimal balance of intelligence, cost, and speed", "cutoff": "See docs"},
    
    # Claude 3.5 models (still available)
    "claude-haiku-3.5": {"company": "Anthropic", "model": "claude-haiku-3.5", "input": 0.0000008, "output": 0.000004, "context": 200000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Fastest, most cost-effective model", "cutoff": "See docs"},
    
    # Legacy Claude 3 models (still available)
    "claude-opus-3": {"company": "Anthropic", "model": "claude-opus-3", "input": 0.000015, "output": 0.000075, "context": 200000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Legacy most intelligent model", "cutoff": "See docs"},
    "claude-sonnet-3.7": {"company": "Anthropic", "model": "claude-sonnet-3.7", "input": 0.000003, "output": 0.000015, "context": 200000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Legacy balanced model", "cutoff": "See docs"},
    "claude-haiku-3": {"company": "Anthropic", "model": "claude-haiku-3", "input": 0.00000025, "output": 0.00000125, "context": 200000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Legacy fastest model", "cutoff": "See docs"},
}

AiRegistry.register_handler(company_name="Anthropic", handler_class=AiAnthropic)
AiRegistry.register_models_from_dict(model_definitions=Anthropic_Models)

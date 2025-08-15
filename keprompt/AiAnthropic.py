import time
from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedFunctions, DefinedToolsArray


console = Console()
terminal_width = console.size.width


class AiAnthropic(AiProvider):

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

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for Anthropic (manual definitions only)"""
        console.print(f"[yellow]Anthropic has no models API, using manual definitions[/yellow]")
        # Use the hardcoded models as the source
        cls._write_json_file(provider_name, Anthropic_Models)


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
# Official pricing sources:
# - https://www.anthropic.com/pricing
# - https://docs.anthropic.com/en/docs/about-claude/models
# Last updated: January 2025
Anthropic_Models = {
    # CLAUDE 4.1 SERIES - Latest flagship models
    "claude-opus-4.1": {
        "company": "Anthropic",
        "provider": "Anthropic", 
        "model": "claude-opus-4.1", 
        "input": 15.0 / 1000000,  # $15.00 / 1M tokens
        "output": 75.0 / 1000000,  # $75.00 / 1M tokens
        "context": 200000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Most powerful model for highly complex tasks (claude-opus-4.1-20250514)", 
        "cutoff": "2025-05"
    },
    "claude-opus-4-latest": {  # claude-opus-4-20250514
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-opus-4-latest",
        "input": 15.0 / 1000000,  # $15 / MTok
        "output": 75.0 / 1000000,  # $75 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Our previous flagship model with very high intelligence and capability (claude-opus-4-20250514)",
        "cutoff": "2025-03"
    },
    "claude-sonnet-4-latest": {  # claude-sonnet-4-20250514
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-sonnet-4-latest",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High-performance model with exceptional reasoning capabilities and balanced performance (claude-sonnet-4-20250514)",
        "cutoff": "2025-03"
    },
    "claude-3-7-sonnet-latest": {  # claude-3-7-sonnet-20250219
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-7-sonnet-latest",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High-performance model with early extended thinking capabilities (claude-3-7-sonnet-20250219)",
        "cutoff": "2024-10"
    },
    "claude-3-5-sonnet-latest": {  # claude-3-5-sonnet-20241022
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-5-sonnet-latest",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High level of intelligence and capability with strong performance in coding and agentic tasks (claude-3-5-sonnet-20241022)",
        "cutoff": "2024-04"
    },
    "claude-3-5-haiku-latest": {  # claude-3-5-haiku-20241022
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-5-haiku-latest",
        "input": 0.8 / 1000000,  # $0.80 / MTok
        "output": 4.0 / 1000000,  # $4 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Our fastest model with intelligence at blazing speeds (claude-3-5-haiku-20241022)",
        "cutoff": "2024-07"
    },
    
    # Specific dated versions - Latest Models
    "claude-opus-4-1-20250805": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-opus-4-1-20250805",
        "input": 15.0 / 1000000,  # $15 / MTok
        "output": 75.0 / 1000000,  # $75 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Our most capable and intelligent model yet. Claude Opus 4.1 sets new standards in complex reasoning and advanced coding.",
        "cutoff": "2025-03"
    },
    "claude-opus-4-20250514": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-opus-4-20250514",
        "input": 15.0 / 1000000,  # $15 / MTok
        "output": 75.0 / 1000000,  # $75 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Our previous flagship model with very high intelligence and capability",
        "cutoff": "2025-03"
    },
    "claude-sonnet-4-20250514": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-sonnet-4-20250514",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High-performance model with exceptional reasoning capabilities and balanced performance",
        "cutoff": "2025-03"
    },
    "claude-3-7-sonnet-20250219": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-7-sonnet-20250219",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High-performance model with early extended thinking capabilities",
        "cutoff": "2024-10"
    },
    "claude-3-5-sonnet-20241022": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "High level of intelligence and capability with strong performance in coding and agentic tasks",
        "cutoff": "2024-04"
    },
    "claude-3-5-sonnet-20240620": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-5-sonnet-20240620",
        "input": 3.0 / 1000000,  # $3 / MTok
        "output": 15.0 / 1000000,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Previous version of Claude 3.5 Sonnet",
        "cutoff": "2024-04"
    },
    "claude-3-5-haiku-20241022": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-5-haiku-20241022",
        "input": 0.8 / 1000000,  # $0.80 / MTok
        "output": 4.0 / 1000000,  # $4 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Our fastest model with intelligence at blazing speeds",
        "cutoff": "2024-07"
    },
    
    # Legacy Models
    "claude-3-opus-20240229": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-opus-20240229",
        "input": 15.0 / 1000000,  # $15 / MTok
        "output": 75.0 / 1000000,  # $75 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Legacy Claude 3 Opus model",
        "cutoff": "2023-08"
    },
    "claude-3-haiku-20240307": {
        "company": "Anthropic",
        "provider": "Anthropic",
        "model": "claude-3-haiku-20240307",
        "input": 0.25 / 1000000,  # $0.25 / MTok
        "output": 1.25 / 1000000,  # $1.25 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Fast and compact model for near-instant responsiveness",
        "cutoff": "2023-08"
    }
}

AiRegistry.register_handler(provider_name="Anthropic", handler_class=AiAnthropic)
AiAnthropic.register_models("Anthropic")

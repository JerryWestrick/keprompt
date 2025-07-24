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
    "claude-3-5-haiku-latest": {
        "company": "Anthropic",
        "model": "Claude 3.5 Haiku",
        "input": 0.00000025,  # $0.25 / MTok
        "output": 0.00000125,  # $1.25 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Claude 3.5 Haiku is Anthropic’s fastest and most cost-effective model, optimized for rapid responses and efficiency. It excels in tasks like knowledge retrieval, sales automation, and lightweight chatbots, balancing intelligence with low latency.",
        "cutoff": "2024-10",  # End of October 2024
        "link": "https://docs.anthropic.com/en/docs/about-claude/models/overview"
    },
    "claude-3-5-sonnet-latest": {
        "company": "Anthropic",
        "model": "Claude 3.5 Sonnet",
        "input": 0.000003,  # $3 / MTok
        "output": 0.000015,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Claude 3.5 Sonnet balances intelligence, speed, and cost, offering strong performance in coding, agentic tasks, and visual data extraction. It’s ideal for complex workflows, tool use, and applications requiring advanced reasoning.",
        "cutoff": "2024-10",  # End of October 2024
        "link": "https://docs.anthropic.com/en/docs/about-claude/models/overview"
    },
    "claude-3-7-sonnet-latest": {
        "company": "Anthropic",
        "model": "Claude 3.7 Sonnet",
        "input": 0.000003,  # $3 / MTok
        "output": 0.000015,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Claude 3.7 Sonnet is Anthropic’s most intelligent model, a hybrid reasoning model excelling in coding, content generation, and data analysis. It offers both rapid responses and extended thinking for complex problem-solving.",
        "cutoff": "2024-10",  # End of October 2024
        "link": "https://docs.anthropic.com/en/docs/about-claude/models/overview"
    },
    "claude-opus-4-0": {
        "company": "Anthropic",
        "model": "Claude 4 Opus",
        "input":  0.000015,  # $15 / MTok
        "output": 0.000075,  # $75 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Claude 4 Opus is Anthropic’s most powerful model, excelling in advanced coding, complex reasoning, and long-horizon tasks. It’s ideal for enterprise applications and AI agents requiring sustained performance and high accuracy.",
        "cutoff": "2024-11",  # November 2024
        "link": "https://docs.anthropic.com/en/docs/about-claude/models/overview"
    },
    "claude-sonnet-4-0": {
        "company": "Anthropic",
        "model": "Claude 4 Sonnet",
        "input": 0.000003,  # $3 / MTok
        "output": 0.000015,  # $15 / MTok
        "context": 200000,
        "modality_in": "Text+Vision",
        "modality_out": "Text",
        "functions": "Yes",
        "description": "Claude 4 Sonnet offers superior coding and reasoning capabilities, improving on Claude 3.7 Sonnet. It’s ideal for high-volume use cases, user-facing assistants, and tasks requiring precise instruction-following and adaptive tool use.",
        "cutoff": "2024-11",  # November 2024
        "link": "https://docs.anthropic.com/en/docs/about-claude/models/overview"
    }
}

AiRegistry.register_handler(company_name="Anthropic", handler_class=AiAnthropic)
AiRegistry.register_models_from_dict(model_definitions=Anthropic_Models)

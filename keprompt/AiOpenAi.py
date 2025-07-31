from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiOpenAi(AiCompany):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": self.prompt.model,
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


# Register handler and models
AiRegistry.register_handler(company_name="OpenAI", handler_class=AiOpenAi)

# OpenAI model definitions and pricing
# Official pricing source: https://openai.com/api/pricing/
# Last updated: January 2025
OpenAI_Models = {
    # Latest GPT models
    "gpt-4.1":      {"company": "OpenAI", "model": "gpt-4.1", "input": 2 / 1000000, "output": 8 / 1000000, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Smartest model for complex tasks", "cutoff": "2024-06"},
    "gpt-4.1-mini": {"company": "OpenAI", "model": "gpt-4.1-mini", "input": 0.4 / 1000000, "output": 1.6 / 1000000, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Affordable model balancing speed and intelligence", "cutoff": "2024-06"},
    "gpt-4.1-nano": {"company": "OpenAI", "model": "gpt-4.1-nano", "input": 0.1 / 1000000, "output": 0.4 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Fastest, most cost-effective model for low-latency tasks", "cutoff": "2023-10"},
    
    # Reasoning models
    "o3": {"company": "OpenAI", "model": "o3", "input": 0.000002, "output": 0.000008, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Most powerful reasoning model with leading performance", "cutoff": "2024-06"},
    "o4-mini": {"company": "OpenAI", "model": "o4-mini", "input": 0.0000011, "output": 0.0000044, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Faster, cost-efficient reasoning model", "cutoff": "2024-06"},
    
    # Legacy GPT-4o models (still available)
    "gpt-4o": {"company": "OpenAI", "model": "gpt-4o", "input": 0.000005, "output": 0.00002, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Advanced multimodal model for complex tasks", "cutoff": "2023-10"},
    "gpt-4o-mini": {"company": "OpenAI", "model": "gpt-4o-mini", "input": 0.0000006, "output": 0.0000024, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Affordable multimodal model", "cutoff": "2023-10"}    
}

AiRegistry.register_models_from_dict(model_definitions=OpenAI_Models)

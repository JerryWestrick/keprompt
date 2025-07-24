from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiXai(AiCompany):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {"model": self.prompt.model,"messages": messages,"tools": DefinedToolsArray,"tool_choice": "auto"}

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


# Register handler and models
AiRegistry.register_handler(company_name="XAI", handler_class=AiXai)

# XAI model definitions and pricing
# Official pricing source: https://x.ai/api
# Last updated: January 2025
XAI_Models = {
    # Latest Grok models
    "grok-4": {"company": "XAI", "model": "grok-4", "input": 0.000003, "output": 0.000015, "context": 256000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "The world's best model", "cutoff": "See docs"},
    "grok-3": {"company": "XAI", "model": "grok-3", "input": 0.000003, "output": 0.000015, "context": 131072, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Flagship enterprise model with advanced reasoning", "cutoff": "See docs"},
    "grok-3-mini": {"company": "XAI", "model": "grok-3-mini", "input": 0.0000003, "output": 0.0000005, "context": 131072, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Lightweight reasoning model for cost-effective applications", "cutoff": "See docs"},
    
    # Legacy models (still available)
    "grok-2-1212": {"company": "XAI", "model": "grok-2-1212", "input": 0.000002, "output": 0.000010, "context": 131072, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Updated Grok-2 model with improved performance", "cutoff": "See docs"},
    "grok-2-vision-1212": {"company": "XAI", "model": "grok-2-vision-1212", "input": 0.000002, "output": 0.000010, "context": 131072, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Vision-capable Grok-2 model", "cutoff": "See docs"}
}

AiRegistry.register_models_from_dict(model_definitions=XAI_Models)

from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiXai(AiProvider):
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

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for XAI (manual definitions only)"""
        console.print(f"[yellow]XAI API has limited model info, using manual definitions[/yellow]")
        # Use the hardcoded models as the source
        cls._write_json_file(provider_name, XAI_Models)


# Register handler and models
AiRegistry.register_handler(provider_name="XAI", handler_class=AiXai)

# XAI model definitions and pricing
# Official pricing sources:
# - https://x.ai/api
# - https://docs.x.ai/docs/models
# Last updated: January 2025

# PRICING SCHEMES EXPLAINED:
# 1. TEXT MODELS: Standard per-token pricing (input/output per 1M tokens)
# 2. IMAGE GENERATION: Per-image pricing ($0.07 per image)
# 3. VISION MODELS: Text input pricing + image processing capabilities
# 4. LARGE CONTEXT: Higher pricing for contexts >128K tokens ($6/$30 vs $3/$15)

XAI_Models = {
    # LATEST MODELS - User-friendly aliases
    "grok-4": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-4", 
        "input": 3.0 / 1000000,  # $3.00 / 1M tokens
        "output": 15.0 / 1000000,  # $15.00 / 1M tokens
        "context": 256000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "The world's best model with advanced reasoning, coding, and visual processing capabilities", 
        "cutoff": "2025-07"
    },
    "grok-3": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-3", 
        "input": 3.0 / 1000000,  # $3.00 / 1M tokens
        "output": 15.0 / 1000000,  # $15.00 / 1M tokens
        "context": 131072, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Flagship enterprise model that excels at data extraction, programming, and text summarization", 
        "cutoff": "2025-02"
    },
    "grok-3-mini": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-3-mini", 
        "input": 0.3 / 1000000,  # $0.30 / 1M tokens
        "output": 0.5 / 1000000,  # $0.50 / 1M tokens
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Lightweight model that thinks before responding. Excels at quantitative tasks involving math and reasoning", 
        "cutoff": "2025-02"
    },
    
    # LEGACY MODELS - Still available
    "grok-2-vision-1212": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-2-vision-1212", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 10.0 / 1000000,  # $10.00 / 1M tokens
        "context": 131072, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Vision-capable Grok-2 model with image understanding", 
        "cutoff": "2024-12"
    },
    "grok-2-1212": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-2-1212", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 10.0 / 1000000,  # $10.00 / 1M tokens
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Updated Grok-2 model with improved performance", 
        "cutoff": "2024-12"
    },
    "grok-vision-beta": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-vision-beta", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 10.0 / 1000000,  # $10.00 / 1M tokens
        "context": 131072, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Beta vision model for image understanding tasks", 
        "cutoff": "2024-12"
    },
    "grok-beta": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-beta", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 10.0 / 1000000,  # $10.00 / 1M tokens
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Beta version of Grok model", 
        "cutoff": "2024-12"
    },
    
    # SPECIALIZED MODELS - Different pricing structure
    "grok-2-image-1212": {
        "company": "XAI",
        "provider": "XAI", 
        "model": "grok-2-image-1212", 
        "input": 0.0 / 1000000,  # No text input pricing
        "output": 0.07,  # $0.07 per image generated
        "context": 131072, 
        "modality_in": "Text", 
        "modality_out": "Images", 
        "functions": "No", 
        "description": "Latest image generation model capable of generating multiple images from text prompts", 
        "cutoff": "2024-12"
    }
}

# Note: Large context pricing (>128K tokens):
# - Input: $6.00 / 1M tokens (2x standard rate)
# - Output: $30.00 / 1M tokens (2x standard rate)
# - Applies to grok-4 when using contexts larger than 128K tokens

AiXai.register_models("XAI")

from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiOpenAi(AiProvider):
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

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from OpenAI API response."""
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        return tokens_in, tokens_out

    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        """Calculate costs based on OpenAI pricing for the current model."""
        # Get model pricing from the OpenAI_Models dictionary
        model_info = OpenAI_Models.get(self.prompt.model, {})
        
        # Get pricing per token (already in per-token format in the models dict)
        input_price_per_token = model_info.get("input", 0.0)
        output_price_per_token = model_info.get("output", 0.0)
        
        # Calculate costs
        cost_in = tokens_in * input_price_per_token
        cost_out = tokens_out * output_price_per_token
        
        return cost_in, cost_out

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for OpenAI (manual definitions only)"""
        console.print(f"[yellow]OpenAI API has limited model info, using manual definitions[/yellow]")
        # Use the hardcoded models as the source
        cls._write_json_file(provider_name, OpenAI_Models)


# Register handler and models
AiRegistry.register_handler(provider_name="OpenAI", handler_class=AiOpenAi)

# OpenAI model definitions and pricing
# Official pricing sources:
# - https://openai.com/api/pricing/
# - https://platform.openai.com/docs/models
# Last updated: January 2025
OpenAI_Models = {
    # GPT-5 SERIES - Latest flagship models
    "gpt-5": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-5", 
        "input": 1.25 / 1000000,  # $1.25 / 1M tokens
        "output": 10.0 / 1000000,  # $10.00 / 1M tokens
        "context": 400000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "OpenAI's most advanced model with major improvements in reasoning, code quality, and user experience", 
        "cutoff": "2025-08"
    },
    "gpt-5-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-5-mini", 
        "input": 0.25 / 1000000, 
        "output": 2.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "A faster, cheaper version of GPT-5 for well-defined tasks", 
        "cutoff": "2024-06"
    },
    "gpt-5-nano": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-5-nano", 
        "input": 0.05 / 1000000, 
        "output": 0.4 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "The fastest, cheapest version of GPT-5—great for summarization and classification tasks", 
        "cutoff": "2024-06"
    },
    
    # GPT-4.1 Series - Current Generation
    "gpt-4.1": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-4.1", 
        "input": 5.0 / 1000000, 
        "output": 20.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Fast, highly intelligent model with largest context window", 
        "cutoff": "2024-06"
    },
    "gpt-4.1-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-4.1-mini", 
        "input": 0.8 / 1000000, 
        "output": 3.2 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Balanced for intelligence, speed, and cost", 
        "cutoff": "2024-06"
    },
    "gpt-4.1-nano": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-4.1-nano", 
        "input": 0.2 / 1000000, 
        "output": 0.8 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Fastest, most cost-effective GPT-4.1 model", 
        "cutoff": "2024-06"
    },
    
    # o3/o4 Reasoning Models
    "o3": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o3", 
        "input": 15.0 / 1000000, 
        "output": 60.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Our most powerful reasoning model", 
        "cutoff": "2024-06"
    },
    "o3-pro": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o3-pro", 
        "input": 30.0 / 1000000, 
        "output": 120.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Version of o3 with more compute for better responses", 
        "cutoff": "2024-06"
    },
    "o3-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o3-mini", 
        "input": 1.0 / 1000000, 
        "output": 4.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "A small model alternative to o3", 
        "cutoff": "2024-06"
    },
    "o4-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o4-mini", 
        "input": 1.1 / 1000000, 
        "output": 4.4 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Faster, more affordable reasoning model", 
        "cutoff": "2024-06"
    },
    
    # Deep Research Models
    "o3-deep-research": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o3-deep-research", 
        "input": 20.0 / 1000000, 
        "output": 80.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Our most powerful deep research model", 
        "cutoff": "2024-06"
    },
    "o4-mini-deep-research": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o4-mini-deep-research", 
        "input": 1.5 / 1000000, 
        "output": 6.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Faster, more affordable deep research model", 
        "cutoff": "2024-06"
    },
    
    # Legacy GPT-4o models (still available)
    "gpt-4o": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-4o", 
        "input": 5.0 / 1000000, 
        "output": 20.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Advanced multimodal model for complex tasks", 
        "cutoff": "2023-10"
    },
    "gpt-4o-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "gpt-4o-mini", 
        "input": 0.6 / 1000000, 
        "output": 2.4 / 1000000, 
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Affordable multimodal model", 
        "cutoff": "2023-10"
    },
    
    # Legacy o1 models (still available)
    "o1": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o1", 
        "input": 15.0 / 1000000, 
        "output": 60.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Previous full o-series reasoning model", 
        "cutoff": "2023-10"
    },
    "o1-pro": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o1-pro", 
        "input": 30.0 / 1000000, 
        "output": 120.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Version of o1 with more compute for better responses", 
        "cutoff": "2023-10"
    },
    "o1-mini": {
        "company": "OpenAI",
        "provider": "OpenAI", 
        "model": "o1-mini", 
        "input": 3.0 / 1000000, 
        "output": 12.0 / 1000000, 
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "A small model alternative to o1", 
        "cutoff": "2023-10"
    }
}

AiOpenAi.register_models("OpenAI")

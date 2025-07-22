from typing import Dict, List
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiMistral(AiCompany):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {"model": self.prompt.model,"messages": messages,"tools": DefinedToolsArray,"tool_choice": "auto"}

    def get_api_url(self) -> str:
        return "https://api.mistral.ai/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.prompt.api_key}","Content-Type": "application/json","Accept": "application/json"}

    def to_ai_message(self, response: Dict) -> AiMessage:
        choice = response.get("choices", [{}])[0].get("message", {})
        content = []

        if choice.get("content"):
            content.append(AiTextPart(vm=self.prompt.vm, text=choice["content"]))

        tool_calls = choice.get("tool_calls", [])
        if not tool_calls:
            tool_calls = []

        for tool_call in tool_calls:
            content.append(AiCall(vm=self.prompt.vm,name=tool_call["function"]["name"],arguments=tool_call["function"]["arguments"],id=tool_call["id"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        mistral_messages = []

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
                elif part.type == "call":       tool_calls.append({'id': part.id,'type': 'function','function': {'name': part.name,'arguments': part.arguments}})
                elif part.type == 'result':     tool_results = {'id': part.id,'content': part.result}
                else:                           raise ValueError(f"Unknown part type: {part.type}")


            if msg.role == "tool":
                message = {"role": "tool", "content": tool_results["content"], "tool_call_id": tool_results["id"]}
            else:
                message = {"role": msg.role,"content": content}
                if tool_calls:
                    message["tool_calls"] = tool_calls

            mistral_messages.append(message)

        return mistral_messages


# Register handler and models
AiRegistry.register_handler(company_name="MistralAI", handler_class=AiMistral)

# MistralAI model definitions and pricing
# Official pricing source: https://mistral.ai/pricing
# Last updated: January 2025
Mistral_Models = {
    # Latest Premier models
    "mistral-medium-3": {"company": "MistralAI", "model": "mistral-medium-3", "input": 0.0000004, "output": 0.000002, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "State-of-the-art performance. Simplified enterprise deployments. Cost-efficient", "cutoff": "See docs"},
    "magistral-medium": {"company": "MistralAI", "model": "magistral-medium", "input": 0.000002, "output": 0.000005, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Thinking model excelling in domain-specific, transparent, and multilingual reasoning", "cutoff": "See docs"},
    "mistral-large": {"company": "MistralAI", "model": "mistral-large", "input": 0.000002, "output": 0.000006, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Top-tier reasoning for high-complexity tasks and sophisticated problems", "cutoff": "See docs"},
    "devstral-medium": {"company": "MistralAI", "model": "devstral-medium", "input": 0.0000004, "output": 0.000002, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Enhanced model for advanced coding agents", "cutoff": "See docs"},
    
    # Open models
    "mistral-small-3.2": {"company": "MistralAI", "model": "mistral-small-3.2", "input": 0.0000001, "output": 0.0000003, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "SOTA. Multimodal. Multilingual. Apache 2.0", "cutoff": "See docs"},
    "magistral-small": {"company": "MistralAI", "model": "magistral-small", "input": 0.0000005, "output": 0.0000015, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Thinking model excelling in domain-specific reasoning", "cutoff": "See docs"},
    "codestral": {"company": "MistralAI", "model": "codestral", "input": 0.0000003, "output": 0.0000009, "context": 32000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Lightweight, fast, and proficient in over 80 programming languages", "cutoff": "See docs"},
    "devstral-small": {"company": "MistralAI", "model": "devstral-small", "input": 0.0000001, "output": 0.0000003, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "The best open-source model for coding agents", "cutoff": "See docs"},
    "voxtral-small": {"company": "MistralAI", "model": "voxtral-small", "input": 0.0000001, "output": 0.0000003, "context": 128000, "modality_in": "Text+Audio", "modality_out": "Text", "functions": "Yes", "description": "State-of-the-art performance on speech and audio understanding", "cutoff": "See docs"},
    "voxtral-mini": {"company": "MistralAI", "model": "voxtral-mini", "input": 0.00000004, "output": 0.00000004, "context": 128000, "modality_in": "Text+Audio", "modality_out": "Text", "functions": "Yes", "description": "Low-latency speech recognition for edge and devices", "cutoff": "See docs"},
    
    # Vision models
    "pixtral-large": {"company": "MistralAI", "model": "pixtral-large", "input": 0.000002, "output": 0.000006, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Vision-capable large model with frontier reasoning capabilities", "cutoff": "See docs"},
    "pixtral-12b": {"company": "MistralAI", "model": "pixtral-12b", "input": 0.00000015, "output": 0.00000015, "context": 128000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Vision-capable small model", "cutoff": "See docs"},
    
    # Other models
    "mistral-nemo": {"company": "MistralAI", "model": "mistral-nemo", "input": 0.00000015, "output": 0.00000015, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "State-of-the-art Mistral model trained specifically for code tasks", "cutoff": "See docs"},
    "mistral-saba": {"company": "MistralAI", "model": "mistral-saba", "input": 0.0000002, "output": 0.0000006, "context": 32000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Custom-trained model to serve specific geographies, markets, and customers", "cutoff": "See docs"},
    
    # Legacy models (still available)
    "ministral-8b-24.10": {"company": "MistralAI", "model": "ministral-8b-24.10", "input": 0.0000001, "output": 0.000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Powerful model for on-device use cases", "cutoff": "See docs"},
    "ministral-3b-24.10": {"company": "MistralAI", "model": "ministral-3b-24.10", "input": 0.00000004, "output": 0.00000004, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Most efficient edge model", "cutoff": "See docs"},
    "mistral-7b": {"company": "MistralAI", "model": "mistral-7b", "input": 0.00000025, "output": 0.00000025, "context": 32000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "A 7B transformer model, fast-deployed and easily customisable", "cutoff": "See docs"},
    "mixtral-8x7b": {"company": "MistralAI", "model": "mixtral-8x7b", "input": 0.0000007, "output": 0.0000007, "context": 32000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "A 7B sparse Mixture-of-Experts (SMoE). Uses 12.9B active parameters out of 45B total", "cutoff": "See docs"},
    "mixtral-8x22b": {"company": "MistralAI", "model": "mixtral-8x22b", "input": 0.000002, "output": 0.000006, "context": 64000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "A 22B sparse Mixture-of-Experts (SMoE). Uses only 39B active parameters out of 141B", "cutoff": "See docs"}
}

AiRegistry.register_models_from_dict(model_definitions=Mistral_Models)

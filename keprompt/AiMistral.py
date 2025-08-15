from typing import Dict, List
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiMistral(AiProvider):
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

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for MistralAI (manual definitions only)"""
        console.print(f"[yellow]MistralAI API has limited model info, using manual definitions[/yellow]")
        # Use the hardcoded models as the source
        cls._write_json_file(provider_name, Mistral_Models)


# Register handler and models
AiRegistry.register_handler(provider_name="MistralAI", handler_class=AiMistral)

# MistralAI model definitions and pricing
# Official pricing sources:
# - https://mistral.ai/pricing
# - https://docs.mistral.ai/getting-started/models/models_overview
# Last updated: January 2025

# PRICING SCHEMES EXPLAINED:
# 1. TEXT MODELS: Standard per-token pricing (input/output per 1M tokens)
# 2. AUDIO MODELS: Transcription pricing (per minute or per request)
# 3. OCR MODELS: Document processing pricing (per page/document)
# 4. EMBEDDING MODELS: Per-token embedding generation
# 5. MODERATION MODELS: Per-request content moderation

Mistral_Models = {
    # PREMIER MODELS - User-friendly aliases
    "mistral-medium-latest": {  # mistral-medium-2508
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-medium-latest", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 6.0 / 1000000,  # $6.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Frontier-class multimodal model with improved tone and performance (mistral-medium-2508)", 
        "cutoff": "2025-08"
    },
    "magistral-medium-latest": {  # magistral-medium-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "magistral-medium-latest", 
        "input": 3.0 / 1000000,  # $3.00 / 1M tokens
        "output": 9.0 / 1000000,  # $9.00 / 1M tokens
        "context": 40000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Frontier-class reasoning model with advanced problem-solving capabilities (magistral-medium-2507)", 
        "cutoff": "2025-07"
    },
    "mistral-large-latest": {  # mistral-large-2411
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-large-latest", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 6.0 / 1000000,  # $6.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Top-tier reasoning model for high-complexity tasks (mistral-large-2411)", 
        "cutoff": "2024-11"
    },
    "pixtral-large-latest": {  # pixtral-large-2411
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "pixtral-large-latest", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 6.0 / 1000000,  # $6.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Frontier-class multimodal model with image understanding (pixtral-large-2411)", 
        "cutoff": "2024-11"
    },
    "codestral-latest": {  # codestral-2508
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "codestral-latest", 
        "input": 0.3 / 1000000,  # $0.30 / 1M tokens
        "output": 0.9 / 1000000,  # $0.90 / 1M tokens
        "context": 256000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Cutting-edge coding model for FIM, code correction, and test generation (codestral-2508)", 
        "cutoff": "2025-08"
    },
    "devstral-medium-latest": {  # devstral-medium-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "devstral-medium-latest", 
        "input": 1.0 / 1000000,  # $1.00 / 1M tokens
        "output": 3.0 / 1000000,  # $3.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Enterprise-grade coding model for codebase exploration and multi-file editing (devstral-medium-2507)", 
        "cutoff": "2025-07"
    },
    "ministral-3b-latest": {  # ministral-3b-2410
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "ministral-3b-latest", 
        "input": 0.04 / 1000000,  # $0.04 / 1M tokens
        "output": 0.04 / 1000000,  # $0.04 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "World's best edge model for low-latency applications (ministral-3b-2410)", 
        "cutoff": "2024-10"
    },
    "ministral-8b-latest": {  # ministral-8b-2410
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "ministral-8b-latest", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens
        "output": 0.1 / 1000000,  # $0.10 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Powerful edge model with high performance/price ratio (ministral-8b-2410)", 
        "cutoff": "2024-10"
    },
    
    # OPEN MODELS - User-friendly aliases
    "mistral-small-latest": {  # mistral-small-2506
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-small-latest", 
        "input": 0.2 / 1000000,  # $0.20 / 1M tokens
        "output": 0.6 / 1000000,  # $0.60 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Leader in small models category with image understanding (mistral-small-2506)", 
        "cutoff": "2025-06"
    },
    "magistral-small-latest": {  # magistral-small-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "magistral-small-latest", 
        "input": 0.2 / 1000000,  # $0.20 / 1M tokens
        "output": 0.6 / 1000000,  # $0.60 / 1M tokens
        "context": 40000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Small reasoning model with advanced problem-solving (magistral-small-2507)", 
        "cutoff": "2025-07"
    },
    "devstral-small-latest": {  # devstral-small-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "devstral-small-latest", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens
        "output": 0.3 / 1000000,  # $0.30 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Open source coding model for codebase exploration and software engineering (devstral-small-2507)", 
        "cutoff": "2025-07"
    },
    "open-mistral-nemo": {  # open-mistral-nemo-2407
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "open-mistral-nemo", 
        "input": 0.3 / 1000000,  # $0.30 / 1M tokens
        "output": 0.3 / 1000000,  # $0.30 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Best multilingual open source model (open-mistral-nemo-2407)", 
        "cutoff": "2024-07"
    },
    "pixtral-12b": {  # pixtral-12b-2409
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "pixtral-12b", 
        "input": 0.15 / 1000000,  # $0.15 / 1M tokens
        "output": 0.15 / 1000000,  # $0.15 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "12B model with image understanding capabilities (pixtral-12b-2409)", 
        "cutoff": "2024-09"
    },
    
    # AUDIO MODELS - Different pricing structure
    "voxtral-small-latest": {  # voxtral-small-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "voxtral-small-latest", 
        "input": 0.2 / 1000000,  # $0.20 / 1M tokens (text input)
        "output": 0.6 / 1000000,  # $0.60 / 1M tokens (text output)
        "context": 32000, 
        "modality_in": "Text+Audio", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "First model with audio input capabilities for instruct use cases (voxtral-small-2507)", 
        "cutoff": "2025-07"
    },
    "voxtral-mini-latest": {  # voxtral-mini-2507
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "voxtral-mini-latest", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens (text input)
        "output": 0.3 / 1000000,  # $0.30 / 1M tokens (text output)
        "context": 32000, 
        "modality_in": "Text+Audio", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Mini version of audio input model for transcription (voxtral-mini-2507)", 
        "cutoff": "2025-07"
    },
    
    # SPECIALIZED MODELS - Different pricing schemes
    "mistral-embed": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-embed", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens
        "output": 0.0 / 1000000,  # No output tokens for embeddings
        "context": 8000, 
        "modality_in": "Text", 
        "modality_out": "Embeddings", 
        "functions": "No", 
        "description": "State-of-the-art semantic embeddings for text representation", 
        "cutoff": "2023-12"
    },
    "codestral-embed": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "codestral-embed", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens
        "output": 0.0 / 1000000,  # No output tokens for embeddings
        "context": 8000, 
        "modality_in": "Text", 
        "modality_out": "Embeddings", 
        "functions": "No", 
        "description": "State-of-the-art semantic embeddings for code representation", 
        "cutoff": "2025-05"
    },
    
    # SPECIFIC DATED VERSIONS - Premier Models
    "mistral-medium-2508": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-medium-2508", 
        "input": 2.0 / 1000000,  # $2.00 / 1M tokens
        "output": 6.0 / 1000000,  # $6.00 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Frontier-class multimodal model with improved tone and performance", 
        "cutoff": "2025-08"
    },
    "magistral-medium-2507": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "magistral-medium-2507", 
        "input": 3.0 / 1000000,  # $3.00 / 1M tokens
        "output": 9.0 / 1000000,  # $9.00 / 1M tokens
        "context": 40000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Frontier-class reasoning model with advanced problem-solving capabilities", 
        "cutoff": "2025-07"
    },
    "codestral-2508": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "codestral-2508", 
        "input": 0.3 / 1000000,  # $0.30 / 1M tokens
        "output": 0.9 / 1000000,  # $0.90 / 1M tokens
        "context": 256000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Cutting-edge coding model for FIM, code correction, and test generation", 
        "cutoff": "2025-08"
    },
    
    # SPECIFIC DATED VERSIONS - Open Models
    "mistral-small-2506": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "mistral-small-2506", 
        "input": 0.2 / 1000000,  # $0.20 / 1M tokens
        "output": 0.6 / 1000000,  # $0.60 / 1M tokens
        "context": 128000, 
        "modality_in": "Text+Vision", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Leader in small models category with image understanding", 
        "cutoff": "2025-06"
    },
    "devstral-small-2507": {
        "company": "MistralAI",
        "provider": "MistralAI", 
        "model": "devstral-small-2507", 
        "input": 0.1 / 1000000,  # $0.10 / 1M tokens
        "output": 0.3 / 1000000,  # $0.30 / 1M tokens
        "context": 128000, 
        "modality_in": "Text", 
        "modality_out": "Text", 
        "functions": "Yes", 
        "description": "Open source coding model for codebase exploration and software engineering", 
        "cutoff": "2025-07"
    }
}

# Note: OCR and Moderation models have different pricing structures:
# - OCR: Priced per document/page, not per token
# - Moderation: Priced per request, not per token
# - Audio transcription: May have per-minute pricing in addition to token pricing

AiMistral.register_models("MistralAI")

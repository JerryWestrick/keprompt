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
 "mistral-medium-latest":      {"company": "MistralAI", "model": "mistral-medium-latest",     "input": 0.4 / 1000000, "output": 2 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "magistral-medium-latest":    {"company": "MistralAI", "model": "magistral-medium-latest",   "input": 2   / 1000000, "output": 5 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "mistral-large-latest":       {"company": "MistralAI", "model": "mistral-large-latest",      "input": 2   / 1000000, "output": 6 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "devstral-medium-latest":     {"company": "MistralAI", "model": "devstral-medium-latest",    "input": 0.4 / 1000000, "output": 2 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "codestral-latest":           {"company": "MistralAI", "model": "codestral-latest",          "input": 0.3 / 1000000, "output": 0.9 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "mistral-ocr-latest":         {"company": "MistralAI", "model": "mistral-ocr-latest",        "input": 1 / 1000, "output": 3 / 1000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "voxtral-mini-latest":        {"company": "MistralAI", "model": "voxtral-mini-latest",       "input": 0.002, "output": 0.0, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 
# Open Models
 "mistral-small-latest":       {"company": "MistralAI", "model": "mistral-small-latest",      "input": 0.1 / 1000000, "output": 0.3 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "magistral-small-latest":     {"company": "MistralAI", "model": "magistral-small-latest",    "input": 0.5 / 1000000, "output": 1.5 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "devstral-small-latest":      {"company": "MistralAI", "model": "devstral-small-latest",     "input": 0.1 / 1000000, "output": 0.3 / 1000000, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
 "voxtral-small-latest":       {"company": "MistralAI", "model": "voxtral-small-latest",      "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},


# Unknown Models
#  "ministral-3b-latest":        {"company": "MistralAI", "model": "ministral-3b-latest",       "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
#  "ministral-8b-latest":        {"company": "MistralAI", "model": "ministral-8b-latest",       "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
#  "mistral-saba-latest":        {"company": "MistralAI", "model": "mistral-saba-latest",       "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
#  "open-mistral-nemo":          {"company": "MistralAI", "model": "open-mistral-nemo",         "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
#  "pixtral-large-latest":       {"company": "MistralAI", "model": "pixtral-large-latest",      "input": 0.000000004, "output": 0.0000001, "context": 128000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "", "cutoff": "See Docs"},
}

AiRegistry.register_models_from_dict(model_definitions=Mistral_Models)

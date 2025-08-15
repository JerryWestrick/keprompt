from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedFunctions, DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiGoogle(AiProvider):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        request = {
            "contents": messages,
            "tools": [{"functionDeclarations": GoogleToolsArray}]
        }
        if self.system_message:
            request["system_instruction"] = {"parts": [{"text": self.system_message}]}
        return request

    def get_api_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.prompt.model}:generateContent?key={self.prompt.api_key}"

    def get_headers(self) -> Dict:
        return {"Content-Type": "application/json"}

    def to_ai_message(self, response: Dict) -> AiMessage:
        candidates = response.get("candidates", [])
        if not candidates:
            raise Exception("No response candidates received from Google API")

        content = []
        for part in candidates[0]['content']["parts"]:
            if   "text" in part:            content.append(AiTextPart(vm=self.prompt.vm, text=part["text"]))
            elif "functionCall" in part:
                fc = part["functionCall"]
                content.append(AiCall(vm=self.prompt.vm,name=fc["name"],arguments=fc.get("args", {}),id=fc.get("id", "")))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        google_messages = []

        for msg in messages:
            if msg.role == "system":
                self.system_message = msg.content[0].text if msg.content else None
                continue

            content = []
            for part in msg.content:
                if   part.type == "text":       content.append({"text": part.text})
                elif part.type == "image_url":  content.append({"inlineData": {"mimeType": part.media_type,"data": part.file_contents}})
                elif part.type == "call":       content.append({"functionCall": {"name": part.name,"args": json.loads(part.arguments)}})
                elif part.type == "result":     content.append({"functionResponse": {"name": part.name,"response": part.result,"id": part.id or ""}})
                else: raise Exception(f"Unknown part type: {part.type}")

            google_messages.append({"role": msg.role, "parts": content})

        return google_messages

    @classmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for Google (manual definitions only)"""
        console.print(f"[yellow]Google uses manual definitions to ensure system stability[/yellow]")
        cls._write_json_file(provider_name, Google_Models)


# Register handler and models
AiRegistry.register_handler(provider_name="Google", handler_class=AiGoogle)

# Google model definitions and pricing
# Official pricing source: https://ai.google.dev/pricing
# Last updated: January 2025
Google_Models = {
    # Latest Gemini 2.5 models
    "gemini-2.5-pro": {"company": "Google", "provider": "Google", "model": "gemini-2.5-pro", "input": 0.00000125, "output": 0.00001, "context": 1000000, "modality_in": "Text+Vision+Audio", "modality_out": "Text", "functions": "Yes", "description": "State-of-the-art multipurpose model, excels at coding and complex reasoning", "cutoff": "See docs"},
    "gemini-2.5-flash": {"company": "Google", "provider": "Google", "model": "gemini-2.5-flash", "input": 0.0000003, "output": 0.0000025, "context": 1000000, "modality_in": "Text+Vision+Audio", "modality_out": "Text", "functions": "Yes", "description": "First hybrid reasoning model with thinking budgets", "cutoff": "See docs"},
    "gemini-2.5-flash-lite": {"company": "Google", "provider": "Google", "model": "gemini-2.5-flash-lite", "input": 0.0000001, "output": 0.0000004, "context": 1000000, "modality_in": "Text+Vision+Audio", "modality_out": "Text", "functions": "Yes", "description": "Smallest and most cost effective model, built for at scale usage", "cutoff": "See docs"},
    
    # Gemini 2.0 models
    "gemini-2.0-flash": {"company": "Google", "provider": "Google", "model": "gemini-2.0-flash", "input": 0.0000001, "output": 0.0000004, "context": 1000000, "modality_in": "Text+Vision+Audio", "modality_out": "Text+Image", "functions": "Yes", "description": "Most balanced multimodal model, built for the era of Agents", "cutoff": "See docs"},
    "gemini-2.0-flash-lite": {"company": "Google", "provider": "Google", "model": "gemini-2.0-flash-lite", "input": 0.000000075, "output": 0.0000003, "context": 1000000, "modality_in": "Text", "modality_out": "Text", "functions": "Yes", "description": "Smallest and most cost effective model", "cutoff": "See docs"},
    
    # Legacy Gemini 1.5 models (still available)
    "gemini-1.5-pro": {"company": "Google", "provider": "Google", "model": "gemini-1.5-pro", "input": 0.00000125, "output": 0.000005, "context": 2000000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Highest intelligence Gemini 1.5 series model", "cutoff": "See docs"},
    "gemini-1.5-flash": {"company": "Google", "provider": "Google", "model": "gemini-1.5-flash", "input": 0.000000075, "output": 0.0000003, "context": 1000000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Fastest multimodal model with great performance", "cutoff": "See docs"},
    "gemini-1.5-flash-8b": {"company": "Google", "provider": "Google", "model": "gemini-1.5-flash-8b", "input": 0.0000000375, "output": 0.00000015, "context": 1000000, "modality_in": "Text+Vision", "modality_out": "Text", "functions": "Yes", "description": "Smallest model for lower intelligence use cases", "cutoff": "See docs"}

}

AiGoogle.register_models("Google")

# Prepare Google tools array
GoogleToolsArray = [
    {
        "name": tool['function']['name'],
        "description": tool['function']['description'],
        "parameters": {k: v for k, v in tool['function']['parameters'].items() if k != 'additionalProperties'}
    }
    for tool in DefinedToolsArray
]

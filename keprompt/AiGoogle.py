from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedFunctions, DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiGoogle(AiCompany):
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


# Register handler and models
AiRegistry.register_handler(company_name="Google", handler_class=AiGoogle)

Google_Models = {
    "gemini-2.0-flash-exp": {"company": "Google", "model": "gemini-2.0-flash-exp", "input": 0.000000, "output": 0.000000, "context": 8192},
    "gemini-1.5-flash": {"company": "Google", "model": "gemini-1.5-flash", "input": 0.000000, "output": 0.000000, "context": 8192},
    "gemini-1.5-flash-8b": {"company": "Google", "model": "gemini-1.5-flash-8b", "input": 0.000000, "output": 0.000000, "context": 8192}
}

AiRegistry.register_models_from_dict(model_definitions=Google_Models)

# Prepare Google tools array
GoogleToolsArray = [
    {
        "name": tool['function']['name'],
        "description": tool['function']['description'],
        "parameters": {k: v for k, v in tool['function']['parameters'].items() if k != 'additionalProperties'}
    }
    for tool in DefinedToolsArray
]
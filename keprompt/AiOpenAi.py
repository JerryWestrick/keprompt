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
                elif part.type == 'result':     tool_results= {'role': "tool", 'tool_call_id': part.id,'content': part.result}
                else:                           raise ValueError(f"Unknown part type: {part.type}")

            if msg.role == "tool":
                message = tool_results
            else:
                message = {"role": msg.role,"content": content[0]["text"] if len(content) == 1 else content}
                if tool_calls:
                    message["tool_calls"] = tool_calls

            openai_messages.append(message)

        return openai_messages


# Register handler and models
AiRegistry.register_handler(company_name="OpenAI", handler_class=AiOpenAi)

OpenAI_Models = {
    "gpt-4o-mini": {"company": "OpenAI", "model": "gpt-4o-mini", "input": 0.00000015, "output": 0.0000006, "context": 128000},
    "gpt-4o": {"company": "OpenAI", "model": "gpt-4o", "input": 0.000005, "output": 0.00002, "context": 128000},
    "gpt-4o-2024-05-13": {"company": "OpenAI", "model": "gpt-4o-2024-05-13", "input": 0.000005, "output": 0.000015, "context": 128000},
    "gpt-4o-mini-2024-07-18": {"company": "OpenAI", "model": "gpt-4o-mini-2024-07-18", "input": 0.00000015, "output": 0.0000006, "context": 128000},
    "gpt-4o-2024-08-06": {"company": "OpenAI", "model": "gpt-4o-2024-08-06", "input": 0.000005, "output": 0.00002, "context": 128000},
    "o1": {"company": "OpenAI", "model": "o1", "input": 0.000003, "output": 0.000012, "context": 128000},
    "o1-mini": {"company": "OpenAI", "model": "o1-mini", "input": 0.0000006, "output": 0.0000024, "context": 128000},
    "o3-mini": {"company": "OpenAI", "model": "o3-mini", "input": 0.0000011, "output": 0.0000044, "context": 128000}
}

AiRegistry.register_models_from_dict(model_definitions=OpenAI_Models)
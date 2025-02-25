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

Mistral_Models = {
    "mistral-large-latest": {"company": "MistralAI","model": "mistral-large-latest","input": 0.000002,"output": 0.000006,"context": 32000},
    "mistral-small-latest": {"company": "MistralAI","model": "mistral-small-latest","input": 0.0000002,"output": 0.0000006,"context": 32000},
    "codestral-latest":     {"company": "MistralAI","model": "codestral-latest",    "input": 0.0000003,"output": 0.0000009,"context": 32000},
    "ministral-8b-latest":  {"company": "MistralAI","model": "ministral-8b-latest", "input": 0.0000001,"output": 0.0000001,"context": 32000},
    "ministral-3b-latest":  {"company": "MistralAI","model": "ministral-3b-latest", "input": 0.00000004,"output": 0.00000004,"context": 32000},
    "pixtral-large-latest": {"company": "MistralAI","model": "pixtral-large-latest","input": 0.0000002,"output": 0.0000006,"context": 32000},
    "pixtral-12b":          {"company": "MistralAI","model": "pixtral-12b",         "input": 0.00000015,"output": 0.00000015,"context": 32000
    }
}

AiRegistry.register_models_from_dict(model_definitions=Mistral_Models)


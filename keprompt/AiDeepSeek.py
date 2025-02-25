from typing import Dict, List
import json
from rich.console import Console

from .AiRegistry import AiRegistry
from .AiCompany import AiCompany
from .AiPrompt import AiMessage, AiTextPart, AiCall, AiResult, AiPrompt
from .keprompt_functions import DefinedToolsArray

console = Console()
terminal_width = console.size.width


class AiDeepSeek(AiCompany):
    def prepare_request(self, messages: List[Dict]) -> Dict:
        return {
            "model": self.prompt.model,
            "messages": messages,
            "tools": DefinedToolsArray,
            "stream": False
        }

    def get_api_url(self) -> str:
        return "https://api.deepseek.com/v1/chat/completions"

    def get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.prompt.api_key}",
            "Content-Type": "application/json"
        }

    def to_ai_message(self, response: Dict) -> AiMessage:
        content = []
        choices = response.get("choices", [])
        if not choices:
            raise Exception("No response choices received from DeepSeek API")

        message = choices[0].get("message", {})
        msg_content = message.get("content", None)
        if isinstance(msg_content, str):
            if msg_content:
                content.append(AiTextPart(vm=self.prompt.vm, text=msg_content))
        else:
            for part in msg_content:
                content.append(AiTextPart(vm=self.prompt.vm, text=part["text"]))

        msg_content = message.get("tool_calls", [])
        for part in msg_content:
            fc = part["function"]
            content.append(AiCall(vm=self.prompt.vm,id=part["id"],name=fc["name"],arguments=fc["arguments"]))

        return AiMessage(vm=self.prompt.vm, role="assistant", content=content)

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        deepseek_messages = []

        for msg in messages:
            content = []
            tool_calls = []
            for part in msg.content:
                if   part.type == "text":       content.append({"type": "text", "text": part.text})
                elif part.type == "image_url":  content.append({'type': 'image','source': {'type': 'base64','media_type': part.media_type,'data': part.file_contents}})
                elif part.type == "call":       tool_calls.append({'type': 'function','id': part.id,'function': {'name':part.name, 'arguments':json.dumps(part.arguments)}})
                elif part.type == 'result':     deepseek_messages.append({"role": "tool", "tool_call_id": part.id, "content": part.result})
                else: raise Exception(f"Unknown part type: {part.type}")

            if msg.role == "system":
                deepseek_messages.append({"role": "user", "content": f"system: {content[0]['text']}"})
                continue

            if msg.role == "user" and content:
                cmsg = {"role": "user", "content": content }
                deepseek_messages.append(cmsg)
                continue

            if msg.role == "assistant" :
                cmsg = {"role": msg.role}
                if content:     cmsg = {"role": msg.role, "content": content}
                if tool_calls:  cmsg["tool_calls"] = tool_calls
                deepseek_messages.append(cmsg)
                continue


        return deepseek_messages


# Register handler and models
AiRegistry.register_handler(company_name="DeepSeek", handler_class=AiDeepSeek)

DeepSeek_Models = {
    "deepseek-chat":        {"company": "DeepSeek","model": "deepseek-chat",    "input": 0.00000014,"output": 0.00000028,"context": 65536},
    "deepseek-reasoner":    {"company": "DeepSeek","model": "deepseek-reasoner","input": 0.00000014,"output": 0.00000028,"context": 65536}
}

AiRegistry.register_models_from_dict(model_definitions=DeepSeek_Models)

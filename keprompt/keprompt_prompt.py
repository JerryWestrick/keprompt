import base64
import json
import mimetypes
from abc import ABC, abstractmethod
from typing import List, Optional, Union

import keyring
import requests
from rich.console import Console
from rich.progress import Progress, TimeElapsedColumn

from keprompt.keprompt_functions import (
    DefinedToolsArray,
    GoogleToolsArray,
    AnthropicToolsArray,
)

# Global Variables
console = Console()
TERMINAL_WIDTH = console.size.width
COMPANIES_WITH_API_KEY = [
    "Anthropic",
    "Google",
    "MistralAI",
    "OpenAI",
    "XAI",
    "DeepSeek",
    "Groq",
]


class APIKeyError(Exception):
    """Custom exception for API key related errors."""


class AiMessagePart(ABC):
    def __init__(self, vm, part_type: str):
        self.type = part_type
        self.vm = vm

    @abstractmethod
    def to_json(self, company: str) -> dict:
        pass


class AiTextPart(AiMessagePart):
    def __init__(self, vm, text: str):
        super().__init__(vm=vm, part_type="text")
        self.text = text

    def to_json(self, company: str) -> dict:
        text = self.vm.substitute(self.text)
        if company == "Google":
            return {"text": text}
        return {"type": "text", "text": text}

    def __str__(self) -> str:
        return f"Text(text={self.vm.substitute(self.text)})"

    def __repr__(self) -> str:
        return f"Text(text={self.text!r})"


class AiImagePart(AiMessagePart):
    def __init__(self, vm, filename: str):
        super().__init__(vm=vm, part_type="image_url")
        self.filename = vm.substitute(filename)

        try:
            with open(self.filename, "rb") as file:
                self.file_contents = base64.b64encode(file.read()).decode()
        except FileNotFoundError:
            console.print(f"[bold red]File not found: {self.filename}[/bold red]")
            raise
        except IOError as e:
            console.print(f"[bold red]IOError: {e}[/bold red]")
            raise

        self.media_type, _ = mimetypes.guess_type(self.filename) or ("application/octet-stream",)

    def __str__(self) -> str:
        return f"Image(filename={self.filename}, media_type={self.media_type})"

    def __repr__(self) -> str:
        return f"Image(filename={self.filename!r}, media_type={self.media_type!r})"

    def to_json(self, company: str) -> dict:
        base64_data = f"data:{self.media_type};base64,{self.file_contents}"
        if company == "Anthropic":
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.media_type,
                    "data": self.file_contents,
                },
            }
        elif company == "Google":
            return {"inline_data": {"mime_type": self.media_type, "data": self.file_contents}}
        elif company == "MistralAI":
            return {"type": "image_url", "image_url": base64_data}
        # Default case
        return {"type": "image_url", "image_url": {"url": base64_data}}


class AiCall(AiMessagePart):
    def __init__(
            self,
            vm,
            name: str,
            arguments: str,
            id: Optional[str] = None,
    ):
        super().__init__(vm=vm, part_type="call")
        self.name = name
        self.id = id
        self.arguments = arguments

    def __str__(self) -> str:
        return f"Call(name={self.name}, id={self.id}, arguments={self.arguments})"

    def __repr__(self) -> str:
        return f"Call(name={self.name!r}, id={self.id!r}, arguments={self.arguments!r})"

    def to_json(self, company: str) -> dict:
        function_call = {"name": self.name, "arguments": self.arguments}
        if company == "Anthropic":
            return {
                "type": "tool_use",
                "id": self.id,
                "name": self.name,
                "input": self.arguments,
            }
        elif company == "Google":
            return {"functionCall": function_call}
        elif company in ["OpenAI", "DeepSeek"]:
            return {
                "type": "function",
                "id": self.id,
                "name": self.name,
                "arguments": self.arguments,
            }
        elif company in ["MistralAI"]:
            return {
                "id": self.id,
                "type": "function",
                "function": function_call
            }
        elif company == "XAI":
            return {
                "id": self.id,
                "function": {"type": "function", "name": self.name, "arguments": self.arguments},
            }
        else:
            raise ValueError(f"Unknown Company Value: {company}")


class AiResult(AiMessagePart):
    def __init__(self, vm, name: str, id: str, result: str):
        super().__init__(vm=vm, part_type="result")
        self.name = name
        self.id = id
        self.result = result

    def __str__(self) -> str:
        return f"Result(name={self.name}, id={self.id}, content={self.result})"

    def __repr__(self) -> str:
        return f"ToolResult(name={self.name!r}, id={self.id!r}, content={self.result!r})"

    def to_json(self, company: str) -> dict:
        if company == "Anthropic":
            return {"type": "tool_result", "tool_use_id": self.id, "content": self.result}
        elif company == "Google":
            return {
                "functionResponse": {
                    "name": self.name,
                    "response": {"text": self.result},
                }
            }
        elif company in ["MistralAI", "OpenAI", "DeepSeek", "XAI"]:
            role = "tool" if company in ["MistralAI", "XAI", "DeepSeek", "OpenAI"] else "user"
            return {"role": role, "tool_call_id": self.id, "content": self.result}
        else:
            raise ValueError(f"Unknown Company Value: {company}")


class AiMessage:
    def __init__(
            self,
            vm,
            role: str,
            content: Optional[List[AiMessagePart]] = None,
            tool_calls: Optional[List[AiCall]] = None,
    ):
        self.role = role
        self.content: List[AiMessagePart] = content or []
        self.tool_calls: List[AiCall] = tool_calls or []
        self.vm = vm

    def __str__(self) -> str:
        return f"Message(role={self.role}, content={self.content}, tool_calls={self.tool_calls})"

    def __repr__(self) -> str:
        content_repr = ",\n\t".join(str(part) for part in self.content)
        tool_calls_repr = ", ".join(str(call) for call in self.tool_calls)
        return f"Message(role={self.role!r}, content=[\n\t{content_repr}\n\t], tool_calls=[{tool_calls_repr}])\n"

    def to_json(self, company: str) -> Union[dict, List[dict]]:
        if company == "Anthropic":
            return self._to_json_anthropic()
        elif company == "Google":
            return self._to_json_google()
        elif company == "MistralAI":
            return self._to_json_mistralai()
        elif company in ["OpenAI", "DeepSeek"]:
            return self._to_json_openai_deepseek()
        elif company == "Groq":
            return self._to_json_groq()
        elif company == "XAI":
            return self._to_json_xai()
        else:
            raise ValueError(f"Unknown company: {company}")

    def _to_json_anthropic(self) -> dict:
        if self.role == "system" and isinstance(self.content[0], AiTextPart):
            system_message = self.content[0]
            return {"role": self.role, "content": system_message.text}

        content_json = [part.to_json("Anthropic") for part in self.content]

        if self.role == "assistant" and self.tool_calls:
            tool_calls_json = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ]
            return {"role": "assistant", "content": content_json, "tool_calls": tool_calls_json}

        if self.role == "result":
            return {"role": "user", "content": content_json}

        return {"role": self.role, "content": content_json}

    def _to_json_google(self) -> dict:
        role_mapping = {"assistant": "model", "result": "user"}
        role = role_mapping.get(self.role, self.role)
        content_json = [part.to_json("Google") for part in self.content]
        return {"role": role, "parts": content_json}

    def _to_json_mistralai(self) -> dict:
        if self.role == "assistant":
            if self.tool_calls:
                tool_calls_json = [call.to_json("MistralAI") for call in self.tool_calls]
                return {"role": "assistant", "content": None, "tool_calls": tool_calls_json}

            content_json = [{"type": "text", "text": cast_AiTextPart(part).text} for part in self.content]
            return {"role": self.role, "content": content_json}

        if self.role == "result":
            result = cast_AiResult(self.content[0])
            return {"role": "tool", "name": result.name, "tool_call_id": result.id, "content": result.result}

        content_json = [part.to_json("MistralAI") for part in self.content]
        return {"role": self.role, "content": content_json}

    def _to_json_openai_deepseek(self) -> dict:
        if self.role == "assistant" and self.tool_calls:
            content_json = [part.to_json("OpenAI") for part in self.content]
            tool_calls_json = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ]
            return {"role": "assistant", "content": content_json or None, "tool_calls": tool_calls_json}

        if self.content[0] and isinstance(self.content[0], AiResult):
            return [
                {
                    "role": "tool",
                    "tool_call_id": cast_AiResult(part).id,
                    "content": json.dumps(part.result),
                }
                for part in self.content
            ]

        content_json = [part.to_json("OpenAI") for part in self.content]
        return {"role": self.role, "content": content_json}

    def _to_json_groq(self) -> dict:
        if self.role == "assistant" and self.tool_calls:
            content_json = [part.to_json("Groq") for part in self.content]
            tool_calls_json = [call.to_json("Groq") for call in self.tool_calls]
            return {"role": "assistant", "content": content_json, "tool_calls": tool_calls_json}

        if isinstance(self.content[0], AiResult):
            return [
                {
                    "role": "tool",
                    "name": cast_AiResult(part).name,
                    "tool_call_id": part.id,
                    "content": json.dumps(part.result),
                }
                for part in self.content
            ]

        if self.role == "system":
            system_message = cast_AiTextPart(self.content[0])
            return {"role": self.role, "content": system_message.text}

        content_json = [part.to_json("Groq") for part in self.content]
        return {"role": self.role, "content": content_json}

    def _to_json_xai(self) -> dict:
        if self.role == "system":
            system_message = cast_AiTextPart(self.content[0])
            return {"role": self.role, "content": system_message.text}

        if self.role == "assistant":
            content_json = [part.to_json("XAI") for part in self.content]
            tool_calls_json = [call.to_json("XAI") for call in self.tool_calls]
            return {"role": "assistant", "content": content_json, "tool_calls": tool_calls_json}

        if self.role == "result":
            result = cast_AiResult(self.content[0])
            return {"role": "tool", "tool_call_id": result.id, "content": result.result}

        content_json = [part.to_json("XAI") for part in self.content]
        return {"role": self.role, "content": content_json, "tool_calls": None}


def cast_AiTextPart(part: AiMessagePart) -> AiTextPart:
    if not isinstance(part, AiTextPart):
        raise TypeError("Expected AiTextPart")
    return part


def cast_AiResult(part: AiMessagePart) -> AiResult:
    if not isinstance(part, AiResult):
        raise TypeError("Expected AiResult")
    return part


class AiPrompt:
    def __init__(self, vm):
        self.messages: List[AiMessage] = []
        self.system_message: Optional[str] = None
        self.toks_in: int = 0
        self.toks_out: int = 0
        self.company: str = ""
        self.model: str = ""
        self.api_key: str = ""
        self.vm = vm

    def add_message(
            self,
            vm,
            role: str,
            content: Optional[List[AiMessagePart]] = None,
            tool_calls: Optional[List[AiCall]] = None,
    ):
        content = content or []
        tool_calls = tool_calls or []

        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content.extend(content)
            self.messages[-1].tool_calls.extend(tool_calls)
        else:
            self.messages.append(AiMessage(vm=self.vm, role=role, content=content, tool_calls=tool_calls))

    def to_json(self) -> List[dict]:
        """Generate JSON serializable object for API company-specific request."""
        json_msgs: List[dict] = []
        for msg in self.messages:
            json_data = msg.to_json(company=self.company)
            if isinstance(json_data, list):
                json_msgs.extend(json_data)
            else:
                json_msgs.append(json_data)

        if self.company == "Anthropic" and json_msgs and json_msgs[0]["role"] == "system":
            self.system_message = json_msgs.pop(0)["content"]

        if self.company == "Google" and json_msgs and json_msgs[0]["role"] == "system":
            self.system_message = json_msgs.pop(0)["parts"][0]["text"]

        return json_msgs

    def ask(self, label: str) -> AiMessage:
        """Make a prompt to self.company::self.model and process the result."""
        if self.company in COMPANIES_WITH_API_KEY:
            self.api_key = get_api_key(company=self.company)
        else:
            self.api_key = ""

        request_params = self.make_request_params()

        if self.vm.debug:
            console.print("[bold yellow]Sending to API...[/bold yellow]")

        # self.log_api_json(request_params, )
        with Progress(
                "[progress.description]{task.description}",
                TimeElapsedColumn(),
                console=console,
                transient=True,
        ) as progress:
            task = progress.add_task(label, total=None)
            response = requests.post(**request_params)
            progress.update(task, description=label)

        if response.status_code != 200:
            err_msg = f"API Request failed with status code {response.status_code}: {response.text}"
            d = json.loads(request_params['data'])
            self.vm.log_last_json(d['messages'])
            raise APIKeyError(err_msg)

        try:
            response_data = response.json()
        except json.JSONDecodeError as err:
            console.print(f"[bold red]Error decoding JSON: {err.msg}[/bold red]")
            console.print(f"[bold red]Raw response: {response.text}[/bold red]")
            raise

        if self.vm.debug:
            console.print("[bold green]Received from API:[/bold green]")
            clean_data = self.clean_messages(response_data)
            console.print_json(json.dumps(clean_data, indent=2))

        return self._process_response(response_data)

    def _process_response(self, data: dict) -> AiMessage:
        msg_parts: List[AiMessagePart] = []
        company = self.company

        if company == "Anthropic":
            self.toks_out += data.get("usage", {}).get("output_tokens", 0)
            self.toks_in += data.get("usage", {}).get("input_tokens", 0)

            role = data.get("role")
            contents = data.get("content", [])

            if isinstance(contents, str):
                contents = [contents]

            for msg in contents:
                if isinstance(msg, str):
                    msg_parts.append(AiTextPart(vm=self.vm, text=msg))
                elif isinstance(msg, dict):
                    if msg.get("type") == "text":
                        msg_parts.append(AiTextPart(vm=self.vm, text=msg.get("text", "")))
                    elif msg.get("type") == "tool_use":
                        msg_parts.append(
                            AiCall(
                                vm=self.vm,
                                name=msg.get("name", ""),
                                arguments=msg.get("input", ""),
                                id=msg.get("id"),
                            )
                        )

            return AiMessage(vm=self.vm, role=role, content=msg_parts)

        elif company == "Google":
            self.toks_out += data.get("usageMetadata", {}).get("candidatesTokenCount", 0)
            self.toks_in += data.get("usageMetadata", {}).get("promptTokenCount", 0)

            candidates = data.get("candidates", [])
            if not candidates:
                raise APIKeyError("No content found in the response.")

            llm_msg = candidates[0].get("content", {})
            role = llm_msg.get("role")
            parts = llm_msg.get("parts", [])

            for part in parts:
                if "text" in part:
                    msg_parts.append(AiTextPart(vm=self.vm, text=part["text"]))
                elif "functionCall" in part:
                    msg_parts.append(
                        AiCall(
                            vm=self.vm,
                            name=part["functionCall"].get("name", ""),
                            arguments=part["functionCall"].get("args", ""),
                        )
                    )
                else:
                    console.print(f"[red]Unexpected response type: {part.keys()}[/red]")
                    raise APIKeyError("Unexpected response structure from Google.")

            return AiMessage(vm=self.vm, role=role, content=msg_parts)

        elif company in ["MistralAI", "OpenAI", "XAI", "DeepSeek"]:
            self.toks_out += data.get("usage", {}).get("completion_tokens", 0)
            self.toks_in += data.get("usage", {}).get("prompt_tokens", 0)

            choices = data.get("choices", [])
            if not choices:
                raise APIKeyError("No content found in the response.")

            llm_msg = choices[0].get("message", {})
            role = llm_msg.get("role")
            parts = llm_msg.get("content") or []

            if not isinstance(parts, list):
                parts = [parts]

            for part in parts:
                if isinstance(part, str) and part:
                    msg_parts.append(AiTextPart(vm=self.vm, text=part))
                elif isinstance(part, dict) and part.get("text"):
                    msg_parts.append(AiTextPart(vm=self.vm, text=part["text"]))
                else:
                    console.print(f"[red]Unexpected response type: {type(part)}[/red]")
                    raise APIKeyError("Unexpected response structure from the company.")

            tool_calls = []
            if "tool_calls" in llm_msg and llm_msg["tool_calls"]:
                for fc in llm_msg["tool_calls"]:
                    tool_calls.append(
                        AiCall(
                            vm=self.vm,
                            name=fc["function"]["name"],
                            arguments=fc["function"]["arguments"],
                            id=fc["id"],
                        )
                    )

            return AiMessage(vm=self.vm, role=role, content=msg_parts, tool_calls=tool_calls)

        else:
            raise APIKeyError(f"Unknown company: {company}")

    def clean_messages(self, data: dict) -> dict:
        sensitive_keys = {"url", "data", "image_url"}

        def recursive_clean(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in sensitive_keys and isinstance(v, str):
                        d[k] = "..."
                    else:
                        recursive_clean(v)
            elif isinstance(d, list):
                for item in d:
                    recursive_clean(item)

        recursive_clean(data)
        return data

    def make_request_params(self) -> dict:
        data = {
            "model": self.model,
            "messages": self.to_json(),
            "tools": DefinedToolsArray,
        }
        headers = {"Content-Type": "application/json"}

        match self.company:
            case "Anthropic":
                data.update({"max_tokens": 1024})
                data["tools"] = AnthropicToolsArray
                url = "https://api.anthropic.com/v1/messages"
                headers.update(
                    {
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    }
                )
            case "Google":
                data.update(
                    {
                        "contents": self.to_json(),
                        "system_instruction": {"parts": [{"text": self.system_message}]},
                        "tools": [{"functionDeclarations": GoogleToolsArray}],
                    }
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            case "Groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers.update({"Authorization": f"Bearer {self.api_key}"})
            case "MistralAI":
                url = "https://api.mistral.ai/v1/chat/completions"
                headers.update({"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"})
            case "OpenAI":
                url = "https://api.openai.com/v1/chat/completions"
                headers.update({"Authorization": f"Bearer {self.api_key}"})
            case "DeepSeek":
                data.update({"stream": False})
                url = "https://api.deepseek.com/v1/chat/completions"
                headers.update({"Authorization": f"Bearer {self.api_key}"})
            case "XAI":
                data.update({"too_choice": "auto"})
                url = "https://api.x.ai/v1/chat/completions"
                headers.update({"Authorization": f"Bearer {self.api_key}"})
            case _:
                raise APIKeyError(f"Unknown company: {self.company}")

        json_data = json.dumps(data)

        request_params = {
            "url": url,
            "headers": headers,
            "data": json_data,
        }

        if self.vm.debug:
            console.print("[bold cyan]Sending the following request data:[/bold cyan]")
            clean_data = self.clean_messages(data)
            console.print_json(json.dumps(clean_data, indent=2))

        return request_params


def get_api_key(company: str) -> str:
    try:
        api_key = keyring.get_password("keprompt", username=company)
    except keyring.errors.PasswordDeleteError:
        console.print(f"[bold red]Error accessing keyring for company: {company}[/bold red]")
        raise APIKeyError("Unable to access the keyring.")

    if not api_key:
        api_key = console.input(f"Please enter your {company} API key: ")
        if not api_key:
            console.print("[bold red]API key cannot be empty.[/bold red]")
            raise APIKeyError("API key cannot be empty.")
        keyring.set_password("keprompt", username=company, password=api_key)

    return api_key

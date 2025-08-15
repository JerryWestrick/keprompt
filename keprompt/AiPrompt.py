import base64
import json
import mimetypes
from abc import ABC, abstractmethod
from typing import List, Optional
import keyring
from rich.console import Console

from .AiRegistry import AiRegistry
from .keprompt_util import HORIZONTAL_LINE, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT, VERTICAL

# Global Variables
console = Console()
TERMINAL_WIDTH = console.size.width
MAX_LINE_LENGTH = TERMINAL_WIDTH - 30
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
    def to_json(self) -> dict:
        pass

    @abstractmethod
    def print_message(self) -> str :
        pass


class AiTextPart(AiMessagePart):
    def __init__(self, vm, text: str):
        super().__init__(vm=vm, part_type="text")
        self.text = text

    def substitute(self) -> str:
        return self.vm.substitute(self.text)

    def to_json(self) -> dict:
        text = self.vm.substitute(self.text)
        return {"type": "text", "text": text}

    def __str__(self) -> str:
        return f"Text(text={self.vm.substitute(self.text)})"

    def __repr__(self) -> str:
        return f"Text(text={self.text!r})"

    def print_message(self) -> str:
        txt = self.vm.substitute(self.text)
        txt = self.substitute().replace('\n', '\\n')
        if len(txt) > MAX_LINE_LENGTH:
            txt = txt[:MAX_LINE_LENGTH] + '...'
        return f"Text({txt})"

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

    def to_json(self) -> dict:
        base64_data = f"data:{self.media_type};base64,{self.file_contents}"
        return {"type": "image_url", "image_url": {"url": base64_data}}

    def print_message(self) -> str:
        return f"Image(name='{self.filename}', data=...)"


class AiCall(AiMessagePart):
    def __init__(self, vm, name: str, arguments: dict, id: Optional[str] = None, ):
        super().__init__(vm=vm, part_type="call")
        self.name = name
        self.id = id
        self.arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
            
    def __str__(self) -> str:
        return f"Call(name={self.name}, id={self.id}, arguments={self.arguments})"

    def __repr__(self) -> str:
        return f"Call(name={self.name!r}, id={self.id!r}, arguments={self.arguments!r})"

    def to_json(self) -> dict:
        return {
            "type": "tool",
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    def print_message(self) -> str:
        targs = {}
        for k,v in self.arguments.items():
            if len(v) > 25:
                targs[k] = v[:25] + '...'
            else:
                targs[k]=v
        args = json.dumps(targs)
        args = args.replace('\n', '\\n')
        return f"Call {self.name}(id={self.id}, {args[1:-1]})"


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

    def to_json(self) -> dict:
        return {"type": "tool_result", "tool_use_id": self.id, "content": self.result}

    def print_message(self) -> str:
        replaced = self.result.replace('\n', '\\n')
        if len(replaced) > MAX_LINE_LENGTH:
            replaced = replaced[:MAX_LINE_LENGTH] + '...'
        return f"Rtn  {self.name}(id={self.id}, content:{replaced})"


class AiMessage:
    def __init__(self, vm, role: str, content=None):
        if content is None:
            content = []
        self.role = role
        self.content: List[AiMessagePart] = content
        self.vm = vm

    def __str__(self) -> str:
        return f"Message(role={self.role}, content={self.content})"

    def __repr__(self) -> str:
        content_repr = ",\n\t".join(str(part) for part in self.content)
        return f"Message(role={self.role!r}, content=[\n\t{content_repr}\n\t])\n"

    def to_json(self) -> dict:
        content = [part.to_json() for part in self.content]
        return json.loads(json.dumps({"role": self.role, "content": content}))

    def print_message(self) -> str:
        content = ''
        for t in self.content:
            content += t.print_message()
        return f"{self.role:<10} [{content}]"


class AiPrompt:
    def __init__(self, vm):
        self.messages: List[AiMessage] = []
        self.system_message: Optional[str] = None
        self.toks_in: int = 0
        self.toks_out: int = 0
        self.provider: str = ""
        self.model: str = ""
        self.api_key: str = ""
        self.vm = vm

    def print_messages(self, lbl:str):
        l = 1 + len(lbl)
        console.print(f"\n[white]{VERTICAL}[/][blue]{TOP_LEFT}{HORIZONTAL_LINE * 3} Messages {lbl} {HORIZONTAL_LINE * (TERMINAL_WIDTH - 17 - l)}{TOP_RIGHT}[/][white]{VERTICAL}[/]")
        for msg in self.messages:
            role = f"{msg.role:<10}"
            content:str = ''

            header = f"[white]{VERTICAL}[/][blue]{VERTICAL}[/] [green]{role}[/]"
            for p in msg.content:
                content = p.print_message()
                used = TERMINAL_WIDTH - len(content) - len(role) - 6
                console.print(f"{header}{content} {' ' * used}[blue]{VERTICAL}[/][white]{VERTICAL}[/]")
                header = f"[white]{VERTICAL}[/][blue]{VERTICAL}[/] [green]          [/]"

        console.print(
            f"[white]{VERTICAL}[/][blue]{BOTTOM_LEFT}{HORIZONTAL_LINE * (TERMINAL_WIDTH - 4)}{BOTTOM_RIGHT}[/][white]{VERTICAL}[/]")

    def add_message(self, vm, role: str, content: Optional[List[AiMessagePart]] = None):
        content = content or []

        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content.extend(content)
        else:
            self.messages.append(AiMessage(vm=self.vm, role=role, content=content))

    def to_json(self) -> List[dict]:
        """Generate JSON serializable object."""
        json_msgs: List[dict] = []
        for msg in self.messages:
            json_data = msg.to_json()
            if isinstance(json_data, list):
                json_msgs.extend(json_data)
            else:
                json_msgs.append(json_data)

        return json_msgs

    def ask(self, label: str, call_id: str = None) -> AiMessage:
        """Make a prompt to self.company::self.model and process the result."""

        # Store call_id for AiCompany to access
        self._current_call_id = call_id

        # if 'LLM' in self.vm.debug:
        #     console.print("[bold yellow]Sending to API...[/bold yellow]")

        handler = AiRegistry.create_handler(prompt=self)

        if not handler:
            raise ValueError(f"No handler registered for {self.provider}")

        retval = handler.call_llm(label=label)

        return retval

    def _process_response(self, data: dict) -> AiMessage:
        msg_parts: List[AiMessagePart] = []
        company = self.provider

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

            # Process tool_calls and add them to msg_parts
            if "tool_calls" in llm_msg and llm_msg["tool_calls"]:
                for fc in llm_msg["tool_calls"]:
                    msg_parts.append(
                        AiCall(
                            vm=self.vm,
                            name=fc["function"]["name"],
                            arguments=fc["function"]["arguments"],
                            id=fc["id"],
                        )
                    )

            return AiMessage(vm=self.vm, role=role, content=msg_parts)

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

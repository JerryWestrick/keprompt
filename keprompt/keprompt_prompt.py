import base64
import json
import mimetypes
import pprint
import typing
from abc import ABC, abstractmethod
from json import JSONDecodeError
from typing import List

import keyring
import keyring.errors  # Ensure keyring.errors is explicitly imported for clarity
import requests
from rich.console import Console
from rich.progress import Progress, TimeElapsedColumn

from keprompt.keprompt_functions import DefinedToolsArray, GoogleToolsArray, AnthropicToolsArray

# Global Variables
console = Console()
terminal_width = console.size.width
companies_with_api_key = ["Anthropic", "Google", "MistralAI", "OpenAI", "XAI", "DeepSeek", "Groq"]

def get_api_key(company: str) -> str:
    try:
        api_key = keyring.get_password('keprompt', username=company)
    except keyring.errors.PasswordDeleteError:
        console.print(f"[bold red]Error accessing keyring ('keprompt', username={company})[/bold red]")
        api_key = None

    if api_key is None:
        api_key = console.input(f"Please enter your {company} API key: ")
        keyring.set_password("keprompt", username=company, password=api_key)

    if not api_key:
        console.print("[bold red]API key cannot be empty.[/bold red]")
        raise ValueError("API key cannot be empty.")

    return api_key


class AiMessagePart(ABC):

    def __init__(self, vm, part_type: str):
        self.type = part_type
        self.vm=vm

    @abstractmethod
    def to_json(selfmessages, company):
        pass


class AiTextPart(AiMessagePart):
    def __init__(self, vm, text: str):
        super().__init__(vm=vm, part_type="text")
        self.text = text

    def to_json(self, company: str):
        text = self.vm.substitute(self.text)
        if company == 'Google':
            return {"text": text}

        return {"type": "text", "text": text}

    def __str__(self):
        return f"Text(text={self.vm.substitute(self.text)}))"

    def __repr__(self):
        return f"Text(text={self.text!r})"


class AiImagePart(AiMessagePart):

    def __init__(self, vm, filename: str):
        super().__init__(vm=vm, part_type="image_url")
        temp = vm.substitute(filename)
        self.filename = temp

        """ Read a binary file from local disk and encode it as base64."""
        with open(self.filename, 'rb') as file:
            self.file_contents = base64.b64encode(file.read()).decode()
        self.media_type, _ = mimetypes.guess_type(self.filename)

    def __str__(self):
        return f"Image(filename={self.filename}, media_type={self.media_type})"

    def __repr__(self):
        return f"Image(filename={self.filename!r}, media_type={self.media_type!r})"

    def to_json(self, company: str):

        if company == 'Anthropic':
            return {"type": "image",
                    "source": {"type": "base64", "media_type": self.media_type, "data": self.file_contents}}

        if company == 'Google':
            return {"inline_data": {"mime_type": self.media_type, "data": self.file_contents}}

        if company == 'MistralAI':
            return {"type": "image_url", "image_url": f"data:{self.media_type};base64,{self.file_contents}"}

        # others/default
        return {"type": "image_url", "image_url": {"url": f"data:image/{self.media_type};base64,{self.file_contents}"}}


class AiCall(AiMessagePart):
    def __init__(self, vm, name: str, arguments: str, id: str | None = None):
        super().__init__(vm=vm, part_type="call")
        self.name = name
        self.id = id
        self.arguments = arguments

    def __str__(self):
        return f"Call(name={self.name}, id={self.id}, arguments={self.arguments})"

    def __repr__(self):
        return f"Call(name={self.name!r}, id={self.id!r}, arguments={self.arguments!r})"

    def to_json(self, company: str):

        match company:
            case 'Anthropic':
                return {"type": "tool_use", "id": self.id, "name": self.name, "input": self.arguments}

            case 'Google':
                return {"functionCall": {"name": self.name, "args": self.arguments}}

            case 'MistralAI':
                return {"type": "function", "id": self.id, "function": {"name": self.name, "arguments": self.arguments}}

            case 'OpenAI':
                return {"type": "function", "name": self.name, "id": self.id, "arguments": self.arguments}

            case 'DeepSeek':
                return {"type": "function", "name": self.name, "id": self.id, "arguments": self.arguments}

            case 'XAI':
                return {'id': self.id, "function": {"type": "function", "name": self.name, "arguments": self.arguments}}

            case _:
                raise ValueError(f"Unknown Company Value: {company}")


class AiResult(AiMessagePart):
    def __init__(self, vm, name: str, id: str, result: str):
        super().__init__(vm=vm, part_type="result")
        self.name = name
        self.id = id
        self.result = result

    def __str__(self):
        return f"Result(name={self.name}, id={self.id}, content={self.result})"

    def __repr__(self):
        return f"ToolResult(name={self.name!r}, id={self.id!r}, content={self.result!r})"

    def to_json(self, company: str):
        match company:
            case 'Anthropic':
                return {"type": "tool_result", "tool_use_id": self.id, "content": self.result}

            case 'Google':
                return {"functionResponse": {"name": self.name, "response": {"text": self.result}}}

            case 'MistralAI':
                return {"role": "tool", "id": self.id, "name": self.name, "content": self.result}

            case "XAI" | "DeepSeek" | "OpenAI":
                return {"role": "tool", "tool_call_id": self.id, "content": self.result}

            case _:
                raise ValueError(f"Unknown Company Value: {company}")


class AiMessage:
    def __init__(self, vm, role: str, content: list[AiMessagePart] = None, tool_calls: List[AiCall] = None):
        if content is None: content = []
        if tool_calls is None: tool_calls = []
        self.role = role
        assert (content is not None)
        assert (type(content) is list)
        self.content: List[AiMessagePart] = content
        self.tool_calls: List[AiCall] = tool_calls
        self.vm = vm

    def __str__(self):
        return f"Message(role={self.role}, content={self.content}, tool_calls={self.tool_calls})"

    def __repr__(self):
        r = f"Message(role={self.role!r}, content= [\n"
        for part in self.content:
            r += f"\t{str(part).replace('\n', '\\n')}\n"
        r += "\t],"
        r += f" tool_calls={self.tool_calls}))\n"
        return r

    def to_json(self, company: str):

        c = []
        t = []
        match company:
            case 'Anthropic':
                if self.role == 'system' and type(self.content[0]) is AiTextPart:
                    system_message: AiTextPart = typing.cast(AiTextPart, self.content[0])
                    return {"role": self.role, "content": system_message.text}

                c = []
                for p in self.content:
                    c.append(p.to_json(company=company))

                if self.role == 'assistant' and self.tool_calls:
                    c = []
                    for p in self.content:
                        c.append(p.to_json(company=company))

                    for p in self.tool_calls:
                        t.append(
                            {"id": p.id, "type": "function",
                             "function": {"name": p.name, "arguments": p.arguments}})

                    return {"role": "assistant", "content": c, "tool_calls": t}

                if self.role == 'result':
                    return {"role": "user", "content": c}

                return {"role": self.role, "content": c}

            case "Google":
                role = self.role
                match role:
                    case 'assistant':
                        role = 'model'
                    case 'result':
                        role = 'user'

                for p in self.content:
                    c.append(p.to_json(company=company))

                return {"role": role, "parts": c}

            case "MistralAI":
                match self.role:
                    case 'assistant':
                        if self.tool_calls:
                            for p in self.tool_calls:
                                t.append(p.to_json(company=company))
                            return {"role": "assistant", "content": None, "tool_calls": t}

                        if self.content:
                            for p in self.content:
                                p = typing.cast(AiTextPart, p)
                                c.append({"type": "text", "text": p.text})
                            return {"role": self.role, "content": c}

                    case 'result':
                        p = self.content[0]
                        p = typing.cast(AiResult, p)
                        return {"role": "tool", "name": p.name, "tool_call_id": p.id, "content": p.result}

                    case _:
                        for p in self.content:
                            c.append(p.to_json(company=company))
                        return {"role": self.role, "content": c}

            case "OpenAI" | "DeepSeek":

                if self.role == 'assistant' and self.tool_calls:
                    c = []
                    for p in self.content:
                        c.append(p.to_json(company=company))

                    for p in self.tool_calls:
                        t.append(
                            {"id": p.id, "type": "function", "function": {"name": p.name, "arguments": p.arguments}})

                    return {"role": "assistant", "content": c, "tool_calls": t}

                if type(self.content[0]) == AiResult:
                    for p in self.content:
                        if type(p) is not AiResult:
                            raise ValueError(f"A function return with a part that in not a AiToolResult")
                        p = typing.cast(AiResult, p)
                        c.append({"role": "tool", "name": p.name, "tool_call_id": p.id, "content": json.dumps(p.result)})
                    return c

                c = []
                for p in self.content:
                    c.append(p.to_json(company=company))
                return {"role": self.role, "content": c}

            case "Groq":

                if self.role == 'assistant' and self.tool_calls:
                    c = []
                    for p in self.content:
                        c.append(p.to_json(company=company))

                    for p in self.tool_calls:
                        t.append(
                            {"id": p.id, "type": "function", "function": {"name": p.name, "arguments": p.arguments}})

                    return {"role": "assistant", "content": c, "tool_calls": t}

                if type(self.content[0]) == AiResult:
                    for p in self.content:
                        if type(p) is not AiResult:
                            raise ValueError(f"A function return with a part that in not a AiToolResult")
                        p = typing.cast(AiResult, p)
                        c.append({"role": "tool", "name": p.name, "tool_call_id": p.id, "content": json.dumps(p.result)})
                    return c

                if self.role == 'system':
                    system_message: AiTextPart = typing.cast(AiTextPart, self.content[0])
                    return {"role": self.role, "content": system_message.text}

                c = []
                for p in self.content:
                    c.append(p.to_json(company=company))

                return {"role": self.role, "content": c}

            case "XAI":
                match self.role:
                    case "system":
                        # Assumes message is a AiTextPart, but that may not be true
                        system_message: AiTextPart = typing.cast(AiTextPart, self.content[0])
                        return {"role": self.role, "content": system_message.text}

                    case "assistant":
                        c = []
                        if self.content:
                            for p in self.content:
                                c.append(p.to_json(company=company))

                        if self.tool_calls:
                            for p in self.tool_calls:
                                t.append(p.to_json(company=company))

                        return {"role": "assistant", "content": c, "tool_calls": t}

                    case "result":
                        tc: AiResult = typing.cast(AiResult, self.content[0])
                        return {"role": "tool", "tool_call_id": tc.id, "content": tc.result}

                    case _:
                        if self.content:
                            for p in self.content:
                                c.append(p.to_json(company=company))
                        return {"role": self.role, "content": c, "tool_calls": None}




# schema = None
# if os.path.exists("TES/Vegas_pro/schema.json"):
#     with open("TES/Vegas_pro/schema.json", "r") as schema_file:
#         schema = json.load(schema_file)



class AiPrompt:
    def __init__(self, vm):
        self.messages = []
        self.system_message = None
        self.toks_in: int = 0
        self.toks_out: int = 0
        self.company: str = ''
        self.model: str = ''
        self.api_key: str = ''
        self.vm = vm

    def add_message(self, vm, role: str, content: list[AiMessagePart] = None, tool_calls: List[AiCall] = None):

        if content is None: content = []
        if tool_calls is None: tool_calls = []

        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content.extend(content)
            self.messages[-1].tool_calls.extend(tool_calls)
        else:
            self.messages.append(AiMessage(vm=self.vm, role=role, content=content, tool_calls=tool_calls))


    def to_json(self) -> list[dict]:
        """Generate Json-able Object for API company specific Request"""
        json_msgs = []
        for msg in self.messages:
            x = msg.to_json(company=self.company)
            if type(x) is list:
                json_msgs.extend(x)
            else:
                json_msgs.append(x)

        # Anthropic use data['system'] instead of Message(role=system
        if self.company in ['Anthropic']:
            if json_msgs[0]['role'] == 'system':
                msg = json_msgs.pop(0)
                self.system_message = msg['content']

        # Google use data['system'] instead of Message(role=system
        if self.company in ['Google'] and json_msgs[0]['role'] == 'system':
            msg = json_msgs.pop(0)
            self.system_message = msg['parts'][0]['text']

        return json_msgs

    def ask(self, label) -> AiMessage:
        """make a prompt to self.company::self.model and process the result"""
        if self.company in companies_with_api_key:
            self.api_key = get_api_key(company=self.company)
        else:
            self.api_key = ''

        # Execute the request with the parameters generated by self.make_url_hdr()
        request_params = self.make_request_params()

        if self.vm.debug:
            console.print(f"{'-' * 10}> Sending to API...")

            # console.print_json(json.dumps(request_params), indent=2)
            console.print(f"<{'-' * 10} End Sending")

        with Progress(
                "[progress.description]{task.description}",  # Show description
                TimeElapsedColumn(),  # Automatically show elapsed time
                console=console, transient=True  # Use transient=True to avoid a new line at the end
        ) as progress:
            task = progress.add_task(label, total=None)
            # Execute the HTTP request while the progress bar is running
            response = requests.post(**request_params)
            progress.update(task, description=label)  # Finalize task

        # response = requests.post(**request_params)

        # Process an Error Response
        if response.status_code != 200:
            err_msg = f"API Request failed with status code {response.status_code}: {response.text}"
            raise ValueError(err_msg)  # @Todo replace all valueError for my own errors.

        # We got a good response...
        try:
            response_data = response.json()
        except JSONDecodeError as err:
            console.print(f"Error decoding json in response, {err.msg}")
            console.print(f"{'-' * 10}> Err Receiving from API...")
            console.print(f"Raw text Received: {response.text}")
            console.print(f"<{'-' * 10} End Receiving")
            raise


        # Debug Returned value
        if self.vm.debug:
            console.print(f"{'-' * 10}> Receiving from API...")
            part = json.loads(json.dumps(response_data))
            self.clean_messages(part)
            console.print_json(json.dumps(part), indent=2)
            console.print(f"<{'-' * 10} End Receiving")

        # Gather response Info From returned Json into an AiMessage...
        msg_parts: list[AiMessagePart] = []

        match self.company:
            case 'Anthropic':
                self.toks_out += response_data['usage']["output_tokens"]
                self.toks_in += response_data['usage']["input_tokens"]
                if 'content' not in response_data:
                    err_msg = "No content found in the response."
                    raise ValueError(err_msg)

                role = response_data['role']
                parts = response_data['content']
                if type(parts) is str:
                    parts = [parts]

                for msg in parts:
                    if type(msg) is str:
                        msg_parts.append(AiTextPart(vm=self.vm, text=msg))
                    elif type(msg) is dict:
                        if msg['type'] == 'text':
                            msg_parts.append(AiTextPart(vm=self.vm, text=msg['text']))
                        elif msg['type'] == 'tool_use':
                            fc_id = msg['id']
                            fc_name = msg['name']
                            fc_args = msg['input']
                            msg_parts.append(AiCall(vm=self.vm, name=fc_name, arguments=fc_args, id=fc_id))

                return AiMessage(vm=self.vm, role=role, content=msg_parts)

            case 'Google':
                self.toks_out += response_data['usageMetadata']["candidatesTokenCount"]
                self.toks_in += response_data['usageMetadata']["promptTokenCount"]
                if 'candidates' not in response_data or len(response_data['candidates']) <= 0:
                    err_msg = "No content found in the response."
                    raise ValueError(err_msg)

                    # This is the message returned
                llm_msg = response_data['candidates'][0]['content']
                role = llm_msg['role']
                parts = llm_msg['parts']

                # Loop over all returned messages
                for part in parts:
                    part = typing.cast(dict, part)
                    if "text" in part.keys():
                        msg_parts.append(AiTextPart(vm=self.vm, text=part['text']))
                    elif "functionCall" in part.keys():
                        msg_parts.append(
                            AiCall(vm=self.vm, name=part['functionCall']['name'], arguments=part['functionCall']['args']))
                    else:
                        emsg = f"ERROR: unexpected response type from google {part.keys()} in response['choices'][0]['message']"
                        console.print(f"[red]{emsg}[/]")
                        pprint.pprint(part)
                        raise ValueError(emsg)

                return AiMessage(vm=self.vm, role=role, content=msg_parts)

            case 'MistralAI' | 'OpenAI' | 'XAI' | 'DeepSeek':

                self.toks_out += response_data['usage']["completion_tokens"]
                self.toks_in += response_data['usage']["prompt_tokens"]

                if 'choices' not in response_data or len(response_data['choices']) <= 0:
                    err_msg = "No content found in the response."
                    raise ValueError(err_msg)

                # This is the message returned
                llm_msg = response_data['choices'][0]['message']
                role = llm_msg['role']
                parts = llm_msg['content']
                if parts is None:
                    parts = []

                if type(parts) is not list:
                    parts = [parts]

                # Loop over all returned messages
                for part in parts:
                    if type(part) is str:
                        if part != '':
                            msg_parts.append(AiTextPart(vm=self.vm, text=part))
                    elif type(part) is dict:
                        part = typing.cast(dict, part)
                        if part['text'] != '':
                            msg_parts.append(AiTextPart(vm=self.vm, text=part['text']))
                    else:
                        emsg = f"ERROR: unexpected response type from {self.company} {type(part)} in response['choices'][0]['message']"
                        console.print(f"[red]{emsg}[/]")
                        raise ValueError(emsg)

                llm_tool_calls: list[dict] = []
                tool_calls: list[AiCall] = []
                if "tool_calls" in llm_msg:
                    llm_tool_calls = llm_msg['tool_calls']

                if llm_tool_calls:
                    for fc in llm_tool_calls:
                        fc_id = fc['id']
                        fc_name = fc['function']['name']
                        fc_args = fc['function']['arguments']
                        tool_calls.append(AiCall(vm=self.vm, name=fc_name, arguments=fc_args, id=fc_id))

                return AiMessage(vm=self.vm, role=role, content=msg_parts, tool_calls=tool_calls)

            case _:
                raise ValueError(f"Unknown company: {self.company}")

    def clean_messages(self, data: dict):
        for k, v in data.items():
            if k in ["url", "data", "image_url"] and type(v) == str:
                data[k] = '...'
            elif type(v) == dict:
                self.clean_messages(v)
            elif type(v) == list:
                for item in v:
                    if type(item) == dict:
                        self.clean_messages(item)

    def make_request_params(self) -> dict:
        retval: dict = {}
        json_data: str = ''

        match self.company:
            case "Anthropic":
                data = {"model": self.model, "max_tokens": 1024, "messages": self.to_json(),
                        "tools": AnthropicToolsArray}
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.anthropic.com/v1/messages",
                    "headers": {"x-api-key": self.api_key, "Content-Type": "application/json",
                                "anthropic-version": "2023-06-01"},
                    "data": json_data
                }

            case "Google":
                data = {"contents": self.to_json(),
                        "system_instruction": {"parts": [{"text": self.system_message}]},
                        "tools": [{"functionDeclarations": GoogleToolsArray}]
                        }
                json_data = json.dumps(data)
                retval = {
                    "url": f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
                    "headers": {"Content-Type": "application/json", },
                    "data": json_data
                }

            case "Groq":
                data = {
                    "model": self.model,
                    "messages": self.to_json(),
                    "tools": DefinedToolsArray,
                    # "response_format": "application/json"
                }
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.groq.com/openai/v1/chat/completions",
                    "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}", },
                    "data": json_data,
                }

            case "MistralAI":
                data = {"model": self.model,
                        "messages": self.to_json(),
                        "tools": DefinedToolsArray,
                        }

                json_data = json.dumps(data)

                retval = {
                    "url": f"https://api.mistral.ai/v1/chat/completions",
                    "headers": {"Content-Type": "application/json", "Accept": "application/json",
                                "Authorization": f"Bearer {self.api_key}"},
                    "data": json_data,
                }

            case "Ollama":
                pass

            case "OpenAI" :
                data = {
                    "model": self.model,
                    "messages": self.to_json(),
                    "tools": DefinedToolsArray,
                    # "response_format": "application/json"
                }
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.openai.com/v1/chat/completions",
                    "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}", },
                    "data": json_data,
                }

            case "DeepSeek":
                data = {
                    "model": self.model,
                    "messages": self.to_json(),
                    "tools": DefinedToolsArray,
                    "stream": False
                }
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.deepseek.com/chat/completions",
                    "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}" },
                    "data": json_data,
                }


            case "XAI":
                data = {"model": self.model,
                        "messages": self.to_json(),
                        "tools": DefinedToolsArray,
                        "too_choice": "auto"
                        }

                json_data = json.dumps(data)

                retval = {
                    "url": "https://api.x.ai/v1/chat/completions",
                    "headers": {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", },
                    "data": json_data,
                }

            case _:
                raise ValueError(f"Unknown company: {self.company}")

        if self.vm.debug:
            console.print(f"{'-' * 10}> Send to API...")
            t = json.loads(json_data)
            self.clean_messages(t)
            console.print_json(json.dumps(t, indent=2))
            console.print(f"<{'-' * 10} End Send...")

        return retval

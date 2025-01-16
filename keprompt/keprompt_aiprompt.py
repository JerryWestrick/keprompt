import base64
import json
import mimetypes
import pprint
import threading
import typing
from abc import ABC, abstractmethod
from time import sleep
from typing import List

import keyring
import requests
from rich.console import Console

from keprompt.keprompt_functions import DefinedToolsArray, GoogleToolsArray, AnthropicToolsArray

# Global Variables
console = Console()
terminal_width = console.size.width
companies_with_api_key = ["Anthropic", "Google", "MistralAI", "OpenAI", "XAI"]


def get_api_key(company:str) -> str:
    try:
        api_key = keyring.get_password('kestep', username=company)
    except keyring.errors.PasswordDeleteError:
        console.print(f"[bold red]Error accessing keyring ('kestep', username={company})[/bold red]")
        api_key = None

    if api_key is None:
        api_key = console.input(f"Please enter your {company} API key: ")
        keyring.set_password("kestep", username=company, password=api_key)

    if not api_key:
        console.print("[bold red]API key cannot be empty.[/bold red]")
        raise ValueError("API key cannot be empty.")

    return api_key

class DotThread(threading.Thread):
    def __init__(self):
        super(DotThread, self).__init__()
        self.stop_event = threading.Event()
        self.count = 0
        self.is_running = False

    def run(self):
        self.is_running = True
        self.stop_event.clear()
        self.count = 0
        while not self.stop_event.is_set():
            console.print('.', end='')
            self.count += 1
            sleep(1)
        self.is_running = False

    def start(self):
        if not self.is_running:
            super(DotThread, self).start()

    def stop(self):
        if self.is_running:
            self.stop_event.set()

class AiMessagePart(ABC):
    def __init__(self, part_type: str):
        self.type = part_type

    @abstractmethod
    def to_json(self, company):
        pass

class AiTextPart(AiMessagePart):
    def __init__(self, text: str):
        super().__init__("text")
        self.text = text

    def to_json(self, company: str):
        if company in ['Google']:
            return {"text": self.text}

        return {"type": "text", "text": self.text}

    def __str__(self):
        return f"Text(text={self.text})"

    def __repr__(self):
        return f"Text(text={self.text!r})"

class AiImagePart(AiMessagePart):

    def __init__(self, filename:str ):
        super().__init__("image_url")
        self.filename = filename

        """ Read a binary file from local disk and encode it as base64."""
        with open(filename, 'rb') as file:
            self.file_contents = base64.b64encode(file.read()).decode()
        self.media_type, _ = mimetypes.guess_type(filename)

    def __str__(self):
        return f"Image(filename={self.filename}, media_type={self.media_type})"

    def __repr__(self):
        return f"Image(filename={self.filename!r}, media_type={self.media_type!r})"

    def to_json(self, company: str):

        if company == 'Anthropic':
            return {"type": "image","source": {"type": "base64", "media_type": self.media_type, "data": self.file_contents}}

        if company == 'Google':
            return {"inline_data": {"mime_type": self.media_type, "data": self.file_contents}}

        if company == 'MistralAI':
            return {"type": "image_url","image_url": f"data:{self.media_type};base64,{self.file_contents}"}

        # others/default
        return {"type": "image_url", "image_url": {"url": f"data:image/{self.media_type};base64,{self.file_contents}"}}

class AiToolPart(AiMessagePart):
    def __init__(self, name: str, arguments: str, id: str|None = None):
        super().__init__("tool_call")
        self.name = name
        self.id = id
        self.arguments = arguments

    def __str__(self):
        return f"Tool(name={self.name}, id={self.id}, arguments={self.arguments})"

    def __repr__(self):
        return f"Tool(name={self.name!r}, id={self.id!r}, arguments={self.arguments!r})"

    def to_json(self, company: str):

        match company:
            case 'Anthropic':
                return {"type": "tool_use","id": self.id,"name": self.name,"input": self.arguments}

            case 'Google':
                return {"functionCall": {"name": self.name, "args": self.arguments}}

            case 'MistralAI':
                return {"type": "function","id": self.id,"function": {"name": self.name, "arguments": self.arguments}}

            case 'OpenAI':
                return {"type": "function", "name": self.name, "id": self.id, "arguments": self.arguments}

            case 'XAI':
                return {'id': self.id, "function": {"type": "function", "name": self.name, "arguments": self.arguments}}

            case _:
                raise ValueError(f"Unknown Company Value: {company}")




class AiToolResult(AiMessagePart):
    def __init__(self, name: str, id: str, result: str):
        super().__init__("tool_result")
        self.name = name
        self.id = id
        self.result = result

    def __str__(self):
        return f"ToolResult(name={self.name}, id={self.id}, content={self.result})"

    def __repr__(self):
        return f"ToolResult(name={self.name!r}, id={self.id!r}, content={self.result!r})"

    def to_json(self, company: str):
        match company:
            case 'Anthropic':
                return {"type": "tool_result","tool_use_id": self.id,"content": self.result}

            case 'Google':
                return {"functionResponse":{"name": self.name, "response": {"text": self.result}}}

            case 'MistralAI':
                return {"role":"tool", "id": self.id, "name": self.name, "content": self.result}

            case "XAI":
                return {"role": "tool", "tool_call_id":self.id, "content": self.result}

            case _:
                raise ValueError(f"Unknown Company Value: {company}")

class AiMessage:
    def __init__(self, role: str, content=None, tool_calls: List[AiToolPart] = None):
        if content is None: content = []
        if tool_calls is None: tool_calls = []
        self.role = role
        assert(content is not None)
        assert(type(content) is list)
        self.content:List[AiMessagePart] = content
        self.tool_calls:List[AiToolPart] = tool_calls

    def __str__(self):
        return f"Message(role={self.role}, content={self.content}, tool_calls={self.tool_calls})"

    def __repr__(self):
        r =  f"Message(role={self.role!r}, content= [\n"
        for part in self.content:
            r += f"\t{str(part).replace('\n','\\n')}\n"
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
                    case 'assistant': role = 'model'
                    case 'result':    role='user'

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
                                c.append({"type":"text", "text": p.text})
                            return {"role": self.role, "content": c}

                    case 'result':
                            p = self.content[0]
                            p = typing.cast(AiToolResult, p)
                            return {"role": "tool", "name": p.name, "tool_call_id": p.id, "content": p.result}

                    case _:
                        for p in self.content:
                            c.append(p.to_json(company=company))
                        return {"role": self.role, "content": c}

            case "OpenAI":

                if self.role == 'assistant' and self.tool_calls:
                    c = []
                    for p in self.content:
                        c.append(p.to_json(company=company))

                    for p in self.tool_calls:
                        t.append(
                            {"id": p.id, "type": "function", "function": {"name": p.name, "arguments": p.arguments}})

                    return {"role": "assistant", "content": c, "tool_calls": t}

                if type(self.content[0]) == AiToolResult:
                    for p in self.content:
                        if type(p) is not AiToolResult:
                            raise ValueError(f"A function return with a part that in not a AiToolResult")
                        p = typing.cast(AiToolResult, p)
                        c.append({"role": "tool", "name": p.name, "tool_call_id": p.id, "content": [{"type":"text", "text": p.result}]})
                    return c

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
                        tc: AiToolResult = typing.cast(AiToolResult, self.content[0])
                        return {"role": "tool", "tool_call_id": tc.id, "content": tc.result}

                    case _:
                        if self.content:
                            for p in self.content:
                                c.append(p.to_json(company=company))
                        return {"role": self.role, "content": c, "tool_calls": None}



class AiPrompt:
    def __init__(self, step):
        self.messages = []
        self.system_message = None
        self.toks_in: int = 0
        self.toks_out: int = 0
        self.company:str = ''
        self.model:str = ''
        self.api_key:str = ''
        self.step = step

    def add_message(self, role:str, content:list[AiMessagePart]):

        if self.messages and self.messages[-1].role == role:
            self.messages[-1].content.extend(content)
        else:
            self.messages.append(AiMessage(role=role, content=content))

    def to_json(self) -> list[ dict] :
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

    def print_llm_value(self, value, indent=''):

        if isinstance(value, dict):
            self.print_llm_object(value, indent=indent)
        elif isinstance(value, list):
            self.print_llm_list(value, indent=indent)
        else:
            console.print(f"{str(value).replace('\n', '\\n')[:terminal_width - len(indent) - 11]}")

    def print_llm_list(self, data: list, indent=''):
        console.print(indent[:-2] + '[ ')

        for item in data:
            self.print_llm_value(item, indent=indent + '  ')

        console.print(indent + "]")

    def print_llm_object(self, data: dict, indent=''):
        """Recursively print data elements with indentation and escaping '\\n' for newlines."""
        console.print(indent[:-2] + '{ ')
        for key, value in data.items():
            console.print(f"{indent}{key}: ", end='')
            self.print_llm_value(value, indent=indent + '    ')
        console.print(indent + '}')


    def ask(self) -> AiMessage:
        """make a prompt to self.company::self.model and process the result"""
        if self.company in companies_with_api_key:
            self.api_key = get_api_key(company=self.company)
        else:
            self.api_key = ''

        # Execute the request with the parameters generated by self.make_url_hdr()
        response = requests.post(**self.make_request_params())

        # Process an Error Response
        if response.status_code != 200:
            err_msg = f"API Request failed with status code {response.status_code}: {response.text}"
            # console.print_json(json_data)
            raise ValueError(err_msg)

        # We got a good response...
        response_data = response.json()

        # Debug Returned value
        if self.step.debug:
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
                if 'content' not in response_data or len(response_data['content']) <= 0:
                    err_msg = "No content found in the response."
                    raise ValueError(err_msg)

                role = response_data['role']
                parts = response_data['content']
                if type(parts) is str:
                    parts = [parts]

                for msg in parts:
                    if type(msg) is str:
                        msg_parts.append(AiTextPart(msg))
                    elif type(msg) is dict:
                        if msg['type'] == 'text':
                            msg_parts.append(AiTextPart(msg['text']))
                        elif msg['type'] == 'tool_use':
                            fc_id = msg['id']
                            fc_name = msg['name']
                            fc_args = msg['input']
                            msg_parts.append(AiToolPart(fc_name, fc_args, fc_id))

                return AiMessage(role=role, content=msg_parts)

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
                    if "text" in part.keys():
                        msg_parts.append(AiTextPart(part['text']))
                    elif "functionCall" in part.keys():
                        msg_parts.append(AiToolPart(name=part['functionCall']['name'],arguments=part['functionCall']['args']))
                    else:
                        emsg =f"ERROR: unexpected response type from google {part.keys()} in response['choices'][0]['message']"
                        console.print(f"[red]{emsg}[/]")
                        pprint.pprint(part)
                        raise ValueError(emsg)

                return AiMessage(role=role, content=msg_parts)

            case 'MistralAI' | 'OpenAI' | 'XAI':

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
                            msg_parts.append(AiTextPart(part))
                    elif type(part) is dict:
                        if part['text'] != '':
                            msg_parts.append(AiTextPart(part['text']))
                    else:
                        emsg = f"ERROR: unexpected response type from {self.company} {type(part)} in response['choices'][0]['message']"
                        console.print(f"[red]{emsg}[/]")
                        raise ValueError(emsg)

                llm_tool_calls: list[dict] = []
                tool_calls: list[AiToolPart] = []
                if "tool_calls" in llm_msg:
                    llm_tool_calls = llm_msg['tool_calls']

                if llm_tool_calls:
                    for fc in llm_tool_calls:
                        fc_id = fc['id']
                        fc_name = fc['function']['name']
                        fc_args = fc['function']['arguments']
                        tool_calls.append(AiToolPart(fc_name, fc_args, fc_id))

                return AiMessage(role=role, content=msg_parts, tool_calls=tool_calls)

            case _:
                raise ValueError(f"Unknown company: {self.company}")

    def clean_messages(self, data: dict):
        for k, v in data.items():
            if k in ["url", "data", "image_url"] and type(v) == str: data[k] = '...'
            elif type(v) == dict: self.clean_messages(v)
            elif type(v) == list:
                for item in v:
                    if type(item) == dict:
                        self.clean_messages(item)


    def make_request_params(self) -> dict:
        retval: dict = {}
        json_data: str = ''

        match self.company:
            case "Anthropic":
                data = {"model": self.model, "max_tokens": 1024, "messages": self.to_json(), "tools": AnthropicToolsArray}
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.anthropic.com/v1/messages",
                    "headers":{"x-api-key": self.api_key,"Content-Type": "application/json","anthropic-version": "2023-06-01"},
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
                pass

            case "MistralAI":
                data = {"model": self.model,
                        "messages": self.to_json(),
                        "tools": DefinedToolsArray,
                        }

                json_data = json.dumps(data)

                retval = {
                    "url": f"https://api.mistral.ai/v1/chat/completions",
                    "headers": {"Content-Type": "application/json", "Accept": "application/json","Authorization": f"Bearer {self.api_key}"},
                    "data":json_data,
                }

            case "Ollama":
                pass

            case "OpenAI":
                data = {
                    "model": self.model,
                    "messages": self.to_json(),
                    "tools": DefinedToolsArray,
                }
                json_data = json.dumps(data)
                retval = {
                    "url": "https://api.openai.com/v1/chat/completions",
                    "headers": {"Content-Type": "application/json","Authorization": f"Bearer {self.api_key}",},
                    "data": json_data,
                }


            case "XAI":
                data = {"model": self.model,
                        "messages": self.to_json(),
                        "tools": DefinedToolsArray,
                        "too_choice": "auto"
                        }

                json_data = json.dumps(data)

                retval =  {
                    "url": "https://api.x.ai/v1/chat/completions",
                    "headers": {"Authorization": f"Bearer {self.api_key}","Content-Type": "application/json",},
                    "data": json_data,
                }

            case _:
                raise ValueError(f"Unknown company: {self.company}")

        if self.step.debug:
            console.print(f"{'-' * 10}> Send to API...")
            t = json.loads(json_data)
            self.clean_messages(t)
            console.print_json(json.dumps(t, indent=2))
            console.print(f"<{'-' * 10} End Send...")

        return retval
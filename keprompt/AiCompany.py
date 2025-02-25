# CompanyAi.py
import abc
from typing import List, Dict, Any, TYPE_CHECKING

import requests
from rich import json
from rich.console import Console
from rich.progress import TimeElapsedColumn, Progress

from .keprompt_functions import DefinedFunctions
from .keprompt_util import VERTICAL

console = Console()
terminal_width = console.size.width

if TYPE_CHECKING:
    from .AiPrompt import AiMessage, AiPrompt, AiCall, AiResult


class AiCompany(abc.ABC):

    def __init__(self, prompt: 'AiPrompt'):
        self.prompt = prompt
        self.system_prompt = None



    @abc.abstractmethod
    def prepare_request(self, messages: List[Dict]) -> Dict:
        """Override to create company-specific request format"""
        pass

    @abc.abstractmethod
    def get_api_url(self) -> str:
        """Override to provide company API endpoint"""
        pass

    @abc.abstractmethod
    def get_headers(self) -> Dict:
        """Override to provide company-specific headers"""
        pass

    @abc.abstractmethod
    def to_company_messages(self, messages: List['AiMessage']) -> List[Dict]:
        pass

    @abc.abstractmethod
    def to_ai_message(self, response: Dict) -> 'AiMessage':
        """Convert full API response to AiMessage. Each company implements their response parsing."""
        pass

    def call_llm(self, label: str) -> List['AiMessage']:
        do_again = True
        responses = []
        call_count = 0

        self.prompt.vm.print(f"{label} [bold blue]Calling {self.prompt.company}::{self.prompt.model}[/bold blue]")

        while do_again:
            call_count += 1
            do_again = False

            if 'Messages' in self.prompt.vm.debug:
                self.prompt.print_messages(f"Sent to {self.prompt.model}")

            company_messages = self.to_company_messages(self.prompt.messages)
            request = self.prepare_request(company_messages)

            # Make API call with formatted label
            call_label = f"Call-{call_count:02d}"
            response = self.make_api_request(
                url=self.get_api_url(),
                headers=self.get_headers(),
                data=request,
                label=call_label
            )

            response_msg = self.to_ai_message(response)
            self.prompt.messages.append(response_msg)
            responses.append(response_msg)

            tool_msg = self.call_functions(response_msg)
            if tool_msg:
                do_again = True
                self.prompt.messages.append(tool_msg)
                responses.append(tool_msg)

        if 'Messages' in self.prompt.vm.debug:
            self.prompt.print_messages(f"Received from {self.prompt.model}")

        return responses


    def call_functions(self, message):
        # Import here to avoid Circular Imports
        from .AiPrompt import AiResult, AiMessage, AiCall

        tool_results = []

        for part in message.content:
            if not isinstance(part, AiCall): continue

            try:
                if 'Functions' in self.prompt.vm.debug:
                    self.prompt.vm.print(f"[bold green]Executing function: {part.name} with args: {part.arguments}[/]")

                result = DefinedFunctions[part.name](**part.arguments)

                if 'Functions' in self.prompt.vm.debug:
                    self.prompt.vm.print(f"[bold green]Function Return: {result}[/]")

                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=str(result)))
            except Exception as e:
                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=f"Error calling {str(e)}"))

        return AiMessage(vm=self.prompt.vm, role="tool", content=tool_results) if tool_results else None



    def make_api_request(self, url: str, headers: Dict, data: Dict, label: str) -> Dict:

        if 'LLM' in self.prompt.vm.debug:
            self.prompt.vm.print_json(label=f"[bold blue]Sending to {self.prompt.company}::{self.prompt.model}[/bold blue]", data=data)

        with Progress("[progress.description]{task.description}", TimeElapsedColumn(), console=console, transient=True, ) as progress:
            call_label = f"[white]{VERTICAL}[/]{' ' * 12}{label}"
            task = progress.add_task(description=call_label, total=None)
            response = requests.post(url=url, headers=headers, json=data)
            progress.update(task, description=f"[white]{VERTICAL}[/]{' ' * 12}{label}")

        if response.status_code != 200:
            raise Exception(f"{self.prompt.company}::{self.prompt.model} API error: {response.text}")

        resp_obj = response.json()

        tokens = resp_obj.get("usage", {}).get("output_tokens", 0)
        elapsed = response.elapsed.total_seconds()
        tokens_per_sec = tokens / elapsed if elapsed > 0 else 0
        timings = f"Elapsed: {elapsed:.2f} seconds {tokens_per_sec:.2f} tps"
        head = f"{label} {timings}"
        rem = terminal_width - len(head)
        self.prompt.vm.print(f"[white]{VERTICAL}{' ' * 12}{head}{' ' * rem}[white]{VERTICAL}[/]", end='')
        # console.print(f"{head}{' ' * rem} [white]{VERTICAL}[/]", end='')

        retval = response.json()

        if 'LLM' in self.prompt.vm.debug:
            self.prompt.vm.print_json(label=f"[bold blue]Received from {self.prompt.company}::{self.prompt.model}[/bold blue]", data=retval)

        # Update token counts
        self.prompt.toks_in += retval.get("usage", {}).get("input_tokens", 0)
        self.prompt.toks_out += retval.get("usage", {}).get("output_tokens", 0)

        return retval

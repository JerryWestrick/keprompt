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

        # Get call_id from the prompt.ask call (passed from StmtExec)
        call_id = getattr(self.prompt, '_current_call_id', None)
        
        # Log the LLM call using structured logging
        call_msg = f"Calling {self.prompt.company}::{self.prompt.model}"
        self.prompt.vm.logger.log_llm_call(call_msg, call_id)
        
        # Format the statement line with the API call info for execution log
        import re
        # Clean up the label to extract statement number
        clean_label = re.sub(r'\[.*?\]', '', label)  # Remove Rich markup
        stmt_parts = clean_label.strip().split()
        if len(stmt_parts) >= 2:
            stmt_no = stmt_parts[0].replace('│', '')
            keyword = stmt_parts[1]
            # Use the logger's print_statement method to format consistently
            line_len = self.prompt.vm.logger.terminal_width - 14
            header = f"[bold white]{VERTICAL}[/][white]{stmt_no}[/] [cyan]{keyword:<8}[/] "
            call_line = f"{call_msg:<{line_len}}[bold white]{VERTICAL}[/]"
            self.prompt.vm.logger.log_execution(f"{header}[green]{call_line}[/]")

        while do_again:
            call_count += 1
            do_again = False

            # Log messages if in debug/log mode
            self.prompt.vm.logger.log_llm_call(f"Sent messages to {self.prompt.model}", call_id)

            company_messages = self.to_company_messages(self.prompt.messages)
            
            # Log detailed message exchange - what we're sending
            self.prompt.vm.logger.log_message_exchange("send", company_messages, call_id)
            
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
            
            # Log detailed message exchange - what we received
            # Convert the response message back to company format for logging
            received_messages = self.to_company_messages([response_msg])
            self.prompt.vm.logger.log_message_exchange("received", received_messages, call_id)

            tool_msg = self.call_functions(response_msg)
            if tool_msg:
                do_again = True
                self.prompt.messages.append(tool_msg)
                responses.append(tool_msg)
                
                # Don't log tool_response to messages.log - it's not sent to OpenAI
                # The tool results will be included in the next "send" message

        # Log received messages if in debug/log mode
        self.prompt.vm.logger.log_llm_call(f"Received messages from {self.prompt.model}", call_id)

        return responses


    def call_functions(self, message):
        # Import here to avoid Circular Imports
        from .AiPrompt import AiResult, AiMessage, AiCall

        tool_results = []

        for part in message.content:
            if not isinstance(part, AiCall): continue

            try:
                # Log function execution using structured logging
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, "executing")

                result = DefinedFunctions[part.name](**part.arguments)

                # Log function result using structured logging
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, result)

                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=str(result)))
            except Exception as e:
                error_result = f"Error calling {str(e)}"
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, error_result)
                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=error_result))

        return AiMessage(vm=self.prompt.vm, role="tool", content=tool_results) if tool_results else None



    def make_api_request(self, url: str, headers: Dict, data: Dict, label: str) -> Dict:
        # Get call_id from the prompt
        call_id = getattr(self.prompt, '_current_call_id', None)

        # Log API request data using structured logging
        self.prompt.vm.logger.log_llm_call(f"Sending request to {self.prompt.company}::{self.prompt.model}", call_id)

        # Make the API request without progress bar
        response = requests.post(url=url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"{self.prompt.company}::{self.prompt.model} API error: {response.text}")

        resp_obj = response.json()

        tokens = resp_obj.get("usage", {}).get("output_tokens", 0)
        elapsed = response.elapsed.total_seconds()
        tokens_per_sec = tokens / elapsed if elapsed > 0 else 0
        timings = f"Elapsed: {elapsed:.2f} seconds {tokens_per_sec:.2f} tps"
        # Format properly within the table structure
        # Use same width calculation as statement lines - only subtract borders (14)
        timing_content = f"{label} {timings}"
        content_len = self.prompt.vm.logger.terminal_width - 14  # Same as statement lines
        padded_content = f"{timing_content:<{content_len}}"
        final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
        
        self.prompt.vm.logger.log_execution(final_line)

        retval = response.json()

        # Log API response using structured logging
        self.prompt.vm.logger.log_llm_call(f"Received response from {self.prompt.company}::{self.prompt.model}", call_id)

        # Update token counts
        self.prompt.toks_in += retval.get("usage", {}).get("input_tokens", 0)
        self.prompt.toks_out += retval.get("usage", {}).get("output_tokens", 0)

        return retval

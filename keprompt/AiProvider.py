# AiProvider.py
import abc
import os
import json as json_module
from typing import List, Dict, Any, TYPE_CHECKING, Optional
from datetime import datetime

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


class AiProvider(abc.ABC):

    def __init__(self, prompt: 'AiPrompt'):
        self.prompt = prompt
        self.system_prompt = None



    @abc.abstractmethod
    def prepare_request(self, messages: List[Dict]) -> Dict:
        """Override to create provider-specific request format"""
        pass

    @abc.abstractmethod
    def get_api_url(self) -> str:
        """Override to provide provider API endpoint"""
        pass

    @abc.abstractmethod
    def get_headers(self) -> Dict:
        """Override to provide provider-specific headers"""
        pass

    @abc.abstractmethod
    def to_company_messages(self, messages: List['AiMessage']) -> List[Dict]:
        pass

    @abc.abstractmethod
    def to_ai_message(self, response: Dict) -> 'AiMessage':
        """Convert full API response to AiMessage. Each provider implements their response parsing."""
        pass

    @classmethod
    @abc.abstractmethod
    def create_models_json(cls, provider_name: str) -> None:
        """Create/update the models JSON file for this provider"""
        pass

    @classmethod
    def register_models(cls, provider_name: str) -> None:
        """Load models from JSON file, create if missing"""
        json_path = f"prompts/models/{provider_name}.json"
        
        if not os.path.exists(json_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            cls.create_models_json(provider_name)
        
        models = cls.load_models_from_json(json_path)
        
        # Import here to avoid circular imports
        from .AiRegistry import AiRegistry
        AiRegistry.register_models_from_dict(model_definitions=models)

    @classmethod
    def load_models_from_json(cls, json_path: str) -> Dict[str, Dict]:
        """Load and validate models from JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json_module.load(f)
            
            # Validate structure
            if not isinstance(data, dict) or 'models' not in data:
                raise ValueError("Invalid JSON structure: missing 'models' key")
            
            return data['models']
            
        except (FileNotFoundError, json_module.JSONDecodeError, ValueError) as e:
            console.print(f"[red]Error loading models from {json_path}: {e}[/red]")
            raise

    @classmethod
    def _write_json_file(cls, provider_name: str, models: Dict[str, Dict]) -> None:
        """Write models to JSON file with metadata"""
        json_path = f"prompts/models/{provider_name}.json"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        data = {
            "metadata": {
                "provider": provider_name,
                "last_updated": datetime.now().isoformat(),
                "total_models": len(models)
            },
            "models": models
        }
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json_module.dump(data, f, indent=2, ensure_ascii=False)
            
            console.print(f"[green]Successfully wrote {len(models)} models to {json_path}[/green]")
            
        except Exception as e:
            console.print(f"[red]Error writing models to {json_path}: {e}[/red]")
            raise

    def call_llm(self, label: str) -> List['AiMessage']:
        do_again = True
        responses = []
        call_count = 0

        # Get call_id from the prompt.ask call (passed from StmtExec)
        call_id = getattr(self.prompt, '_current_call_id', None)
        
        # Log the LLM call using structured logging
        call_msg = f"Calling {self.prompt.provider}::{self.prompt.model}"
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
        self.prompt.vm.logger.log_llm_call(f"Sending request to {self.prompt.provider}::{self.prompt.model}", call_id)

        # Make the API request without progress bar
        response = requests.post(url=url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"{self.prompt.provider}::{self.prompt.model} API error: {response.text}")

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
        self.prompt.vm.logger.log_llm_call(f"Received response from {self.prompt.provider}::{self.prompt.model}", call_id)

        # Update token counts
        self.prompt.toks_in += retval.get("usage", {}).get("input_tokens", 0)
        self.prompt.toks_out += retval.get("usage", {}).get("output_tokens", 0)

        return retval

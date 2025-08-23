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

    @abc.abstractmethod
    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        """Extract token usage from API response. Returns (tokens_in, tokens_out)."""
        pass

    @abc.abstractmethod
    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        """Calculate costs based on token usage. Returns (cost_in, cost_out)."""
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
            call_msg = f"Calling {self.prompt.provider}::{self.prompt.model}"
            call_line = f"{call_msg:<{line_len}}[bold white]{VERTICAL}[/]"
            self.prompt.vm.logger.log_execution(f"{header}[green]{call_line}[/]")

        while do_again:
            call_count += 1
            do_again = False

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
            
            tool_msg = self.call_functions(response_msg)
            if tool_msg:
                do_again = True
                self.prompt.messages.append(tool_msg)
                responses.append(tool_msg)
                
                # Don't log tool_response to messages.log - it's not sent to OpenAI
                # The tool results will be included in the next "send" message
            else:
                # No function calls - this is a final text response, show it and log it
                # Log the entire conversation including the final response
                all_messages = self.to_company_messages(self.prompt.messages)
                self.prompt.vm.logger.log_message_exchange("received", all_messages, call_id)
                self._display_llm_text_response(response_msg, call_label)

        return responses


    def call_functions(self, message):
        # Import here to avoid Circular Imports
        from .AiPrompt import AiResult, AiMessage, AiCall
        import time

        tool_results = []
        function_call_info = []

        for part in message.content:
            if not isinstance(part, AiCall): continue

            try:
                # Log function execution using structured logging
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, "executing")

                # Track function execution timing
                func_start_time = time.time()
                result = DefinedFunctions[part.name](**part.arguments)
                func_elapsed_time = time.time() - func_start_time

                # Log function result using structured logging
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, result)

                # Store function call info for debug output
                # Format arguments for display (truncate long values)
                display_args = {}
                for k, v in part.arguments.items():
                    if isinstance(v, str) and len(v) > 50:
                        display_args[k] = v[:47] + "..."
                    else:
                        display_args[k] = v
                
                function_call_info.append({
                    'name': part.name,
                    'args': display_args,
                    'elapsed': func_elapsed_time
                })

                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=str(result)))
            except Exception as e:
                func_elapsed_time = time.time() - func_start_time if 'func_start_time' in locals() else 0
                error_result = f"Error calling {str(e)}"
                self.prompt.vm.logger.log_function_call(part.name, part.arguments, error_result)
                
                # Store error function call info for debug output
                display_args = {}
                for k, v in part.arguments.items():
                    if isinstance(v, str) and len(v) > 50:
                        display_args[k] = v[:47] + "..."
                    else:
                        display_args[k] = v
                
                function_call_info.append({
                    'name': part.name,
                    'args': display_args,
                    'elapsed': func_elapsed_time,
                    'error': True
                })
                
                tool_results.append(AiResult(vm=self.prompt.vm, name=part.name, id=part.id or "", result=error_result))

        # Store function call info in the prompt for use in timing display
        if function_call_info:
            self.prompt._last_function_calls = function_call_info
            
            # Display enhanced timing information with function calls
            if hasattr(self.prompt, '_pending_timing_display'):
                pending = self.prompt._pending_timing_display
                
                # Build function call summary for display
                func_summaries = []
                for func_info in function_call_info:
                    # Format arguments for display - show full argument structure
                    args_parts = []
                    for k, v in func_info['args'].items():
                        if isinstance(v, str):
                            # For string values, show them with proper formatting
                            if len(str(v)) > 40:
                                display_val = str(v)[:37] + "..."
                            else:
                                display_val = str(v)
                            args_parts.append(f"{k}={display_val}")
                        else:
                            args_parts.append(f"{k}={v}")
                    
                    args_str = ", ".join(args_parts)
                    
                    func_summary = f"Call {func_info['name']}({args_str})... {func_info['elapsed']:.1f} secs"
                    if func_info.get('error'):
                        func_summary += " [ERROR]"
                    func_summaries.append(func_summary)
                
                # Create enhanced timing line with elapsed time, TPS, and function calls
                func_summary_text = ' | '.join(func_summaries)
                enhanced_content = f"{pending['label']} {pending['timings']} --> {func_summary_text}"
                
                # Format properly within the table structure
                content_len = self.prompt.vm.logger.terminal_width - 14
                padded_content = f"{enhanced_content:<{content_len}}"
                final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
                
                # Log the enhanced timing line
                self.prompt.vm.logger.log_execution(final_line)
                
                # Clean up
                delattr(self.prompt, '_pending_timing_display')

        return AiMessage(vm=self.prompt.vm, role="tool", content=tool_results) if tool_results else None



    def make_api_request(self, url: str, headers: Dict, data: Dict, label: str) -> Dict:
        # Get call_id from the prompt
        call_id = getattr(self.prompt, '_current_call_id', None)

        # Clear any previous function call info before making the request
        if hasattr(self.prompt, '_last_function_calls'):
            delattr(self.prompt, '_last_function_calls')

        # Extract and display what we're sending to the LLM
        send_summary = self._extract_send_summary(data)

        # Make the API request without progress bar
        response = requests.post(url=url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"{self.prompt.provider}::{self.prompt.model} API error: {response.text}")

        resp_obj = response.json()

        tokens = resp_obj.get("usage", {}).get("output_tokens", 0)
        elapsed = response.elapsed.total_seconds()
        tokens_per_sec = tokens / elapsed if elapsed > 0 else 0
        timings = f"Elapsed: {elapsed:.2f} seconds {tokens_per_sec:.2f} tps"
        
        # Build the simplified timing content with send information
        timing_content = f"{label} <-- {send_summary}"
        
        # Check if there are function calls to append (will be set by call_functions after this)
        # We'll store this timing info to be enhanced later
        self.prompt._pending_timing_display = {
            'label': label,
            'timings': timings,
            'content': timing_content,
            'send_summary': send_summary
        }
        
        # Format properly within the table structure
        content_len = self.prompt.vm.logger.terminal_width - 14  # Same as statement lines
        padded_content = f"{timing_content:<{content_len}}"
        final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
        
        self.prompt.vm.logger.log_execution(final_line)

        retval = response.json()

        # Use provider-specific token extraction and cost calculation
        tokens_in, tokens_out = self.extract_token_usage(retval)
        cost_in, cost_out = self.calculate_costs(tokens_in, tokens_out)
        total_cost = cost_in + cost_out
        
        # Count messages sent
        msg_count = len(data.get('messages', []))
        
        # Log enhanced llm.log entry with concise format
        log_entry = f"{call_id}-{label}: nomsgs: {msg_count:02d}, tokens in: {tokens_in}, out: {tokens_out}, cost: ${total_cost:.6f}"
        self.prompt.vm.logger.log_llm_call(log_entry, None)  # Don't prefix with call_id since it's in the message

        # Update token counts
        self.prompt.toks_in += tokens_in
        self.prompt.toks_out += tokens_out

        return retval

    def _extract_send_summary(self, request_data: Dict) -> str:
        """Extract a summary of what we're sending to the LLM"""
        try:
            messages = request_data.get('messages', [])
            if not messages:
                return "Send (empty)"
            
            # Get the last message (could be user, tool, or assistant)
            last_message = messages[-1] if messages else None
            
            if not last_message:
                return "Send (no message)"
            
            role = last_message.get('role', '')
            content = last_message.get('content', '')
            
            # Handle tool role messages (function results)
            if role == 'tool':
                if isinstance(content, list):
                    tool_results = []
                    for part in content:
                        if isinstance(part, dict):
                            # Handle different possible structures
                            tool_name = part.get('name', part.get('tool_use_id', 'unknown'))
                            result_content = part.get('content', part.get('result', ''))
                            
                            if isinstance(result_content, str):
                                if len(result_content) > 40:
                                    result_content = result_content[:37] + "..."
                                # Show the actual result content
                                tool_results.append(f"{tool_name}='{result_content}'")
                            else:
                                tool_results.append(f"{tool_name}=(complex)")
                    if tool_results:
                        return f"Send tool_results({', '.join(tool_results)})"
                elif isinstance(content, str):
                    # Handle simple string content
                    if len(content) > 40:
                        content = content[:37] + "..."
                    return f"Send tool_result('{content}')"
                return "Send tool_result"
            
            # Handle user/assistant messages
            if isinstance(content, list):
                # Extract text from content array
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get('type') == 'text':
                            text_parts.append(part.get('text', ''))
                        elif part.get('type') == 'tool_result':
                            tool_name = part.get('name', 'unknown')
                            text_parts.append(f"tool_result({tool_name})")
                    elif isinstance(part, str):
                        text_parts.append(part)
                
                content = ' '.join(text_parts)
            
            if isinstance(content, str):
                # Truncate long content
                if len(content) > 50:
                    content = content[:47] + "..."
                return f"Send text('{content}')"
            
            return "Send (complex content)"
            
        except Exception:
            return "Send (parse error)"

    def _display_llm_text_response(self, response_msg, call_label: str):
        """Display the final text response from the LLM"""
        from .AiPrompt import AiTextPart
        
        # Extract text content from the response message
        text_parts = []
        for part in response_msg.content:
            if isinstance(part, AiTextPart):
                text_parts.append(part.text)
        
        if text_parts:
            # Combine all text parts
            full_text = ' '.join(text_parts)
            
            # Truncate if too long
            if len(full_text) > 50:
                display_text = full_text[:47] + "..."
            else:
                display_text = full_text
            
            # Check if we have pending timing display to enhance
            if hasattr(self.prompt, '_pending_timing_display'):
                pending = self.prompt._pending_timing_display
                
                # Create simplified timing line with LLM response
                enhanced_content = f"{pending['label']} --> Return text('{display_text}')"
                
                # Format properly within the table structure
                content_len = self.prompt.vm.logger.terminal_width - 14
                padded_content = f"{enhanced_content:<{content_len}}"
                final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
                
                # Log the enhanced timing line
                self.prompt.vm.logger.log_execution(final_line)
                
                # Clean up
                delattr(self.prompt, '_pending_timing_display')

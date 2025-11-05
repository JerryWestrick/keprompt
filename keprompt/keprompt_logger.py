"""
Standard logging system for keprompt v2.0.

This module provides a professional logging interface using Python's standard logging
module with custom log levels and multi-process safe single log file output.
"""

import logging
import os
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.logging import RichHandler


class LogMode(Enum):
    """Logging modes for keprompt."""
    LOG = "none"
    PRODUCTION = "production"  # Clean STDOUT only
    DEBUG = "debug"           # Rich STDERR output only


# Define custom log levels
LLM_LEVEL = 25      # LLM API calls, tokens, costs
FUNC_LEVEL = 23     # Function calls and results
MSG_LEVEL = 21      # Message exchanges

# Add custom levels to logging module
logging.addLevelName(LLM_LEVEL, 'LLM')
logging.addLevelName(FUNC_LEVEL, 'FUNC')
logging.addLevelName(MSG_LEVEL, 'MSG')


class PromptContextFilter(logging.Filter):
    """Filter to add prompt_id context to log records."""
    
    def __init__(self, prompt_id: str = ""):
        super().__init__()
        self.prompt_id = prompt_id
    
    def filter(self, record):
        record.prompt_id = self.prompt_id
        return True


class StandardLogger:
    """
    Simplified logging system for keprompt.
    
    Supports PRODUCTION (clean STDOUT) and DEBUG (rich STDERR) modes.
    Chat details are now captured in chats.db and viewable via chat_viewer.
    """
    
    def __init__(self, prompt_name: str, mode: LogMode = LogMode.PRODUCTION, log_identifier: str = None):
        """
        Initialize the standard logger.
        
        Args:
            prompt_name: Name of the prompt (without .prompt extension)
            mode: Logging mode (production or debug)
            log_identifier: Unused (kept for compatibility)
        """
        self.prompt_name = prompt_name
        self.mode = mode
        self.prompt_id = ""  # Will be set when we get the UUID
        
        # Initialize console for STDERR output
        self.console = Console(stderr=True)
        self.terminal_width = self.console.size.width
    
    def set_prompt_id(self, prompt_id: str):
        """Set the prompt ID for compatibility."""
        self.prompt_id = prompt_id
    
    def _write_to_stderr(self, message: str):
        """Write message to STDERR using Rich console."""
        if self.mode == LogMode.DEBUG:
            self.console.print(message)
    
    # Core logging methods - simplified to only handle DEBUG console output
    def log_info(self, message: str):
        """Log general information (statement execution)."""
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(f"[dim]INFO: {message}[/dim]")
    
    def log_debug(self, message: str):
        """Log debug information (detailed execution flow)."""
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(f"[dim]DEBUG: {message}[/dim]")
    
    def log_llm(self, message: str):
        """Log LLM API calls, tokens, costs."""
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(f"[blue]LLM: {message}[/blue]")
    
    def log_func(self, message: str):
        """Log function calls and results."""
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(f"[green]FUNC: {message}[/green]")
    
    def log_msg(self, message: str):
        """Log message exchanges."""
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(f"[cyan]MSG: {message}[/cyan]")
    
    def log_error(self, message: str, exit_code: int = 1):
        """Log error message and exit."""
        # Always write to STDERR (all modes)
        print(f"Error: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold red]Error: {message}[/bold red]")
        
        # Exit with error code
        sys.exit(exit_code)
    
    def log_warning(self, message: str):
        """Log warning message."""
        # Always write to STDERR
        print(f"Warning: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold yellow]Warning: {message}[/bold yellow]")
    
    # Convenience methods for common logging patterns
    def log_statement(self, msg_no: int, keyword: str, value: str):
        """Log statement execution."""
        if self.mode == LogMode.DEBUG:
            if value:
                self._write_to_stderr(f"[dim]STMT: {keyword} {value}[/dim]")
            else:
                self._write_to_stderr(f"[dim]STMT: {keyword}[/dim]")
    
    def log_llm_call(self, message: str, call_id: str = None):
        """Log LLM API call information."""
        self.log_llm(message)
    
    def log_llm_tokens_and_cost(self, call_id: str, tokens_in: int, tokens_out: int, cost_in: float, cost_out: float):
        """Log LLM token usage and costs in concise format."""
        total_cost = cost_in + cost_out
        self.log_llm(f"{call_id} tokens in: {tokens_in}, out: {tokens_out}, cost in: ${cost_in:.6f}, out: ${cost_out:.6f}, total: ${total_cost:.6f}")
    
    def log_function_call(self, function_name: str, args: Dict, result: Any, duration: float = 0.0):
        """Log function call in single line format."""
        duration_str = f" ({duration:.3f} secs)" if duration > 0 else ""
        self.log_func(f"{function_name}({args}) -> {result}{duration_str}")
        
        # If the result contains an error, also write to stderr with improved formatting
        if isinstance(result, str) and ("Error executing" in result or "ERROR:" in result):
            # Extract and format file-related errors more clearly
            if function_name == "readfile" and "filename" in args:
                filename = args["filename"]
                # Extract the core error message from nested exceptions
                if "No such file or directory" in result:
                    print(f"File Error: Cannot read file '{filename}' - File not found", file=sys.stderr)
                elif "Permission denied" in result:
                    print(f"File Error: Cannot read file '{filename}' - Permission denied", file=sys.stderr)
                else:
                    # For other file errors, show the filename prominently
                    print(f"File Error: Cannot read file '{filename}' - {self._extract_core_error(result)}", file=sys.stderr)
            else:
                # For non-file functions, use the original format but clean it up
                clean_result = self._extract_core_error(result)
                print(f"Function Error: {function_name}({args}) -> {clean_result}", file=sys.stderr)
    
    def _extract_core_error(self, error_message: str) -> str:
        """Extract the core error message from nested exception text."""
        # Remove redundant "Error executing function" prefixes
        if "Error executing function" in error_message:
            parts = error_message.split("Error executing function")
            if len(parts) > 1:
                error_message = parts[-1].strip(": '")
        
        # Remove redundant "Function 'X' failed:" prefixes
        if "' failed:" in error_message:
            parts = error_message.split("' failed:")
            if len(parts) > 1:
                error_message = parts[-1].strip()
        
        # Remove redundant "Error:" prefixes
        if error_message.startswith("Error:"):
            error_message = error_message[6:].strip()
        
        # Clean up multiple "Error accessing file" messages
        if "Error accessing file" in error_message and error_message.count("Error accessing file") > 1:
            # Find the last occurrence which usually has the most complete info
            parts = error_message.split("Error accessing file")
            if len(parts) > 1:
                error_message = "Error accessing file" + parts[-1]
        
        return error_message.strip()
    
    def log_execution_flow(self, direction: str, message: str):
        """Log execution flow (Call-01 <--, Call-01 -->)."""
        self.log_debug(f"{direction} {message}")
    
    def log_total_costs(self, total_tokens_in: int, total_tokens_out: int, total_cost_in: float, total_cost_out: float, provider: str = "", model: str = "", chat_id: str = "", interaction_no: int = 0):
        """Log total costs when exiting keprompt."""
        total_cost = total_cost_in + total_cost_out
        
        # Format chat identification
        chat_info = ""
        if chat_id:
            if interaction_no > 0:
                chat_info = f"Chat {chat_id}:{interaction_no}"
            else:
                chat_info = f"Chat {chat_id}"
        else:
            chat_info = "Chat"
        
        # Format provider and model info
        model_info = ""
        if provider and model:
            model_info = f" with {provider}:{model}"
        elif model:
            model_info = f" with {model}"
        
        self.log_llm(f"CHAT TOTAL: Tokens In: {total_tokens_in}, Out: {total_tokens_out}, Cost In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f}, Total: ${total_cost:.6f}{model_info}")
        
        # Also print to stderr for immediate visibility
        print(f"{chat_info}{model_info} Total Cost: ${total_cost:.6f} (In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f})", file=sys.stderr)
    
    def print_exception(self):
        """Print exception information."""
        import traceback
        exc_text = traceback.format_exc()
        
        # Log the exception
        self.log_error(f"Exception occurred: {exc_text}")
        
        # Always print to STDERR
        traceback.print_exc(file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print_exception(show_locals=True)
    
    def log_variable_assignment(self, var_name: str, value: str):
        """Log variable assignment."""
        self.log_debug(f"Variable assigned: {var_name} = {value}")
    
    def log_variable_retrieval(self, var_name: str, value: str):
        """Log variable retrieval."""
        self.log_debug(f"Variable retrieved: {var_name} = {value}")
    
    def log_execution(self, message: str):
        """Log execution information (for timing displays)."""
        self.log_info(message)
    
    def log_message_exchange(self, direction: str, messages: list, call_id: str):
        """Log detailed message exchanges with the LLM."""
        if not messages:
            return
        
        # In DEBUG mode, log a summary of the message exchange
        if self.mode == LogMode.DEBUG:
            self.log_msg(f"Message exchange: {len(messages)} messages")
    
    def log_chat(self, conversation_data: dict):
        """Log conversation data."""
        self.log_msg(f"Chat logged: {len(conversation_data.get('messages', []))} messages")
    
    def log_user_answer(self, answer: str):
        """Log user answer in conversation mode."""
        self.log_info(f"User answer: {answer}")

    def close(self):
        """Close the logger and cleanup handlers."""
        # No-op since we don't have file handlers anymore
        pass


# Backward compatibility aliases (will be removed in future versions)
KepromptLogger = StandardLogger

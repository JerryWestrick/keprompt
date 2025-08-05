"""
Structured logging system for keprompt v1.0.

This module provides a comprehensive logging interface that creates separate log files
for different types of information, making debugging and analysis much easier.
"""

import json
import os
import shutil
import sys
import time
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .keprompt_util import (
    TOP_LEFT, BOTTOM_LEFT, VERTICAL, HORIZONTAL, TOP_RIGHT, 
    HORIZONTAL_LINE, BOTTOM_RIGHT
)


class LogMode(Enum):
    """Logging modes for keprompt."""
    PRODUCTION = "production"  # Clean STDOUT only
    LOG = "log"               # Files only, silent execution
    DEBUG = "debug"           # Files + rich STDERR output


class KepromptLogger:
    """
    Structured logging system for keprompt.
    
    Creates separate log files for different types of information:
    - execution.log: Rich table execution trace
    - messages.log: Conversation JSON
    - llm.log: API requests/responses, timing
    - functions.log: Function calls and returns (with errors to stderr)
    - errors.log: Errors and warnings
    """
    
    def __init__(self, prompt_name: str, mode: LogMode = LogMode.PRODUCTION, log_identifier: str = None):
        """
        Initialize the structured logger.
        
        Args:
            prompt_name: Name of the prompt (without .prompt extension)
            mode: Logging mode (production, log, or debug)
            log_identifier: Custom identifier for log directory (if None, uses prompt_name)
        """
        self.prompt_name = prompt_name
        self.mode = mode
        self.log_identifier = log_identifier if log_identifier else prompt_name
        
        # Initialize console for STDERR output
        self.console = Console(stderr=True)
        self.terminal_width = self.console.size.width
        
        # Log file handles
        self.log_files = {}
        self.log_directory = None
        
        # Define all log file names
        self.log_file_names = [
            'execution.log',
            'messages.log', 
            'llm.log',
            'functions.log',
            'errors.log'
        ]
        
        # Setup logging if needed
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._setup_logging()
    
    def _setup_logging(self):
        """Setup the logging directory and create all log files."""
        # Create log directory path using the log identifier
        self.log_directory = Path(f"prompts/logs-{self.log_identifier}")
        
        # Create directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Create all log files with headers (only if they don't exist)
        for log_file_name in self.log_file_names:
            log_file_path = self.log_directory / log_file_name
            
            # Only create header if file doesn't exist
            if not log_file_path.exists():
                with open(log_file_path, 'w') as f:
                    f.write(f"=== {log_file_name} ===\n")
            
            # Open file handle for appending
            self.log_files[log_file_name] = open(log_file_path, 'a')
    
    def _write_to_file(self, file_name: str, message: str):
        """Write message to specified log file."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG] and file_name in self.log_files:
            self.log_files[file_name].write(message + '\n')
            self.log_files[file_name].flush()
    
    def _write_to_stderr(self, message: str):
        """Write message to STDERR using Rich console."""
        if self.mode == LogMode.DEBUG:
            self.console.print(message)
    
    def _strip_rich_formatting(self, message: str) -> str:
        """Strip Rich markup from message for plain text files."""
        import re
        return re.sub(r'\[/?[^\]]*\]', '', message)
    
    # Core logging methods
    def log_execution(self, message: str):
        """Log execution trace information."""
        # Always strip rich formatting for files
        plain_message = self._strip_rich_formatting(message)
        self._write_to_file('execution.log', plain_message)
        
        # Rich output to STDERR in debug mode
        if self.mode == LogMode.DEBUG:
            self._write_to_stderr(message)
    
    def log_statement(self, msg_no: int, keyword: str, value: str):
        """Log statement execution details - removed, not helpful."""
        pass
    
    def log_llm_call(self, message: str, call_id: str = None):
        """Log LLM API call information."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if call_id:
            log_entry = f"[{timestamp}] {call_id}: {message}"
        else:
            log_entry = f"[{timestamp}] {message}"
        self._write_to_file('llm.log', log_entry)
    
    def log_function_call(self, function_name: str, args: Dict, result: Any):
        """Log function call details."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] CALL: {function_name}({args}) -> {result}"
        self._write_to_file('functions.log', log_entry)
        
        # If the result contains an error, also write to stderr
        if isinstance(result, str) and ("Error executing" in result or "ERROR:" in result):
            print(f"Function Error: {function_name}({args}) -> {result}", file=sys.stderr)
    
    def log_user_answer(self, answer: str):
        """Log user answer in execution log for --answer mode."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            line_len = self.terminal_width - 14
            header = f"{VERTICAL}-- .user    "
            
            lines = answer.split("\n")
            for line in lines:
                while len(line) > 0:
                    print_line = f"{line:<{line_len}}{VERTICAL}"
                    self.log_execution(f"{header}{print_line}")
                    header = f"{VERTICAL}            "
                    line = line[line_len:]
    
    def log_llm_tokens_and_cost(self, call_id: str, tokens_in: int, tokens_out: int, cost_in: float, cost_out: float):
        """Log LLM token usage and costs."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        total_cost = cost_in + cost_out
        log_entry = f"[{timestamp}] {call_id}: Tokens In: {tokens_in}, Out: {tokens_out}, Cost In: ${cost_in:.6f}, Out: ${cost_out:.6f}, Total: ${total_cost:.6f}"
        self._write_to_file('llm.log', log_entry)
    
    def log_total_costs(self, total_tokens_in: int, total_tokens_out: int, total_cost_in: float, total_cost_out: float):
        """Log total costs when exiting keprompt."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        total_cost = total_cost_in + total_cost_out
        log_entry = f"[{timestamp}] SESSION TOTAL: Tokens In: {total_tokens_in}, Out: {total_tokens_out}, Cost In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f}, Total: ${total_cost:.6f}"
        self._write_to_file('llm.log', log_entry)
        
        # Also print to stderr for immediate visibility
        print(f"Session Total Cost: ${total_cost:.6f} (In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f})", file=sys.stderr)
    
    def log_variable_assignment(self, variable: str, value: str):
        """Log variable assignment - removed, not helpful."""
        pass

    def log_variable_retrieval(self, variable: str, value: str):
        """Log variable retrieval/substitution - removed, not helpful."""
        pass
    
    def log_conversation(self, conversation_data):
        """Log conversation messages to JSON file."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            json_content = json.dumps(conversation_data, indent=2)
            self._write_to_file('messages.log', json_content)
    
    def log_message_exchange(self, direction: str, messages: List[Dict], call_id: str = None):
        """Log detailed message exchange with LLM."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            exchange_data = {
                "timestamp": timestamp,
                "direction": direction,
                "call_id": call_id,
                "messages": messages
            }
            json_content = json.dumps(exchange_data, indent=2)
            self._write_to_file('messages.log', json_content)
    
    def log_error(self, message: str, exit_code: int = 1):
        """Log error message and exit."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"[{timestamp}] ERROR: {message}"
        
        # Always write to errors.log if logging is enabled
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._write_to_file('errors.log', error_msg)
        
        # Always write to STDERR (all modes)
        print(f"Error: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold red]Error: {message}[/bold red]")
        
        # Exit with error code
        sys.exit(exit_code)
    
    def log_warning(self, message: str):
        """Log warning message."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        warning_msg = f"[{timestamp}] WARNING: {message}"
        
        # Write to errors.log if logging is enabled
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._write_to_file('errors.log', warning_msg)
        
        # Always write to STDERR
        print(f"Warning: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold yellow]Warning: {message}[/bold yellow]")
    
    # UI and formatting methods (for execution.log and debug STDERR)
    def print_header(self, filename: str):
        """Print the execution header."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            header = f"{TOP_LEFT}{HORIZONTAL * 2}{os.path.basename(filename):{HORIZONTAL}<{self.terminal_width - 4}}{TOP_RIGHT}"
            self.log_execution(header)
    
    def print_footer(self):
        """Print the execution footer."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            footer = f"{BOTTOM_LEFT}{HORIZONTAL * (self.terminal_width - 2)}{BOTTOM_RIGHT}"
            self.log_execution(footer)
    
    def print_statement(self, msg_no: int, keyword: str, value: str):
        """Print a statement in the standard format."""
        if self.mode not in [LogMode.LOG, LogMode.DEBUG]:
            return
            
        line_len = self.terminal_width - 14
        header = f"{VERTICAL}{msg_no:02} {keyword:<8} "
        
        if not value:
            value = " "
        lines = value.split("\n")
        
        for line in lines:
            while len(line) > 0:
                print_line = f"{line:<{line_len}}{VERTICAL}"
                self.log_execution(f"{header}{print_line}")
                header = f"{VERTICAL}            "
                line = line[line_len:]
    
    def print_exception(self):
        """Print exception information."""
        import traceback
        exc_text = traceback.format_exc()
        
        # Log to errors.log
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._write_to_file('errors.log', exc_text)
        
        # Always print to STDERR
        traceback.print_exc(file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print_exception(show_locals=True)
    
    def close(self):
        """Close all log files."""
        for file_handle in self.log_files.values():
            if hasattr(file_handle, 'close'):
                file_handle.close()
        self.log_files.clear()

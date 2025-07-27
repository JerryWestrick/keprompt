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
    - statements.log: Statement-by-statement debug
    - functions.log: Function calls and returns
    - variables.log: Variable substitutions
    - errors.log: Errors and warnings
    """
    
    def __init__(self, prompt_name: str, mode: LogMode = LogMode.PRODUCTION):
        """
        Initialize the structured logger.
        
        Args:
            prompt_name: Name of the prompt (without .prompt extension)
            mode: Logging mode (production, log, or debug)
        """
        self.prompt_name = prompt_name
        self.mode = mode
        
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
            'statements.log',
            'functions.log',
            'errors.log'
        ]
        
        # Setup logging if needed
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._setup_logging()
    
    def _setup_logging(self):
        """Setup the logging directory and create all log files."""
        # Create log directory path
        self.log_directory = Path(f"prompts/logs_{self.prompt_name}")
        
        # Delete existing directory if it exists
        if self.log_directory.exists():
            shutil.rmtree(self.log_directory)
        
        # Create fresh directory
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Create all log files with headers
        for log_file_name in self.log_file_names:
            log_file_path = self.log_directory / log_file_name
            # Create file with header instead of just touch
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
        """Log statement execution details."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        statement_info = f"[{timestamp}] [{msg_no:02d}] {keyword}: {value}"
        self._write_to_file('statements.log', statement_info)
    
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
    
    def log_variable_assignment(self, variable: str, value: str):
        """Log variable assignment to statements.log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] VARIABLE: {variable} = {value}"
        self._write_to_file('statements.log', log_entry)

    def log_variable_retrieval(self, variable: str, value: str):
        """Log variable retrieval/substitution to statements.log."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] VARIABLE: {variable} <== {value}"
        self._write_to_file('statements.log', log_entry)
    
    def log_conversation(self, conversation_data):
        """Log conversation messages to JSON file."""
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            json_content = json.dumps(conversation_data, indent=2)
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

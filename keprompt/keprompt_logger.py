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
    PRODUCTION = "production"  # Clean STDOUT only
    LOG = "log"               # Files only, silent execution
    DEBUG = "debug"           # Files + rich STDERR output


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
    Standard logging system for keprompt using Python's logging module.
    
    Creates a single log file with format: [timestamp][prompt-id][log-level]> message
    Supports multi-process safe logging with proper log levels.
    """
    
    def __init__(self, prompt_name: str, mode: LogMode = LogMode.PRODUCTION, log_identifier: str = None):
        """
        Initialize the standard logger.
        
        Args:
            prompt_name: Name of the prompt (without .prompt extension)
            mode: Logging mode (production, log, or debug)
            log_identifier: Custom identifier for log directory (if None, uses prompt_name)
        """
        self.prompt_name = prompt_name
        self.mode = mode
        self.log_identifier = log_identifier if log_identifier else prompt_name
        self.prompt_id = ""  # Will be set when we get the UUID
        self.base_prompt_id = ""  # Base prompt ID without exec/init suffixes
        
        # Initialize console for STDERR output
        self.console = Console(stderr=True)
        self.terminal_width = self.console.size.width
        
        # Track next message number to assign (for sequential numbering)
        self.next_msg_number = 1
        
        # Setup logging if needed
        self.logger = None
        self.context_filter = None
        if self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self._setup_logging()
    
    def _setup_logging(self):
        """Setup the standard Python logger with dual handlers: Rich for console, clean text for files."""
        # Create log directory path using the log identifier
        log_directory = Path(f"prompts/logs-{self.log_identifier}")
        log_directory.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(f"keprompt.{self.log_identifier}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create context filter
        self.context_filter = PromptContextFilter(self.prompt_id)
        
        # 1. File handler - clean text for log files
        log_file = log_directory / "keprompt.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.DEBUG)
        
        # File formatter - clean text without colors
        file_formatter = logging.Formatter('[%(asctime)s][%(prompt_id)s][%(levelname)s]> %(message)s',
                                         datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(self.context_filter)
        
        # Add file handler
        self.logger.addHandler(file_handler)
        
        # 2. Rich handler - enhanced console output (only in DEBUG mode)
        if self.mode == LogMode.DEBUG:
            rich_handler = RichHandler(
                console=self.console,
                show_time=True,
                show_level=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True
            )
            rich_handler.setLevel(logging.DEBUG)
            
            # Rich formatter - simpler format since Rich adds its own styling
            rich_formatter = logging.Formatter('[%(prompt_id)s] %(message)s')
            rich_handler.setFormatter(rich_formatter)
            rich_handler.addFilter(self.context_filter)
            
            # Add rich handler
            self.logger.addHandler(rich_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def set_prompt_id(self, prompt_id: str):
        """Set the prompt ID for all subsequent log entries."""
        self.prompt_id = prompt_id
        
        # Extract base prompt ID (remove -exec/-init suffixes for statement logging)
        if '-' in prompt_id:
            self.base_prompt_id = prompt_id.split('-')[0]
        else:
            self.base_prompt_id = prompt_id
            
        if self.context_filter:
            self.context_filter.prompt_id = prompt_id
    
    def _write_to_stderr(self, message: str):
        """Write message to STDERR using Rich console."""
        if self.mode == LogMode.DEBUG:
            self.console.print(message)
    
    def _log(self, level: int, message: str):
        """Internal logging method."""
        if self.logger and self.mode in [LogMode.LOG, LogMode.DEBUG]:
            self.logger.log(level, message)
    
    def _log_with_base_id(self, level: int, message: str):
        """Internal logging method using base prompt ID (for statements)."""
        if self.logger and self.mode in [LogMode.LOG, LogMode.DEBUG]:
            # Temporarily switch to base prompt ID
            original_prompt_id = self.context_filter.prompt_id
            self.context_filter.prompt_id = self.base_prompt_id
            self.logger.log(level, message)
            # Restore original prompt ID
            self.context_filter.prompt_id = original_prompt_id
    
    # Core logging methods with custom levels
    def log_info(self, message: str):
        """Log general information (statement execution)."""
        # Remove Rich markup and table formatting from message for clean logging
        import re
        clean_message = re.sub(r'\[/?[^\]]*\]', '', message)  # Remove Rich markup
        clean_message = re.sub(r'│\s*', '', clean_message)    # Remove table prefix
        clean_message = re.sub(r'\s*│\s*$', '', clean_message)  # Remove table suffix
        clean_message = clean_message.strip()  # Remove extra whitespace
        self._log(logging.INFO, clean_message)
    
    def log_debug(self, message: str):
        """Log debug information (detailed execution flow)."""
        self._log(logging.DEBUG, message)
    
    def log_llm(self, message: str):
        """Log LLM API calls, tokens, costs."""
        self._log(LLM_LEVEL, message)
    
    def log_func(self, message: str):
        """Log function calls and results."""
        self._log(FUNC_LEVEL, message)
    
    def log_msg(self, message: str):
        """Log message exchanges."""
        self._log(MSG_LEVEL, message)
    
    def log_error(self, message: str, exit_code: int = 1):
        """Log error message and exit."""
        self._log(logging.ERROR, message)
        
        # Always write to STDERR (all modes)
        print(f"Error: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold red]Error: {message}[/bold red]")
        
        # Exit with error code
        sys.exit(exit_code)
    
    def log_warning(self, message: str):
        """Log warning message."""
        self._log(logging.WARNING, message)
        
        # Always write to STDERR
        print(f"Warning: {message}", file=sys.stderr)
        
        # Rich formatting in debug mode
        if self.mode == LogMode.DEBUG:
            self.console.print(f"[bold yellow]Warning: {message}[/bold yellow]")
    
    # Convenience methods for common logging patterns
    def log_statement(self, msg_no: int, keyword: str, value: str):
        """Log statement execution using base prompt ID."""
        # Remove Rich markup from message for clean logging
        import re
        if value:
            clean_message = re.sub(r'\[/?[^\]]*\]', '', f"{keyword} {value}")
        else:
            clean_message = re.sub(r'\[/?[^\]]*\]', '', f"{keyword}")
        
        self._log_with_base_id(logging.INFO, clean_message)
    
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
        
        # If the result contains an error, also write to stderr
        if isinstance(result, str) and ("Error executing" in result or "ERROR:" in result):
            print(f"Function Error: {function_name}({args}) -> {result}", file=sys.stderr)
    
    def log_execution_flow(self, direction: str, message: str):
        """Log execution flow (Call-01 <--, Call-01 -->)."""
        self.log_debug(f"{direction} {message}")
    
    def log_total_costs(self, total_tokens_in: int, total_tokens_out: int, total_cost_in: float, total_cost_out: float):
        """Log total costs when exiting keprompt."""
        total_cost = total_cost_in + total_cost_out
        self.log_llm(f"SESSION TOTAL: Tokens In: {total_tokens_in}, Out: {total_tokens_out}, Cost In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f}, Total: ${total_cost:.6f}")
        
        # Also print to stderr for immediate visibility
        print(f"Session Total Cost: ${total_cost:.6f} (In: ${total_cost_in:.6f}, Out: ${total_cost_out:.6f})", file=sys.stderr)
    
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
        
        # Determine how many messages are new (only log new messages)
        current_msg_count = len(messages)
        messages_to_log = messages[self.next_msg_number - 1:]  # Get only new messages
        
        # Log each new message individually with sequential numbering
        import json
        for msg in messages_to_log:
            msg_num = f"{self.next_msg_number:02d}"
            try:
                msg_json = json.dumps(msg, ensure_ascii=False)
                self.log_msg(f"{msg_num}: {msg_json}")
            except (TypeError, ValueError):
                # Fallback if message isn't JSON serializable
                self.log_msg(f"{msg_num}: {str(msg)}")
            
            self.next_msg_number += 1
    
    def log_conversation(self, conversation_data: dict):
        """Log conversation data."""
        self.log_msg(f"Conversation logged: {len(conversation_data.get('messages', []))} messages")
    
    def close(self):
        """Close the logger and cleanup handlers."""
        if self.logger:
            for handler in self.logger.handlers:
                handler.close()
            self.logger.handlers.clear()


# Backward compatibility aliases (will be removed in future versions)
KepromptLogger = StandardLogger

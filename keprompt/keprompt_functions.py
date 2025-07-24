import platform
import subprocess
import sys
from typing import Any, Dict

from rich.console import Console
from rich.prompt import Prompt
from rich.theme import Theme
from rich.table import Table

from .keprompt_util import backup_file
from .function_loader import FunctionLoader

console = Console()

# Define custom theme for prompts
theme = Theme({"prompt": "bold blue", "answer": "italic cyan"})
question_console = Console(theme=theme)


def get_webpage_content(url: str) -> str:
    """
    Fetches the content of a webpage and converts it to text.

    Args:
        url (str): The URL of the webpage to fetch.

    Returns:
        str: The text content of the webpage.

    Raises:
        Exception: If there is an error fetching the URL.
    """
    command = f"wget2 --content-on-error -O - {url} | html2text"

    try:
        process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or e.stdout.strip()
        raise Exception(f"Error fetching URL '{url}': {error_msg}") from e


def readfile(filename: str) -> str:
    """
    Reads the contents of a local file.

    Args:
        filename (str): The name of the file to read.

    Returns:
        str: The contents of the file.

    Exits:
        Exits the program if the file cannot be read.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as err:
        console.print(f"Error accessing file '{filename}': {err}\n\n", style="bold red")
        console.print_exception()
        sys.exit(9)


def askuser(question: str) -> str:
    """
    Prompts the user for input with enhanced formatting.

    Args:
        question (str): The question to present to the user.

    Returns:
        str: The user's response.
    """
    return Prompt.ask(f"[prompt]{question}[/prompt]", console=question_console)


def wwwget(url: str) -> Any:
    """
    Retrieves the content of a webpage.

    Args:
        url (str): The URL of the webpage to retrieve.

    Returns:
        str: The content of the webpage or an error dictionary.
    """
    try:
        return get_webpage_content(url)
    except Exception as err:
        console.print(f"Error while retrieving URL '{url}': {err}", style="bold red")
        return {
            'role': "function",
            'name': 'wwwget',
            'content': f'ERROR: URL not returned: {url}'
        }


def writefile(filename: str, content: str) -> str:
    """
    Writes content to a file with versioning.

    Args:
        filename (str): The name of the file to write.
        content (str): The content to write to the file.

    Returns:
        str: The path of the written file.
    """
    new_filename = backup_file(filename)

    try:
        with open(new_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Content written to file '{new_filename}'"
    except Exception as e:
        console.print(f"Failed to write to file '{new_filename}': {e}", style="bold red")
        raise

import base64

def write_base64_file(filename: str, base64_str: str) -> str:
    """
    Decodes a base64 string and writes the decoded content to a file with versioning.

    Args:
        filename (str): The name of the file to write.
        base64_str (str): The base64 encoded content to write to the file.

    Returns:
        str: The path of the written file.
    """
    new_filename = backup_file(filename)

    try:
        decoded_content = base64.b64decode(base64_str)
        with open(new_filename, 'wb') as f:
            f.write(decoded_content)
        return f"Content written to file '{new_filename}'"
    except Exception as e:
        console.print(f"Failed to write to file '{new_filename}': {e}", style="bold red")
        raise

def execcmd(cmd: str) -> str:
    """
    Executes a shell command and returns its output.

    Args:
        cmd (str): The command to execute.

    Returns:
        str: The standard output or error message.
    """
    sanitized_cmd = cmd.strip('\"\'') if cmd and cmd[0] in {'"', "'"} else cmd

    try:
        result = subprocess.run(
            ['/bin/sh', '-c', sanitized_cmd],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr.strip()}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Global function loader instance
_function_loader = None
_function_data = None

def get_function_loader():
    """Get or create the global function loader instance."""
    global _function_loader
    if _function_loader is None:
        _function_loader = FunctionLoader()
    return _function_loader

def load_external_functions():
    """Load external functions and return tools array and function map."""
    global _function_data
    if _function_data is None:
        loader = get_function_loader()
        _function_data = loader.load_functions()
    return _function_data

def execute_external_function(function_name: str, arguments: Dict[str, Any]) -> str:
    """Execute an external function."""
    function_data = load_external_functions()
    function_map = function_data["function_map"]
    
    loader = get_function_loader()
    return loader.execute_function(function_name, arguments, function_map)

# Load external functions
_external_function_data = load_external_functions()

# Use external function definitions
DefinedToolsArray = _external_function_data["tools_array"]

# Create function mapping that uses external execution
def create_external_function_wrapper(func_name: str):
    """Create a wrapper function that calls external executable."""
    def wrapper(**kwargs):
        return execute_external_function(func_name, kwargs)
    return wrapper

# Build DefinedFunctions dictionary from external functions
DefinedFunctions: Dict[str, Any] = {}
for tool in DefinedToolsArray:
    func_name = tool["function"]["name"]
    DefinedFunctions[func_name] = create_external_function_wrapper(func_name)

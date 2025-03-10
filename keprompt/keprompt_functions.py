import platform
import subprocess
import sys
from typing import Any, Dict

from rich.console import Console
from rich.prompt import Prompt
from rich.theme import Theme
from rich.table import Table

from .keprompt_util import backup_file

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


# Determine the operating system descriptor
os_descriptor = platform.platform()

# Define available tools
DefinedToolsArray = [
    {   'type': 'function',
        'function': {
            "name": "readfile",
            "description": "Read the contents of a named file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to read",
                    },
                },
                "required": ["filename"],
                "additionalProperties": False
            },
        }
    },
    {
        'type': 'function',
        'function': {
            "name": "wwwget",
            "description": "Read a webpage URL and return the contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the web page to read",
                    },
                },
                "required": ["url"],
                "additionalProperties": False
            },
        }
    },
    {   'type': 'function',
        'function': {
            "name": "writefile",
            "description": "Write the contents to a named file on the local file system",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to be written to the file",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False
            },
        }
    },
    {
        'type': 'function',
        'function': {
            "name": "execcmd",
            "description": f"Execute a command on the local {os_descriptor} system",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to be executed",
                    },
                },
                "required": ["cmd"],
                "additionalProperties": False
            },
        }
    },
    {   'type': 'function',
        'function': {
            "name": "askuser",
            "description": "Get clarification by asking the user a question",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask the user",
                    },
                },
                "required": ["question"],
                "additionalProperties": False
            },
        }
    },

    {   'type': 'function',
         'function': {
             "name": "write_base64_file",
             "description": "Decode base64 content and write the decoded data to a named file on the local file system",
             "parameters": {
                 "type": "object",
                 "properties": {
                     "filename": {
                         "type": "string",
                         "description": "The name of the file to write",
                     },
                    "base64_str": {
                        "type": "string",
                        "description": "The base64 encoded content to be decoded and written to the file",
                    },
                 },
                 "required": ["filename", "base64_str"],
                 "additionalProperties": False
                },
        }
    }
]


# Mapping of function names to their implementations
DefinedFunctions: Dict[str, Any] = {
    "readfile": readfile,
    "wwwget": wwwget,
    "writefile": writefile,
    "execcmd": execcmd,
    "askuser": askuser,
    "write_base64_file": write_base64_file
}

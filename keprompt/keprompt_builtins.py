#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import base64
from pathlib import Path

def get_webpage_content(url: str) -> str:
    """Fetch webpage content and convert to text."""
    command = f"wget2 --content-on-error -O - {url} | html2text"
    try:
        process = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, check=True, text=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or e.stdout.strip()
        raise Exception(f"Error fetching URL '{url}': {error_msg}")

def readfile(filename: str) -> str:
    """Read contents of a local file."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as err:
        raise Exception(f"Error accessing file '{filename}': {err}")

def writefile(filename: str, content: str) -> str:
    """Write content to a file with versioning."""
    # Simple backup by adding .backup extension if file exists
    if os.path.exists(filename):
        backup_name = f"{filename}.backup"
        counter = 1
        while os.path.exists(backup_name):
            backup_name = f"{filename}.backup.{counter}"
            counter += 1
        os.rename(filename, backup_name)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Content written to file '{filename}'"
    except Exception as e:
        raise Exception(f"Failed to write to file '{filename}': {e}")

def write_base64_file(filename: str, base64_str: str) -> str:
    """Decode base64 string and write to file."""
    # Simple backup by adding .backup extension if file exists
    if os.path.exists(filename):
        backup_name = f"{filename}.backup"
        counter = 1
        while os.path.exists(backup_name):
            backup_name = f"{filename}.backup.{counter}"
            counter += 1
        os.rename(filename, backup_name)
    
    try:
        decoded_content = base64.b64decode(base64_str)
        with open(filename, 'wb') as f:
            f.write(decoded_content)
        return f"Content written to file '{filename}'"
    except Exception as e:
        raise Exception(f"Failed to write to file '{filename}': {e}")

def execcmd(cmd: str) -> str:
    """Execute a shell command and return output."""
    sanitized_cmd = cmd.strip('"\'') if cmd and cmd[0] in {'"', "'"} else cmd
    try:
        result = subprocess.run(
            ['/bin/sh', '-c', sanitized_cmd],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr.strip()}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def askuser(question: str) -> str:
    """Ask user for input."""
    return input(f"{question}: ")

def wwwget(url: str) -> str:
    """Retrieve webpage content."""
    try:
        return f"<<{get_webpage_content(url)}>>"
    except Exception as err:
        return f"ERROR: URL not returned: {url} - {err}"

# Function definitions for --list-functions
FUNCTION_DEFINITIONS = [
    {
        "name": "readfile",
        "description": "Read the contents of a named file",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The name of the file to read"}
            },
            "required": ["filename"],
            "additionalProperties": False
        }
    },
    {
        "name": "wwwget", 
        "description": "Read a webpage URL and return the contents",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL of the web page to read"}
            },
            "required": ["url"],
            "additionalProperties": False
        }
    },
    {
        "name": "writefile",
        "description": "Write the contents to a named file on the local file system", 
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The name of the file to write"},
                "content": {"type": "string", "description": "The content to be written to the file"}
            },
            "required": ["filename", "content"],
            "additionalProperties": False
        }
    },
    {
        "name": "execcmd",
        "description": "Execute a command on the local system",
        "parameters": {
            "type": "object", 
            "properties": {
                "cmd": {"type": "string", "description": "Command to be executed"}
            },
            "required": ["cmd"],
            "additionalProperties": False
        }
    },
    {
        "name": "askuser",
        "description": "Get clarification by asking the user a question",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Question to ask the user"}
            },
            "required": ["question"],
            "additionalProperties": False
        }
    },
    {
        "name": "write_base64_file",
        "description": "Decode base64 content and write the decoded data to a named file",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The name of the file to write"},
                "base64_str": {"type": "string", "description": "The base64 encoded content"}
            },
            "required": ["filename", "base64_str"],
            "additionalProperties": False
        }
    }
]

# Function mapping
FUNCTIONS = {
    "readfile": readfile,
    "wwwget": wwwget, 
    "writefile": writefile,
    "execcmd": execcmd,
    "askuser": askuser,
    "write_base64_file": write_base64_file
}

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-functions":
            print(json.dumps(FUNCTION_DEFINITIONS))
            return
        elif sys.argv[1] == "--version":
            print("keprompt_builtins version 1.0")
            return
        
        # Function execution: ./keprompt_builtins function_name < json_args
        function_name = sys.argv[1]
        if function_name not in FUNCTIONS:
            print(f"Error: Unknown function '{function_name}'", file=sys.stderr)
            sys.exit(1)
            
        try:
            # Read JSON arguments from stdin
            json_input = sys.stdin.read().strip()
            if json_input:
                arguments = json.loads(json_input)
            else:
                arguments = {}
                
            # Execute the function
            result = FUNCTIONS[function_name](**arguments)
            print(result)
            
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: keprompt_builtins [--list-functions|--version|function_name]", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

# Creating keprompt External Functions

## Context Overview

**keprompt** is an AI prompt management system that allows extending its capabilities through **external functions**. These are standalone executable files that keprompt discovers, loads, and makes available to its LLM for tool use during conversations.

**Integration flow:**
1. Create executable in `prompts/functions/` directory
2. keprompt auto-discovers it on startup
3. Calls `--list-functions` to get function definitions
4. LLM can now call your functions during conversations

## External Function Protocol

Your executable must implement three command-line modes:

### 1. List Functions
```bash
./prompts/functions/your_executable --list-functions
```
Output JSON array of function definitions to stdout in **OpenAI function calling format**:
```json
[
  {
    "name": "function_name",
    "description": "Clear description for LLM understanding",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string|integer|boolean|array|object",
          "description": "Parameter purpose"
        }
      },
      "required": ["param_name"],
      "additionalProperties": false
    }
  }
]
```

### 2. Version (Optional)
```bash
./prompts/functions/your_executable --version
```
Output version string to stdout (e.g., "1.0")

### 3. Execute Function
```bash
echo '{"param_name": "value"}' | ./prompts/functions/your_executable function_name
```
- **Input**: JSON arguments via stdin
- **Output**: Function result to stdout (on success, exit 0)
- **Errors**: Error message to stderr (non-zero exit code)

## Critical Requirements

### Working Directory
**Your executable runs from the PROJECT ROOT**, not from `prompts/functions/`.

```python
# User calls: readfile("data/file.txt")
# Your executable runs with cwd = /path/to/project
# NOT /path/to/project/prompts/functions

# CORRECT:
with open("data/file.txt") as f:  # Relative to project root
    ...

# WRONG:
with open("../../data/file.txt") as f:  # Don't assume functions/ directory
    ...
```

### Executable Permissions
```bash
chmod +x prompts/functions/your_executable
```

### JSON Format
- Function definitions must be valid JSON
- Use `json.dumps()` or equivalent, not string repr
- `"additionalProperties": false` is required in parameters

### Error Handling
```python
# SUCCESS
print(result)
sys.exit(0)

# FAILURE
print(f"Error: {error_message}", file=sys.stderr)
sys.exit(1)
```

## Complete Python Template

```python
#!/usr/bin/env python3
import json
import sys

def your_function(param1: str, param2: int) -> str:
    """Implement your function logic."""
    return f"Result: {param1} * {param2}"

FUNCTION_DEFINITIONS = [
    {
        "name": "your_function",
        "description": "Clear description of what this does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "First parameter purpose"
                },
                "param2": {
                    "type": "integer",
                    "description": "Second parameter purpose"
                }
            },
            "required": ["param1", "param2"],
            "additionalProperties": False
        }
    }
]

FUNCTIONS = {
    "your_function": your_function
}

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-functions":
            print(json.dumps(FUNCTION_DEFINITIONS))
            return
        elif sys.argv[1] == "--version":
            print("your_tool version 1.0")
            return
        
        # Execute function
        function_name = sys.argv[1]
        if function_name not in FUNCTIONS:
            print(f"Error: Unknown function '{function_name}'", file=sys.stderr)
            sys.exit(1)
            
        try:
            json_input = sys.stdin.read().strip()
            arguments = json.loads(json_input) if json_input else {}
            result = FUNCTIONS[function_name](**arguments)
            print(result)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: your_tool [--list-functions|--version|function_name]", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Bash Template

```bash
#!/bin/bash

case "$1" in
    --list-functions)
        cat << 'EOF'
[
  {
    "name": "your_function",
    "description": "What this function does",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {"type": "string", "description": "Parameter purpose"}
      },
      "required": ["param1"],
      "additionalProperties": false
    }
  }
]
EOF
        ;;
    --version)
        echo "your_tool version 1.0"
        ;;
    your_function)
        read -r json_input
        param1=$(echo "$json_input" | jq -r '.param1')
        
        # Your logic here
        echo "Result: $param1"
        ;;
    *)
        echo "Usage: $0 [--list-functions|--version|function_name]" >&2
        exit 1
        ;;
esac
```

## Installation Steps

1. Create executable:
```bash
vim prompts/functions/my_tool
chmod +x prompts/functions/my_tool
```

2. Test standalone:
```bash
# Test listing
./prompts/functions/my_tool --list-functions | jq .

# Test execution
echo '{"param": "value"}' | ./prompts/functions/my_tool function_name
```

3. Start keprompt - it will auto-discover and load your functions

## Common Pitfalls

### ❌ Wrong: Assumes running from prompts/functions/
```python
with open("../../data/file.txt")  # WRONG
```

### ✅ Correct: Uses project root context
```python
with open("data/file.txt")  # CORRECT
```

### ❌ Wrong: Not executable
```bash
# keprompt won't discover it
ls -l prompts/functions/my_tool  # -rw-r--r--
```

### ✅ Correct: Executable permissions
```bash
chmod +x prompts/functions/my_tool
ls -l prompts/functions/my_tool  # -rwxr-xr-x
```

### ❌ Wrong: Invalid JSON
```python
print({'result': 123})  # Outputs: {'result': 123}
```

### ✅ Correct: Valid JSON
```python
print(json.dumps({'result': 123}))  # Outputs: {"result": 123}
```

## Best Practices

**Clear Descriptions**: LLM needs to understand when to use your function
```json
{
  "description": "Search customer database by name, email, or ID"
}
```

**Type Validation**: Validate input types before use
```python
if not isinstance(count, int):
    raise ValueError("count must be an integer")
```

**Meaningful Errors**: Help debugging
```python
raise Exception(f"File not found: {filename}")  # GOOD
raise Exception("Error")  # BAD
```

**Timeout Awareness**: Functions have 30-second timeout
- Design for quick execution
- For long operations, return job ID and use polling

## Multi-Language Support

External functions work in any language:

```go
// Go example structure
package main
import ("encoding/json"; "os")

func main() {
    if len(os.Args) > 1 && os.Args[1] == "--list-functions" {
        // Output function definitions JSON
    }
    // Handle function execution
}
```

```rust
// Rust example structure
use serde_json::Value;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 && args[1] == "--list-functions" {
        // Output function definitions JSON
    }
}
```

## Quick Checklist

Before deployment, verify:
- [ ] Executable in `prompts/functions/` directory
- [ ] Implements `--list-functions` returning valid JSON
- [ ] Accepts function name as first argument
- [ ] Reads JSON from stdin, writes result to stdout
- [ ] Errors go to stderr with non-zero exit
- [ ] Works from project root directory context
- [ ] Function definitions have `"additionalProperties": false`
- [ ] Descriptions are clear for LLM understanding
- [ ] Tested standalone before integration
- [ ] `chmod +x` applied

## Troubleshooting

**Function not appearing**: Check `prompts/functions/functions.json` - if your function isn't listed, verify executable permissions and `--list-functions` output

**Wrong file paths**: Your executable runs from project root, not from `prompts/functions/`

**JSON errors**: Validate output with `jq`: `./your_tool --list-functions | jq .`

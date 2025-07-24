# KePrompt

A powerful prompt engineering and LLM interaction tool designed for developers, researchers, and AI practitioners to streamline communication with various Large Language Model providers.

## Overview

KePrompt provides a flexible framework for crafting, executing, and iterating on LLM prompts across multiple AI providers.

## Philosophy
 - A domain-specific language allows for easy prompt definition and development.  
 - This is translated into a **_universal prompt structure_** upon which the code is implemented.  
 - Different company interfaces translate **_universal prompt structure_** to company specific prompts and back.

## Features

- **Multi-Provider Support**: Interfaces with Anthropic, OpenAI, Google, MistralAI, XAI, DeepSeek, and more
- **Prompt Language**: Simple yet powerful DSL for defining prompts
- **Function Calling**: Integrated tools for file operations, web requests, and user interaction
- **User-Defined Functions**: Create custom functions in any programming language that LLMs can call
- **Language Agnostic Extensions**: Write functions in Python, Shell, Go, Rust, or any executable language
- **Function Override System**: Replace built-in functions with custom implementations
- **API Key Management**: Secure storage of API keys via system keyring
- **Rich Terminal Output**: Terminal-friendly visuals with color-coded responses
- **Logging**: Automatic conversation and response logging
- **Cost Tracking**: Token usage and cost estimation for API calls
- **Extensive Debugging Support**: different debugging options to aid in Prompt development
- **File Versioning**: Renames files adding version number instead of overwriting to aid in development

## Installation

```bash
# Install from PyPI
pip install keprompt

# Install from source
git clone https://github.com/yourusername/keprompt.git
cd keprompt

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install for development
pip install -e .

# For development with additional tools
pip install -r requirements-dev.txt
```

### Quick Start
```bash 
#!/bin/bash

# Create prompts directory if it doesn't exist
mkdir -p prompts

# Write content to Test.prompt
cat > prompts/Test.prompt << 'EOL'
.# Make snake program with gpt-4o
.llm "model": "gpt-4o"
.system
You are to provide short concise answers.
.user
Generate the python code implementing the game of snake, and write the code to the file snake.py using the provided writefile function.
.exec
EOL

echo "Created prompts/Test.prompt successfully."
```

```bash 
keprompt -e Test --debug Messages
```

#### Output
```aiignore
(keprompt-py3.10) jerry@desktop:~/PycharmProjects/keprompt$ keprompt -e Test --debug Messages
╭──Test.prompt───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│00 .#       Make snake program with gpt-4o                                                                                                                                                                                                  │
│01 .llm     "model": "gpt-4o"                                                                                                                                                                                                               │
│02 .system  You are to provide short concise answers.                                                                                                                                                                                       │
│03 .user    Generate the python code implementing the game of snake, and write the code to the file snake.py using the provided writefile function.                                                                                         │
│04 .exec    Calling OpenAI::gpt-4o

│╭─── Messages Sent to gpt-4o ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮│
││ system    Text(You are to provide short concise answers.)                                                                                                                                                                                ││
││ user      Text(Generate the python code implementing the game of snake, and write the code to the file snake.py using the provided writefile function.)                                                                                  ││
│╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯│
│            Call-01 Elapsed: 17.14 seconds 0.00 tps                                                                                                                                                                                          
│
│╭─── Messages Sent to gpt-4o ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮│
││ system    Text(You are to provide short concise answers.)                                                                                                                                                                                ││
││ user      Text(Generate the python code implementing the game of snake, and write the code to the file snake.py using the provided writefile function.)                                                                                  ││
││ assistant Call writefile(id=call_O2R056UlBxXZfzBXs7ESAjk7, "filename": "snake.py", "content": "import pygame\nimport time...")                                                                                                           ││
││ tool      Rtn  writefile(id=call_O2R056UlBxXZfzBXs7ESAjk7, content:Content written to file './snake.py')                                                                                                                                 ││
│╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯│
│            Call-02 Elapsed: 1.08 seconds 0.00 tps                                                                                                                                                                                           
│
│╭─── Messages Received from gpt-4o ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮│
││ system    Text(You are to provide short concise answers.)                                                                                                                                                                                ││
││ user      Text(Generate the python code implementing the game of snake, and write the code to the file snake.py using the provided writefile function.)                                                                                  ││
││ assistant Call writefile(id=call_O2R056UlBxXZfzBXs7ESAjk7, "filename": "snake.py", "content": "import pygame\nimport time...")                                                                                                           ││
││ tool      Rtn  writefile(id=call_O2R056UlBxXZfzBXs7ESAjk7, content:Content written to file './snake.py')                                                                                                                                 ││
││ assistant Text(The Snake game code has been successfully written to the file `snake.py`. You can run it using Python to play the game!)                                                                                                  ││
│╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯│
│04 .exec    18.31 secs output tokens 0 at 0.00 tps                                                                                                          │
│04 .exec   Tokens In=0($0.0000), Out=0($0.0000) Total=$0.0000                                                                                                                                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Wrote logs/Test.svg to disk

```


## Command Line Options
```
keprompt [-h] [-v] [--param key value] [-m] [-f] [-p [PROMPTS]] [-c [CODE]] [-l [LIST]] [-e [EXECUTE]] [-k] [-d {Statements,Prompt,LLM,Functions,Messages} [...]] [-r] [--init] [--check-builtins] [--update-builtins]
```

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --version` | Show version information and exit |
| `--param key value` | Add key/value pairs for substitution in prompts |
| `-m, --models` | List all available LLM models |
| `-f, --functions` | List all available functions (built-in + user-defined) |
| `-p, --prompts [PATTERN]` | List available prompt files (default: all) |
| `-c, --code [PATTERN]` | Show prompt code/commands in files |
| `-l, --list [PATTERN]` | List prompt file content line by line |
| `-e, --execute [PATTERN]` | Execute one or more prompt files |
| `-k, --key` | Add or update API keys for LLM providers |
| `-d, --debug {Statements,Prompt,LLM,Functions,Messages}` | Enable debug output for specific components |
| `-r, --remove` | Remove all backup files with .~nn~ pattern |
| `--init` | Initialize prompts and functions directories |
| `--check-builtins` | Check for built-in function updates |
| `--update-builtins` | Update built-in functions |

## Prompt Language

keprompt uses a simple line-based language for defining prompts. Each line either begins with a command (prefixed with `.`) or is treated as content. Here are the available commands:

| Command | Description |
|---------|-------------|
| `.#` | Comment (ignored) |
| `.assistant` | Define assistant message |
| `.clear ["pattern1", ...]` | Delete files matching pattern(s) |
| `.cmd function(arg=value)` | Execute a predefined function |
| `.debug ["element1", ...]` | Display debug information |
| `.exec` | Execute the prompt (send to LLM) |
| `.exit` | Exit execution |
| `.image filename` | Include an image in the message |
| `.include filename` | Include text file content |
| `.llm {options}` | Configure LLM (model, temperature, etc.) |
| `.system text` | Define system message |
| `.text text` | Add text to the current message |
| `.user text` | Define user message |

### Variable Substitution

You can use `<<variable>>` syntax for substituting variables in prompts. Variables can be defined using the `--param` option.

## Available Functions

keprompt provides several built-in functions that can be called from prompts:

| Function | Description |
|----------|-------------|
| `readfile(filename)` | Read content from a file |
| `writefile(filename, content)` | Write content to a file |
| `write_base64_file(filename, base64_str)` | Write decoded base64 content to a file |
| `wwwget(url)` | Fetch content from a web URL |
| `execcmd(cmd)` | Execute a shell command |
| `askuser(question)` | Prompt the user for input |

## User-Defined Functions

keprompt supports custom user-defined functions that can be written in any programming language. These functions are automatically discovered and made available to LLMs alongside built-in functions.

### Getting Started with Custom Functions

1. **Initialize your project** (if not already done):
   ```bash
   keprompt --init
   ```

2. **Create a custom function executable** in `./prompts/functions/`:
   ```bash
   # Create a Python function
   cat > prompts/functions/my_tools << 'EOF'
   #!/usr/bin/env python3
   import json, sys
   
   def get_schema():
       return [{
           "name": "hello",
           "description": "Say hello to someone",
           "parameters": {
               "type": "object",
               "properties": {
                   "name": {"type": "string", "description": "Name to greet"}
               },
               "required": ["name"]
           }
       }]
   
   if sys.argv[1] == "--list-functions":
       print(json.dumps(get_schema()))
   elif sys.argv[1] == "hello":
       args = json.loads(sys.stdin.read())
       print(f"Hello, {args['name']}!")
   EOF
   
   # Make it executable
   chmod +x prompts/functions/my_tools
   ```

3. **Verify function discovery**:
   ```bash
   keprompt --functions
   ```

4. **Use in prompts**:
   ```bash
   cat > prompts/test.prompt << 'EOF'
   .llm {"model": "gpt-4o-mini"}
   .user Please use the hello function to greet me. My name is Alice.
   .exec
   EOF
   
   keprompt -e test
   ```

### Function Interface Specification

All user-defined functions must follow this interface:

#### Schema Discovery
Functions must support `--list-functions` to return their schema:
```bash
./my_function --list-functions
```
Returns JSON array of function definitions:
```json
[{
    "name": "function_name",
    "description": "Function description",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    }
}]
```

#### Function Execution
Functions are called with the function name and JSON arguments via stdin:
```bash
echo '{"param1": "value1"}' | ./my_function function_name
```

### Examples

#### Shell Script Function
```bash
#!/bin/bash
# File: prompts/functions/git_tools

if [ "$1" = "--list-functions" ]; then
    cat << 'EOF'
[{
    "name": "git_status",
    "description": "Get git repository status",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository path", "default": "."}
        }
    }
}]
EOF
    exit 0
fi

if [ "$1" = "git_status" ]; then
    ARGS=$(cat)
    PATH_ARG=$(echo "$ARGS" | jq -r '.path // "."')
    cd "$PATH_ARG" && git status --porcelain
fi
```

#### Python Function with Multiple Functions
```python
#!/usr/bin/env python3
# File: prompts/functions/math_tools
import json, sys, math

FUNCTIONS = {
    "add": {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    },
    "sqrt": {
        "name": "sqrt",
        "description": "Calculate square root",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "Number to calculate square root of"}
            },
            "required": ["x"]
        }
    }
}

def add(a, b):
    return f"The sum of {a} and {b} is {a + b}"

def sqrt(x):
    return f"The square root of {x} is {math.sqrt(x)}"

if len(sys.argv) > 1:
    if sys.argv[1] == "--list-functions":
        print(json.dumps(list(FUNCTIONS.values())))
    elif sys.argv[1] in FUNCTIONS:
        args = json.loads(sys.stdin.read())
        if sys.argv[1] == "add":
            print(add(args["a"], args["b"]))
        elif sys.argv[1] == "sqrt":
            print(sqrt(args["x"]))
```

### Function Management

#### Override Built-in Functions
You can override built-in functions by creating executables with names that come alphabetically before `keprompt_builtins`:

```bash
# Override the built-in readfile function
cp my_custom_readfile prompts/functions/01_readfile
chmod +x prompts/functions/01_readfile
```

#### Function Discovery Rules
- Functions are loaded alphabetically by filename
- First definition wins (duplicates are ignored)
- Only executable files (+x permission) are considered
- Functions must support `--list-functions` for automatic discovery

#### Debugging Functions
```bash
# Test function schema
./prompts/functions/my_function --list-functions

# Test function execution
echo '{"param": "value"}' | ./prompts/functions/my_function function_name

# Debug function calls in prompts
keprompt -e my_prompt -d Functions
```

### Best Practices

1. **Error Handling**: Always include proper error handling in your functions
2. **Validation**: Validate input parameters before processing
3. **Documentation**: Provide clear descriptions in function schemas
4. **Testing**: Test functions independently before using in prompts
5. **Naming**: Use descriptive function and parameter names
6. **Performance**: Consider timeout implications (30-second limit)

### Advanced Features

#### Function Versioning
```bash
# Check built-in function version
keprompt --check-builtins

# Update built-in functions
keprompt --update-builtins
```

#### Multiple Functions per Executable
A single executable can provide multiple functions by checking the function name argument and implementing different behaviors.

#### Language Support
Functions can be written in any language that can:
- Accept command line arguments
- Read from stdin
- Write to stdout
- Be made executable on your system

Examples: Python, Shell, Go, Rust, Node.js, Ruby, Perl, compiled C/C++, etc.

## Supported LLM Providers

- **Anthropic**: Claude models
- **OpenAI**: GPT models including GPT-4o
- **Google**: Gemini models
- **MistralAI**: Mistral, Small, Large models
- **XAI**: Grok models
- **DeepSeek**: DeepSeek Chat and Reasoner models

Execute following command to see supported models:
```bash
keprompt -m
```

## Available Models

| Company   | Model                 | Max Token | $/mT In | $/mT Out | Input             | Output     | Functions | Cutoff   | Description                                                                          |
|-----------|-----------------------|-----------|---------|----------|-------------------|------------|-----------|----------|--------------------------------------------------------------------------------------|
| Anthropic | claude-haiku-3        | 200000    | 0.2500  | 1.2500   | Text              | Text       | Yes       | See docs | Legacy fastest model                                                                 |
|           | claude-haiku-3.5      | 200000    | 0.8000  | 4.0000   | Text+Vision       | Text       | Yes       | See docs | Fastest, most cost-effective model                                                   |
|           | claude-opus-3         | 200000    | 15.0000 | 75.0000  | Text+Vision       | Text       | Yes       | See docs | Legacy most intelligent model                                                        |
|           | claude-opus-4         | 200000    | 15.0000 | 75.0000  | Text+Vision       | Text       | Yes       | See docs | Most intelligent model for complex tasks                                             |
|           | claude-sonnet-3.7     | 200000    | 3.0000  | 15.0000  | Text+Vision       | Text       | Yes       | See docs | Legacy balanced model                                                                |
|           | claude-sonnet-4       | 200000    | 3.0000  | 15.0000  | Text+Vision       | Text       | Yes       | See docs | Optimal balance of intelligence, cost, and speed                                     |
| DeepSeek  | deepseek-chat         | 64000     | 0.2700  | 1.1000   | Text              | Text       | Yes       | See docs | High-performance model for general tasks with excellent reasoning capabilities       |
|           | deepseek-reasoner     | 64000     | 0.5500  | 2.1900   | Text              | Text       | Yes       | See docs | Advanced reasoning model with transparent thinking process                           |
| Google    | gemini-1.5-flash      | 1000000   | 0.0750  | 0.3000   | Text+Vision       | Text       | Yes       | See docs | Fastest multimodal model with great performance                                      |
|           | gemini-1.5-flash-8b   | 1000000   | 0.0375  | 0.1500   | Text+Vision       | Text       | Yes       | See docs | Smallest model for lower intelligence use cases                                      |
|           | gemini-1.5-pro        | 2000000   | 1.2500  | 5.0000   | Text+Vision       | Text       | Yes       | See docs | Highest intelligence Gemini 1.5 series model                                         |
|           | gemini-2.0-flash      | 1000000   | 0.1000  | 0.4000   | Text+Vision+Audio | Text+Image | Yes       | See docs | Most balanced multimodal model, built for the era of Agents                          |
|           | gemini-2.0-flash-lite | 1000000   | 0.0750  | 0.3000   | Text              | Text       | Yes       | See docs | Smallest and most cost effective model                                               |
|           | gemini-2.5-flash      | 1000000   | 0.3000  | 2.5000   | Text+Vision+Audio | Text       | Yes       | See docs | First hybrid reasoning model with thinking budgets                                   |
|           | gemini-2.5-flash-lite | 1000000   | 0.1000  | 0.4000   | Text+Vision+Audio | Text       | Yes       | See docs | Smallest and most cost effective model, built for at scale usage                     |
|           | gemini-2.5-pro        | 1000000   | 1.2500  | 10.0000  | Text+Vision+Audio | Text       | Yes       | See docs | State-of-the-art multipurpose model, excels at coding and complex reasoning          |
|           | gemma-3-27b           | 8192      | 0.0000  | 0.0000   | Text              | Text       | No        | See docs | Lightweight, state-of-the-art, open model                                            |
|           | gemma-3n-e4b          | 8192      | 0.0000  | 0.0000   | Text              | Text       | No        | See docs | Open model built for efficient performance on everyday devices                       |
| MistralAI | codestral             | 32000     | 0.3000  | 0.9000   | Text              | Text       | Yes       | See docs | Lightweight, fast, and proficient in over 80 programming languages                   |
|           | devstral-medium       | 128000    | 0.4000  | 2.0000   | Text              | Text       | Yes       | See docs | Enhanced model for advanced coding agents                                            |
|           | devstral-small        | 128000    | 0.1000  | 0.3000   | Text              | Text       | Yes       | See docs | The best open-source model for coding agents                                         |
|           | magistral-medium      | 128000    | 2.0000  | 5.0000   | Text              | Text       | Yes       | See docs | Thinking model excelling in domain-specific, transparent, and multilingual reasoning |
|           | magistral-small       | 128000    | 0.5000  | 1.5000   | Text              | Text       | Yes       | See docs | Thinking model excelling in domain-specific reasoning                                |
|           | ministral-3b-24.10    | 128000    | 0.0400  | 0.0400   | Text              | Text       | Yes       | See docs | Most efficient edge model                                                            |
|           | ministral-8b-24.10    | 128000    | 0.1000  | 1.0000   | Text              | Text       | Yes       | See docs | Powerful model for on-device use cases                                               |
|           | mistral-7b            | 32000     | 0.2500  | 0.2500   | Text              | Text       | Yes       | See docs | A 7B transformer model, fast-deployed and easily customisable                        |
|           | mistral-large         | 128000    | 2.0000  | 6.0000   | Text              | Text       | Yes       | See docs | Top-tier reasoning for high-complexity tasks and sophisticated problems              |
|           | mistral-medium-3      | 128000    | 0.4000  | 2.0000   | Text              | Text       | Yes       | See docs | State-of-the-art performance. Simplified enterprise deployments. Cost-efficient      |
|           | mistral-nemo          | 128000    | 0.1500  | 0.1500   | Text              | Text       | Yes       | See docs | State-of-the-art Mistral model trained specifically for code tasks                   |
|           | mistral-saba          | 32000     | 0.2000  | 0.6000   | Text              | Text       | Yes       | See docs | Custom-trained model to serve specific geographies, markets, and customers           |
|           | mistral-small-3.2     | 128000    | 0.1000  | 0.3000   | Text+Vision       | Text       | Yes       | See docs | SOTA. Multimodal. Multilingual. Apache 2.0                                           |
|           | mixtral-8x22b         | 64000     | 2.0000  | 6.0000   | Text              | Text       | Yes       | See docs | A 22B sparse Mixture-of-Experts (SMoE). Uses only 39B active parameters out of 141B  |
|           | mixtral-8x7b          | 32000     | 0.7000  | 0.7000   | Text              | Text       | Yes       | See docs | A 7B sparse Mixture-of-Experts (SMoE). Uses 12.9B active parameters out of 45B total |
|           | pixtral-12b           | 128000    | 0.1500  | 0.1500   | Text+Vision       | Text       | Yes       | See docs | Vision-capable small model                                                           |
|           | pixtral-large         | 128000    | 2.0000  | 6.0000   | Text+Vision       | Text       | Yes       | See docs | Vision-capable large model with frontier reasoning capabilities                      |
|           | voxtral-mini          | 128000    | 0.0400  | 0.0400   | Text+Audio        | Text       | Yes       | See docs | Low-latency speech recognition for edge and devices                                  |
|           | voxtral-small         | 128000    | 0.1000  | 0.3000   | Text+Audio        | Text       | Yes       | See docs | State-of-the-art performance on speech and audio understanding                       |
| OpenAI    | gpt-4.1               | 128000    | 2.0000  | 8.0000   | Text+Vision       | Text       | Yes       | See docs | Smartest model for complex tasks                                                     |
|           | gpt-4.1-mini          | 128000    | 0.4000  | 1.6000   | Text+Vision       | Text       | Yes       | See docs | Affordable model balancing speed and intelligence                                    |
|           | gpt-4.1-nano          | 128000    | 0.1000  | 0.4000   | Text              | Text       | Yes       | See docs | Fastest, most cost-effective model for low-latency tasks                             |
|           | gpt-4o                | 128000    | 5.0000  | 20.0000  | Text+Vision       | Text       | Yes       | 2023-10  | Advanced multimodal model for complex tasks                                          |
|           | gpt-4o-mini           | 128000    | 0.6000  | 2.4000   | Text+Vision       | Text       | Yes       | See docs | Affordable multimodal model                                                          |
|           | o1                    | 128000    | 3.0000  | 12.0000  | Text              | Text       | Limited   | See docs | Reasoning model for complex problems                                                 |
|           | o1-mini               | 128000    | 0.6000  | 2.4000   | Text              | Text       | Limited   | See docs | Smaller reasoning model                                                              |
|           | o3                    | 128000    | 2.0000  | 8.0000   | Text              | Text       | Yes       | See docs | Most powerful reasoning model with leading performance                               |
|           | o3-mini               | 128000    | 1.1000  | 4.4000   | Text              | Text       | Yes       | See docs | Compact reasoning model                                                              |
|           | o4-mini               | 128000    | 1.1000  | 4.4000   | Text              | Text       | Yes       | See docs | Faster, cost-efficient reasoning model                                               |
| XAI       | grok-2-1212           | 131072    | 2.0000  | 10.0000  | Text              | Text       | Yes       | See docs | Updated Grok-2 model with improved performance                                       |
|           | grok-2-vision-1212    | 131072    | 2.0000  | 10.0000  | Text+Vision       | Text       | Yes       | See docs | Vision-capable Grok-2 model                                                          |
|           | grok-3                | 131072    | 3.0000  | 15.0000  | Text+Vision       | Text       | Yes       | See docs | Flagship enterprise model with advanced reasoning                                    |
|           | grok-3-mini           | 131072    | 0.3000  | 0.5000   | Text              | Text       | Yes       | See docs | Lightweight reasoning model for cost-effective applications                          |
|           | grok-4                | 256000    | 3.0000  | 15.0000  | Text+Vision       | Text       | Yes       | See docs | The world's best model                                                               |
|           | grok-beta             | 131072    | 5.0000  | 15.0000  | Text              | Text       | Yes       | See docs | Beta version of Grok with experimental features                                      |
|           | grok-vision-beta      | 8192      | 5.0000  | 15.0000  | Text+Vision       | Text       | Yes       | See docs | Beta vision model with image understanding capabilities                              |


Run `keprompt -m` for complete details including pricing, context limits, and capabilities.

## Example Usage

### Basic Prompt Execution

```bash
# Create a prompt file
cat > prompts/example.prompt << EOL
.llm {"model": "claude-3-7-sonnet-latest"}
.system You are a helpful assistant.
.user Tell me about prompt engineering.
.exec
EOL

# Execute the prompt
keprompt -e example --debug Messages
```

### Using Variables

```bash
# Create a prompt with variables
cat > prompts/greeting.prompt << EOL
.llm {"model": "<<model>>"}
.user Hello! My name is <<name>>.
.exec
EOL

# Execute with variables
keprompt -e greeting --param name "Alice" --param model "claude-3-7-sonnet-latest"  --debug Messages
```

### Using Functions

```bash
# Create a prompt that uses functions
cat > prompts/analyze.prompt << EOL
.llm {"model": "claude-3-7-sonnet-latest"}
.user Analyze this text:
.cmd readfile(filename="data.txt")
.exec
EOL

# Execute the prompt
keprompt -e analyze  --debug Messages
```

## Working with Prompts

1. **Create** prompt files in the `prompts/` directory with `.prompt` extension
2. **List** available prompts with `keprompt -p`
3. **Examine** prompt content with `keprompt -l promptname`
4. **Execute** prompts with `keprompt -e promptname`
5. **Debug** execution with `keprompt -e promptname -d Messages LLM`

## Output and Logging

keprompt automatically saves conversation logs to the `logs/` directory:
- `logs/promptname.log`: Text log of the interaction
- `logs/promptname.svg`: SVG visualization of the conversation
- `logs/promptname_messages.json`: JSON format of all messages

## API Key Management

```bash
# Add or update API key
keprompt -k
# Select provider from the menu and enter your API key
```

## Advanced Usage

### Debugging Options

```bash
# Debug LLM API calls
This will give a full dump opn the screen of the data structure sent to API, and a full dump of its response.
 
keprompt -e example -d LLM

# Debug function calls
keprompt -e example -d Functions

# Debug everything
keprompt -e example -d Statements Prompt LLM Functions Messages
```

### Working with Multiple Prompts

```bash
# Execute all prompts matching a pattern
keprompt -e "test*"

# List all prompts with "gpt" in the name
keprompt -p "*gpt*"
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT](LICENSE)


# Todos, Errors, open points
- Done: Crash if no .prompt found
- Done: Was invalid api-key!
- Done: Added cmd arg --statements...
- 

## Release Process

To release a new version:

1. Install build tools if needed:
   ```bash
   pip install build twine
   ```

2. Run the release script:
   ```bash
   ./release.py
   ```
   
   This will:
   - Check for uncommitted changes in Git
   - Verify if the current version is correct
   - Build distribution packages
   - Upload to TestPyPI (optional)
   - Upload to PyPI (if confirmed)

3. Alternatively, manually:
   - Update version in `keprompt/version.py`
   - Build: `python -m build`
   - Upload: `python -m twine upload dist/*`

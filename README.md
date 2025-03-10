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
keprompt [-h] [-v] [--param key value] [-m] [-f] [-p [PROMPTS]] [-c [CODE]] [-l [LIST]] [-e [EXECUTE]] [-k] [-d {Statements,Prompt,LLM,Functions,Messages} [...]] [-r]
```

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --version` | Show version information and exit |
| `--param key value` | Add key/value pairs for substitution in prompts |
| `-m, --models` | List all available LLM models |
| `-f, --functions` | List all available functions that can be called |
| `-p, --prompts [PATTERN]` | List available prompt files (default: all) |
| `-c, --code [PATTERN]` | Show prompt code/commands in files |
| `-l, --list [PATTERN]` | List prompt file content line by line |
| `-e, --execute [PATTERN]` | Execute one or more prompt files |
| `-k, --key` | Add or update API keys for LLM providers |
| `-d, --debug {Statements,Prompt,LLM,Functions,Messages}` | Enable debug output for specific components |
| `-r, --remove` | Remove all backup files with .~nn~ pattern |

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
Here an old example output:

                                Available Models                             
    ┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
    ┃ Company   ┃ Model                    ┃ Max Token ┃ $/mT In ┃ $/mT Out ┃
    ┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
    │ Anthropic │ claude-3-5-haiku-latest  │      8192 │  0.1500 │   4.0000 │
    │           │ claude-3-5-sonnet-latest │      8192 │  3.0000 │  15.0000 │
    │           │ claude-3-7-sonnet-latest │      8192 │  3.0000 │  15.0000 │
    │ DeepSeek  │ deepseek-chat            │     65536 │  0.1400 │   0.2800 │
    │           │ deepseek-reasoner        │     65536 │  0.1400 │   0.2800 │
    │ Google    │ gemini-1.5-flash         │      8192 │  0.0000 │   0.0000 │
    │           │ gemini-1.5-flash-8b      │      8192 │  0.0000 │   0.0000 │
    │           │ gemini-2.0-flash-exp     │      8192 │  0.0000 │   0.0000 │
    │ MistralAI │ codestral-latest         │     32000 │  0.3000 │   0.9000 │
    │           │ ministral-3b-latest      │     32000 │  0.0400 │   0.0400 │
    │           │ ministral-8b-latest      │     32000 │  0.1000 │   0.1000 │
    │           │ mistral-large-latest     │     32000 │  2.0000 │   6.0000 │
    │           │ mistral-small-latest     │     32000 │  0.2000 │   0.6000 │
    │           │ pixtral-12b              │     32000 │  0.1500 │   0.1500 │
    │           │ pixtral-large-latest     │     32000 │  0.2000 │   0.6000 │
    │ OpenAI    │ gpt-4o                   │    128000 │  5.0000 │  20.0000 │
    │           │ gpt-4o-2024-05-13        │    128000 │  5.0000 │  15.0000 │
    │           │ gpt-4o-2024-08-06        │    128000 │  5.0000 │  20.0000 │
    │           │ gpt-4o-mini              │    128000 │  0.1500 │   0.6000 │
    │           │ gpt-4o-mini-2024-07-18   │    128000 │  0.1500 │   0.6000 │
    │           │ o1                       │    128000 │  3.0000 │  12.0000 │
    │           │ o1-mini                  │    128000 │  0.6000 │   2.4000 │
    │           │ o3-mini                  │    128000 │  1.1000 │   4.4000 │
    │ XAI       │ grok-2-latest            │    131072 │  2.0000 │  10.0000 │
    │           │ grok-2-vision-latest     │      8192 │  2.0000 │  10.0000 │
    │           │ grok-beta                │    131072 │  5.0000 │  15.0000 │
    │           │ grok-vision-beta         │      8192 │  5.0000 │  15.0000 │
    └───────────┴──────────────────────────┴───────────┴─────────┴──────────┘

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

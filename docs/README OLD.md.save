# KePrompt

A powerful prompt engineering and LLM interaction tool designed for developers, researchers, and AI practitioners to streamline communication with various Large Language Model providers.

## Overview

KePrompt provides a flexible framework for crafting, executing, and iterating on LLM prompts across multiple AI providers using a domain-specific language that translates to a universal prompt structure.

## Philosophy
- A domain-specific language allows for easy prompt definition and development  
- This is translated into a **_universal prompt structure_** upon which the code is implemented  
- Different company interfaces translate **_universal prompt structure_** to company specific prompts and back

## Features

- **Multi-Provider Support**: Interfaces with Anthropic, OpenAI, Google, MistralAI, XAI, DeepSeek, and more
- **Prompt Language**: Simple yet powerful DSL for defining prompts with 15+ statement types
- **Function Calling**: Integrated tools for file operations, web requests, and user interaction
- **User-Defined Functions**: Create custom functions in any programming language that LLMs can call
- **Language Agnostic Extensions**: Write functions in Python, Shell, Go, Rust, or any executable language
- **Function Override System**: Replace built-in functions with custom implementations
- **Conversation Management**: Persistent conversations that can be saved, loaded, and continued across sessions
- **Model Discovery**: Advanced filtering by model name, company, and provider for easy model selection
- **API Key Management**: Secure storage of API keys via system keyring
- **Rich Terminal Output**: Terminal-friendly visuals with color-coded responses
- **Structured Logging**: Advanced logging system with multiple modes (production, log, debug)
- **Cost Tracking**: Token usage and cost estimation for API calls
- **Variable Substitution**: Configurable variable substitution with customizable delimiters
- **File Backup**: Automatic backup system to prevent overwriting files


## Disclaimer
Not tested on windows or mac...


## Installation

```bash
# Install from PyPI
pip install keprompt

# Install from source
git clone https://github.com/JerryWestrick/keprompt.git
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

1. **Initialize keprompt** (creates directories and installs built-in functions):
```bash
keprompt --init
```

2. **Create a simple prompt**:
```bash
mkdir -p prompts
cat > prompts/hello.prompt << 'EOL'
.# Simple hello world example
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant.
.user Hello! Please introduce yourself.
.exec
EOL
```

3. **Execute the prompt**:
```bash
keprompt -e hello --debug
```

## Command Line Options

```
keprompt [-h] [-v] [--param key value] [-m [PATTERN]] [--company PATTERN] [--provider PATTERN] [-s] [-f] [-p [PROMPTS]] [-c [CODE]] [-l [LIST]] [-e [EXECUTE]] [-k] [--log [IDENTIFIER]] [--debug] [-r] [--init] [--check-builtins] [--update-builtins] [--conversation NAME] [--answer TEXT]
```

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --version` | Show version information and exit |
| `--param key value` | Add key/value pairs for substitution in prompts |
| `-m, --models [PATTERN]` | List all available LLM models with pricing and capabilities (optionally filter by model name pattern) |
| `--company PATTERN` | Filter models by company name pattern (use with -m) |
| `--provider PATTERN` | Filter models by provider name pattern (use with -m) |
| `-s, --statements` | List all supported prompt statement types |
| `-f, --functions` | List all available functions (built-in + user-defined) |
| `-p, --prompts [PATTERN]` | List available prompt files (default: all) |
| `-c, --code [PATTERN]` | Show prompt code/commands in files |
| `-l, --list [PATTERN]` | List prompt file content line by line |
| `-e, --execute [PATTERN]` | Execute one or more prompt files |
| `-k, --key` | Add or update API keys for LLM providers |
| `--log [IDENTIFIER]` | Enable structured logging to prompts/logs-<identifier>/ directory |
| `--debug` | Enable structured logging + rich output to STDERR |
| `-r, --remove` | Remove all backup files with .~nn~ pattern |
| `--init` | Initialize prompts and functions directories |
| `--check-builtins` | Check for built-in function updates |
| `--update-builtins` | Update built-in functions |
| `--conversation NAME` | Load/save conversation state with the specified name |
| `--answer TEXT` | Continue an existing conversation with a user response |

## Prompt Language

keprompt uses a simple line-based language for defining prompts. Each line either begins with a command (prefixed with `.`) or is treated as content. Here are the available commands:

| Command | Description |
|---------|-------------|
| `.#` | Comment (ignored during execution) |
| `.assistant` | Define assistant message |
| `.clear ["pattern1", ...]` | Delete files matching pattern(s) |
| `.cmd function(arg=value)` | Execute a predefined function |
| `.debug ["element1", ...]` | Display debug information |
| `.exec` | Execute the prompt (send to LLM) |
| `.exit` | Exit execution |
| `.image filename` | Include an image in the message |
| `.include filename` | Include text file content |
| `.llm {options}` | Configure LLM (model, temperature, etc.) |
| `.print text` | Output text to STDOUT with variable substitution |
| `.set variable value` | Set variables including Prefix/Postfix delimiters |
| `.system text` | Define system message |
| `.text text` | Add text to the current message |
| `.user text` | Define user message |

### Variable Substitution

You can use configurable variable substitution in prompts:

- **Default delimiters**: `<<variable>>` syntax
- **Configurable delimiters**: Use `.set Prefix {{` and `.set Postfix }}` to change to `{{variable}}`
- **Command line variables**: Use `--param key value` to set variables
- **Built-in variables**: `last_response` contains the most recent LLM response

Example:
```bash
# Using default delimiters
keprompt -e greeting --param name "Alice" --param model "gpt-4o-mini"

# In greeting.prompt:
.set Prefix {{
.set Postfix }}
.llm {"model": "{{model}}"}
.user Hello! My name is {{name}}.
.exec
```

## Available Functions

keprompt provides several built-in functions that can be called from prompts:

| Function | Description |
|----------|-------------|
| `readfile(filename)` | Read content from a file |
| `writefile(filename, content)` | Write content to a file (creates .backup, .backup.1, etc. if file exists) |
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
keprompt -e my_prompt --debug
```

## Conversation Management

keprompt supports persistent conversations that can be saved, loaded, and continued across multiple sessions. This is particularly useful for multi-turn interactions and maintaining context.

### Starting a New Conversation

```bash
# Start a new conversation and save it
keprompt -e my_prompt --conversation my_chat

# Start with logging enabled
keprompt -e my_prompt --conversation my_chat --debug
```

### Continuing an Existing Conversation

```bash
# Continue a conversation with a user response
keprompt --conversation my_chat --answer "That's interesting, tell me more about the second point."

# Continue with logging
keprompt --conversation my_chat --answer "Can you elaborate?" --debug
```

### Conversation Storage

Conversations are automatically saved in the `conversations/` directory as JSON files containing:
- Complete message history
- Model configuration
- Variable states
- Execution context

### Example Conversation Workflow

```bash
# 1. Start initial conversation
cat > prompts/research.prompt << 'EOF'
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a research assistant. Provide detailed, well-structured responses.
.user I'm researching renewable energy. Can you give me an overview of the main types?
.exec
EOF

keprompt -e research --conversation energy_research --debug

# 2. Continue the conversation
keprompt --conversation energy_research --answer "Can you focus specifically on solar energy efficiency improvements in the last 5 years?"

# 3. Further continuation
keprompt --conversation energy_research --answer "What are the main challenges still facing solar adoption?"
```

## Model Filtering

keprompt provides powerful filtering capabilities for exploring available models:

### Basic Model Listing

```bash
# List all models
keprompt -m

# Filter by model name pattern
keprompt -m gpt
keprompt -m "*sonnet*"
```

### Advanced Filtering

```bash
# Filter by company
keprompt -m --company anthropic
keprompt -m --company openai

# Filter by provider
keprompt -m --provider openai
keprompt -m --provider anthropic

# Combine filters
keprompt -m gpt --company openai --provider openai
keprompt -m --company anthropic --provider anthropic
```

### Filter Examples

```bash
# Show only Claude models
keprompt -m --company anthropic

# Show only GPT-4 variants
keprompt -m gpt-4

# Show all Gemini models
keprompt -m --company google

# Show models from specific provider
keprompt -m --provider mistral
```

## Supported LLM Providers

- **Anthropic**: Claude models (Haiku, Sonnet, Opus)
- **OpenAI**: GPT models including GPT-4o, o1, o3, o4-mini
- **Google**: Gemini models (1.5, 2.0, 2.5 series)
- **MistralAI**: Mistral, Codestral, Devstral, Magistral models
- **XAI**: Grok models (2, 3, 4, beta versions)
- **DeepSeek**: DeepSeek Chat and Reasoner models

Execute the following command to see all supported models with pricing and capabilities:
```bash
keprompt -m
```

## Logging and Debugging

keprompt provides three logging modes:

### Production Mode (Default)
- Clean execution with minimal output
- Errors go to stderr
- No log files created

### Log Mode
```bash
keprompt -e my_prompt --log [identifier]
```
- Structured logging to `prompts/logs-<identifier>/` directory
- Creates execution.log, statements.log, conversations.json
- Rich terminal output

### Debug Mode
```bash
keprompt -e my_prompt --debug
```
- All logging features plus rich debugging output
- Detailed API call information
- Function call tracing
- Variable substitution tracking

## Example Usage

### Basic Prompt Execution

```bash
# Create a prompt file
cat > prompts/example.prompt << EOL
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a helpful assistant.
.user Tell me about prompt engineering.
.exec
EOL

# Execute the prompt
keprompt -e example --debug
```

### Using Variables and Functions

```bash
# Create a prompt with variables and functions
cat > prompts/analyze.prompt << EOL
.llm {"model": "<<model>>"}
.user Analyze this text file:
.cmd readfile(filename="<<filename>>")
.user Please provide a summary and key insights.
.exec
EOL

# Execute with variables
keprompt -e analyze --param model "gpt-4o" --param filename "data.txt" --debug
```

### Advanced Example with Custom Output

```bash
# Create a prompt that uses .print for clean output
cat > prompts/summary.prompt << EOL
.llm {"model": "gpt-4o-mini"}
.user Summarize this in one sentence: <<content>>
.exec
.print Summary: <<last_response>>
EOL

# Execute and capture clean output
result=$(keprompt -e summary --param content "Long text here...")
echo "Result: $result"
```

## Working with Prompts

1. **Create** prompt files in the `prompts/` directory with `.prompt` extension
2. **List** available prompts with `keprompt -p`
3. **Examine** prompt content with `keprompt -l promptname`
4. **Show** prompt structure with `keprompt -c promptname`
5. **Execute** prompts with `keprompt -e promptname`
6. **Debug** execution with `keprompt -e promptname --debug`

## Output and Logging

keprompt automatically saves conversation logs when using `--log` or `--debug` modes:
- `prompts/logs-<identifier>/execution.log`: Rich terminal output
- `prompts/logs-<identifier>/statements.log`: Statement execution log
- `prompts/logs-<identifier>/conversations.json`: JSON format of all messages

## API Key Management

```bash
# Add or update API key
keprompt -k
# Select provider from the menu and enter your API key
```

API keys are securely stored using the system keyring.

## Advanced Usage

### Debugging Options

```bash
# Debug with structured logging
keprompt -e example --debug

# Log to specific directory
keprompt -e example --log my_experiment

# Show all statement types
keprompt -s

# Show all available functions
keprompt -f
```

### Working with Multiple Prompts

```bash
# Execute all prompts matching a pattern
keprompt -e "test*"

# List all prompts with "gpt" in the name
keprompt -p "*gpt*"
```

### Model Discovery and Filtering

```bash
# Explore available models
keprompt -m

# Find specific models
keprompt -m claude
keprompt -m gpt-4
keprompt -m "*mini*"

# Filter by company
keprompt -m --company anthropic
keprompt -m --company openai
keprompt -m --company google

# Filter by provider
keprompt -m --provider anthropic
keprompt -m --provider openai

# Combine filters for precise results
keprompt -m sonnet --company anthropic
keprompt -m gpt --company openai --provider openai
```

### Conversation Workflows

```bash
# Start a research conversation
keprompt -e research_prompt --conversation research_session --debug

# Continue with follow-up questions
keprompt --conversation research_session --answer "Can you provide more details on the third point?"

# Continue with specific requests
keprompt --conversation research_session --answer "Please create a summary table of the key findings."

# Start a new conversation thread
keprompt -e analysis_prompt --conversation analysis_session
```

### Function Management

```bash
# Initialize functions directory
keprompt --init

# Check built-in function version
keprompt --check-builtins

# Update built-in functions
keprompt --update-builtins

# Remove backup files
keprompt -r
```

### Combining Features

```bash
# Execute with conversation, logging, and variables
keprompt -e my_prompt --conversation project_chat --debug --param topic "AI Ethics"

# Continue conversation with logging
keprompt --conversation project_chat --answer "What are the implications?" --log project_analysis

# Filter models and save results
keprompt -m --company anthropic > available_claude_models.txt
```

## Best Practices

1. **Function Development**: Test functions independently before using in prompts
2. **Variable Naming**: Use descriptive variable names and consistent naming conventions
3. **Error Handling**: Include proper error handling in custom functions
4. **Logging**: Use `--debug` mode during development, production mode for automation
5. **Backup Management**: Regularly clean up backup files with `keprompt -r`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT](LICENSE)

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

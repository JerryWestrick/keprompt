# KePrompt Command-Line Interface

## Overview

KePrompt uses an object-first CLI design following REST principles. Commands follow the pattern:

```bash
keprompt <object> <verb> [options]
```

This design makes the interface intuitive and predictable, aligning with modern API conventions.

## Command Structure

### Basic Syntax
```bash
keprompt [global-options] <object> <verb> [object-options]
```

### Global Options
- `--version` - Display version information
- `--json` - Force JSON output (machine-readable)
- `--pretty` - Force pretty table output (human-readable)
- `-d, --dump` - Dump command arguments for debugging

### Output Format Auto-Detection
- **TTY (terminal)**: Defaults to `--pretty` (Rich formatted tables)
- **Pipe/redirect**: Defaults to `--json` (structured JSON)
- Can be overridden explicitly with `--json` or `--pretty`

## Objects and Verbs

### Prompts

#### List Prompts
```bash
keprompt prompts get
keprompt prompts get --name "math*"
```

**Aliases**: `prompt`, `prompts list`

**Output**:
- Lists all available .prompt files
- Shows prompt metadata (name, version, parameters)
- Includes file paths

**Example Output (Pretty)**:
```
Prompt Files
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Prompt       ┃ Attribute  ┃ Value                       ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ math-tutor   │ name       │ Math Tutor                  │
│              │ version    │ 1.0.0                       │
│              │ parameters │ {"model": "gpt-4o-mini"}    │
└──────────────┴────────────┴─────────────────────────────┘
```

---

### Models

#### List Models
```bash
keprompt models get
keprompt models get --name "gpt-4"
keprompt models get --provider OpenAI
keprompt models get --company Anthropic
```

**Aliases**: `model`, `models list`, `models show`

**Filters**:
- `--name <pattern>` - Filter by model name
- `--provider <name>` - Filter by provider (OpenAI, Anthropic, etc.)
- `--company <name>` - Filter by company/creator

**Output**:
- Provider, company, model name
- Max tokens, pricing (per million tokens)
- Capabilities (vision, functions)
- Cutoff date, description

**Example**:
```bash
# Show all GPT-4 models
keprompt models get --name "gpt-4*"

# Show all Anthropic models
keprompt models get --company Anthropic

# Show all models via OpenRouter
keprompt models get --provider OpenRouter
```

#### Update Models
```bash
keprompt models update
keprompt models update --provider OpenAI
```

**Description**: Updates model registry from provider APIs

#### Reset Models
```bash
keprompt models reset
```

**Description**: Resets model registry to defaults

---

### Providers

#### List Providers
```bash
keprompt providers list
```

**Aliases**: `provider list`, `providers get`, `providers show`

**Output**:
- Provider name
- Model count
- Supported companies

**Example Output**:
```
Available Providers
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Provider   ┃ Model Count ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Anthropic  │          12 │
│ DeepSeek   │           3 │
│ Google     │           8 │
│ Mistral    │           6 │
│ OpenAI     │          24 │
│ OpenRouter │         150 │
│ XAI        │           2 │
└────────────┴─────────────┘
```

---

### Functions

#### List Functions
```bash
keprompt functions get
```

**Aliases**: `function get`, `functions list`

**Output**:
- Function name
- Description
- Parameters (name, type, description)

**Built-in Functions**:
- `readfile(filename)` - Read file contents
- `writefile(filename, content)` - Write to file
- `wwwget(url)` - Fetch web content
- `askuser(question)` - Interactive user input
- `execcmd(cmd)` - Execute shell command

---

### Chats

#### Create Chat
```bash
keprompt chats create --prompt <name> [--param key value]...
```

**Aliases**: `chat create`, `chats start`, `chats new`

**Required**:
- `--prompt <name>` - Prompt file to use (without .prompt extension)

**Optional**:
- `--param <key> <value>` - Set parameter (repeatable)
- `--param <key>=<value>` - Alternative syntax

**Examples**:
```bash
# Create chat from math-tutor prompt
keprompt chats create --prompt math-tutor

# Create with parameters
keprompt chats create --prompt research --param topic "AI" --param depth "detailed"

# Alternative parameter syntax
keprompt chats create --prompt code-review --param file="src/main.py"
```

**Output**:
- Chat ID (8-character UUID)
- AI response
- Metadata (tokens, cost, model, timing)
- Parameters used

#### List Chats
```bash
keprompt chats get [--limit <n>]
```

**Aliases**: `chat get`, `chats list`, `chats show`, `chats view`

**Optional**:
- `--limit <n>` - Maximum number of chats to return (default: 100)

**Output**:
- Chat ID
- Created timestamp
- Prompt name and version
- Provider and model
- API calls, total time, total cost

#### Get Chat Details
```bash
keprompt chats get <chat-id>
```

**Output**:
- Full chat details
- Message history
- Variables
- Cost breakdown

#### Reply to Chat
```bash
keprompt chats reply <chat-id> <message>
keprompt chats reply <chat-id> --answer "message"
```

**Aliases**: `chat reply`, `chats update`, `chats answer`, `chats send`

**Required**:
- `<chat-id>` - 8-character chat identifier
- `<message>` - User message (positional or via --answer)

**Optional**:
- `--full` - Show full conversation history (default: only new messages)
- `--answer "text"` - Alternative to positional message
- `--message "text"` - Same as --answer

**Examples**:
```bash
# Positional message
keprompt chats reply a1b2c3d4 "Explain more about the second point"

# Using --answer flag
keprompt chats reply a1b2c3d4 --answer "What about edge cases?"

# Show full conversation
keprompt chats reply a1b2c3d4 --full "Thanks, that helps!"
```

#### Delete Chat
```bash
keprompt chats delete <chat-id>
keprompt chats delete --days <n>
keprompt chats delete --count <n>
keprompt chats delete --gb <size>
```

**Aliases**: `chat delete`, `chats rm`

**Modes**:
1. **Single delete**: `<chat-id>` - Delete specific chat
2. **Age-based**: `--days <n>` - Delete chats older than N days
3. **Count-based**: `--count <n>` - Keep only N most recent chats
4. **Size-based**: `--gb <size>` - Target maximum database size in GB

**Examples**:
```bash
# Delete specific chat
keprompt chats delete a1b2c3d4

# Delete chats older than 30 days
keprompt chats delete --days 30

# Keep only 100 most recent
keprompt chats delete --count 100

# Target 1GB database size
keprompt chats delete --gb 1.0
```

---

### Database

#### Get Database Info
```bash
keprompt database get
```

**Output**:
- Database existence
- File path
- Size (MB)
- Chat count
- Last modified

#### Create Database
```bash
keprompt database create
```

**Description**: Initialize new database (deletes existing)

#### Delete Database
```bash
keprompt database delete [--days <n>] [--count <n>] [--gb <size>]
```

**Description**: Clean up database with optional pruning

---

### Server

#### Start Server
```bash
keprompt server start [options]
```

**Options**:
- `--port <n>` - Port number (auto-assigned if not specified)
- `--host <addr>` - Host to bind (default: localhost)
- `--web-gui` - Enable web graphical interface
- `--reload` - Enable auto-reload for development
- `--directory <path>` - Server directory (default: current)

**Examples**:
```bash
# Start with web GUI
keprompt server start --web-gui

# Specify port
keprompt server start --port 8080 --web-gui

# Development mode with reload
keprompt server start --web-gui --reload

# Start in specific directory
keprompt server start --directory /path/to/project --web-gui
```

**Important**: Cannot use `--all` with start command

#### List Servers
```bash
keprompt server list [--active-only] [--all] [--directory <path>]
```

**Options**:
- `--active-only` - Show only running servers
- `--all` - Show all registered servers
- `--directory <path>` - Show servers for specific directory

**Output**:
- Directory
- Port
- PID
- Status (running/stopped)
- Started time
- Web GUI enabled

#### Check Server Status
```bash
keprompt server status [--all] [--directory <path>]
```

**Options**:
- `--all` - Check all registered servers
- `--directory <path>` - Check specific directory

#### Stop Server
```bash
keprompt server stop [--all] [--directory <path>]
```

**Options**:
- `--all` - Stop all servers
- `--directory <path>` - Stop server for specific directory (default: current)

**Examples**:
```bash
# Stop current directory server
keprompt server stop

# Stop all servers
keprompt server stop --all

# Stop specific directory
keprompt server stop --directory /path/to/project
```

---

## Command Aliases

### Normalization
All commands support intuitive aliases that are normalized to canonical forms:

| Command Type | Aliases → Canonical |
|-------------|---------------------|
| **Prompts** | `list`, `show` → `get` |
| **Models** | `list`, `show` → `get` |
| **Providers** | `list`, `show` → `get` |
| **Functions** | `list`, `show` → `get` |
| **Chats - get** | `list`, `show`, `view` → `get` |
| **Chats - create** | `start`, `new` → `create` |
| **Chats - reply** | `answer`, `send`, `update` → `update` |
| **Chats - delete** | `rm` → `delete` |
| **Database** | `list`, `show` → `get` |

### Object Aliases
| Singular → Plural |
|-------------------|
| `prompt` → `prompts` |
| `model` → `models` |
| `provider` → `providers` |
| `function` → `functions` |
| `chat` → `chats` |
| `database` → `databases` |

**Note**: Both singular and plural forms work identically.

---

## Output Formats

### JSON Format (Machine-Readable)
```bash
keprompt chats get --json | jq '.data[0].chat_id'
```

**Envelope Structure**:
```json
{
  "success": true,
  "data": { /* command-specific data */ },
  "error": null,
  "meta": {
    "schema_version": 1,
    "command": "chats",
    "args": { /* all arguments */ },
    "timestamp": "2025-11-04T19:00:00Z",
    "version": "1.4.0"
  }
}
```

**Error Format**:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  },
  "meta": { /* same as above */ }
}
```

### Pretty Format (Human-Readable)
Rich formatted tables with:
- Color-coded columns
- Aligned text
- Box drawing characters
- Responsive widths

---

## Environment Variables

### API Keys
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export MISTRAL_API_KEY="..."
export XAI_API_KEY="..."
export OPENROUTER_API_KEY="..."
```

### Configuration
```bash
export KEPROMPT_PROJECT="myproject"  # Project name override
export ENVIRONMENT="production"       # Environment tag
```

---

## Common Workflows

### Quick Start
```bash
# 1. List available prompts
keprompt prompts get

# 2. Create a chat
keprompt chats create --prompt hello

# 3. Continue conversation
keprompt chats reply <chat-id> "Tell me more"
```

### Development Workflow
```bash
# 1. Start server with web GUI
keprompt server start --web-gui --reload

# 2. Access web interface at http://localhost:8080
# 3. Develop and test prompts via web UI
# 4. Stop server when done
keprompt server stop
```

### Cost Analysis
```bash
# List recent chats with costs
keprompt chats get --limit 20

# Get specific chat details
keprompt chats get <chat-id>

# Query database directly for detailed analysis
sqlite3 prompts/chats.db "SELECT * FROM cost_tracking"
```

### Multi-Model Testing
```bash
# Note: Requires prompt with .llm {"model": "<<model>>"}

# Test with GPT-4
keprompt chats create --prompt test --param model "openai/gpt-4o"

# Test with Claude
keprompt chats create --prompt test --param model "anthropic/claude-3-5-sonnet-20241022"

# Test with Gemini
keprompt chats create --prompt test --param model "google/gemini-pro"

# Compare costs
keprompt chats get --limit 10
```

**Example test.prompt file for multi-model testing:**
```
.prompt "name":"Model Test", "version":"1.0.0", "params":{"model":"openai/gpt-4o-mini"}
.llm {"model": "<<model>>"}
.system You are a helpful assistant.
.user What is 2+2?
.exec
```

---

## Advanced Usage

### Parameter Passing
```bash
# Single parameter
keprompt chats create --prompt analyze --param file "data.csv"

# Multiple parameters
keprompt chats create --prompt report \
  --param input "data.csv" \
  --param format "pdf" \
  --param style "professional"

# With spaces (using = syntax)
keprompt chats create --prompt email \
  --param subject="Monthly Report" \
  --param to="team@example.com"
```

### Piping and Integration
```bash
# Get chat ID programmatically
CHAT_ID=$(keprompt chats create --prompt hello --json | jq -r '.data.chat_id')

# Continue in script
keprompt chats reply $CHAT_ID "Follow up question"

# Export chat list to CSV
keprompt chats get --json | jq -r '.data[] | [.chat_id, .created_timestamp, .total_cost] | @csv' > chats.csv
```

### Server Management
```bash
# Start multiple servers for different projects
cd /project1 && keprompt server start --port 8080 --web-gui &
cd /project2 && keprompt server start --port 8081 --web-gui &
cd /project3 && keprompt server start --port 8082 --web-gui &

# List all running servers
keprompt server list --active-only

# Stop all servers
keprompt server stop --all
```

---

## Troubleshooting

### Common Issues

**"No models found"**
```bash
# Update model registry
keprompt models update
```

**"API key not found"**
```bash
# Add to ~/.env file
echo 'OPENAI_API_KEY=sk-...' >> ~/.env

# Or set via environment variable
export OPENAI_API_KEY="sk-..."
```

**"Prompt not found"**
```bash
# List available prompts
keprompt prompts get

# Check current directory has prompts/ folder
ls prompts/
```

**"Chat not found"**
```bash
# List chats to find ID
keprompt chats get

# Verify chat ID format (8 characters)
```

**"Server already running"**
```bash
# Check status
keprompt server status

# Stop existing server
keprompt server stop

# Or use different port
keprompt server start --port 8081 --web-gui
```

### Debug Mode
```bash
# Show verbose information
keprompt chats create --prompt test --param debug "true"

# Dump command arguments
keprompt -d chats get
```

---

## Tips & Best Practices

### 1. Use Aliases
All commands support intuitive aliases - use what feels natural:
```bash
keprompt chat create --prompt hello
keprompt chats new --prompt hello
# Both work the same way
```

### 2. Default to Pretty Output in Terminal
When working in terminal, output is automatically formatted for readability.

### 3. Use JSON for Scripts
When piping or in scripts, use `--json` for reliable parsing:
```bash
keprompt chats get --json | jq '.data[] | select(.total_cost > 0.01)'
```

### 4. Parameter Organization
For complex prompts, use a script:
```bash
#!/bin/bash
keprompt chats create --prompt analysis \
  --param input_file "$1" \
  --param output_format "pdf" \
  --param detail_level "comprehensive" \
  --param include_charts "true"
```

### 5. Server Management
Use server registry for multi-project work:
```bash
# Each directory gets its own server instance
# Registry automatically tracks PIDs and ports
# Clean shutdown with stop command
```

---

## See Also

- [03-prompt-language.md](03-prompt-language.md) - Writing .prompt files
- [05-json-api.md](05-json-api.md) - API layer details
- [06-http-server.md](06-http-server.md) - REST server usage
- [07-chat-management.md](07-chat-management.md) - Chat system internals

---

*Last Updated: 2025-11-04*
*For KePrompt v1.9.2*

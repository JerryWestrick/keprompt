# KePrompt

**A powerful command-line tool for prompt engineering and AI interaction**

KePrompt lets you work with multiple AI providers (OpenAI, Anthropic, Google, and more) using simple prompt files and a unified command-line interface. No Python programming required.

## Why KePrompt?

- **One tool, many AIs**: Switch between GPT-4, Claude, Gemini, and others with a single command
- **Simple prompt language**: Write prompts using an easy-to-learn syntax
- **Comprehensive cost tracking**: Automatic SQLite-based tracking of all API usage with detailed reporting
- **Conversation management**: Save and resume multi-turn conversations
- **Function calling**: Extend prompts with file operations, web requests, and custom functions
- **Web GUI**: Modern browser-based interface for interactive prompt development
- **Production ready**: Built-in logging, error handling, and debugging tools

## Quick Start

### 0. Prepare Your Working Directory
```bash
# Create a new project directory with isolated Python environment
mkdir myproject
cd myproject
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 1. Install KePrompt
```bash
pip install keprompt
```

### 2. Initialize your workspace
```bash
keprompt database create
```
This creates the `prompts/` directory and initializes the database.

### 3. Set up your API key
```bash
# Add to your .env file or export directly
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
# ... or add to ~/.env
```

### 4. Create your first prompt
```bash
cat > prompts/hello.prompt << 'EOF'
.prompt "name":"Hello Assistant", "version":"1.0.0", "params":{}
.# My first keprompt file
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant.
.user Hello! Please introduce yourself and explain what you can help with.
.exec
EOF
```

### 5. Run your prompt
```bash
keprompt chats create --prompt hello
```

🎉 **You should see the AI's response!** The system automatically tracks costs and saves the conversation.

## Your First Real Prompt

Let's create something more useful - a file analyzer:

```bash
cat > prompts/analyze.prompt << 'EOF'
.prompt "name":"File Analyzer", "version":"1.0.0", "params":{"model":"gpt-4o", "filename":"file_to_analyze"}
.# Analyze any text file
.llm {"model": "<<model>>"}
.system You are an expert text analyst. Provide clear, actionable insights.
.user Please analyze this file:

.include <<filename>>

Provide a summary, key points, and any recommendations.
.exec
EOF
```

Run it with a parameter:
```bash
keprompt chats create --prompt analyze --param filename "README.md"
```

Run it with 2 parameters:
```bash
keprompt chats create --prompt analyze --param filename "README.md" --param model "openrouter/openai/gpt-oss-20b"
```

## Modern CLI Interface

KePrompt uses an intuitive object-verb command structure:

```bash
keprompt <object> <verb> [options]
```

### Core Objects
- **prompts** - List and manage prompt files
- **chats** - Create and manage conversations
- **models** - Browse available AI models
- **providers** - View AI providers
- **functions** - List available functions
- **server** - Start/stop web interface
- **database** - Manage conversation database

### Common Commands
```bash
# List available prompts
keprompt prompts get

# Create a new conversation
keprompt chats create --prompt hello --param name "Alice"

# Continue a conversation
keprompt chats reply <chat-id> "Tell me more"

# List conversations with costs
keprompt chats get

# Browse available models
keprompt models get --company OpenAI

# Start web interface
keprompt server start --web-gui
```

See the full CLI reference in [ks/02-cli-interface.md](ks/02-cli-interface.md)

## Web GUI Interface

KePrompt includes a modern web-based interface for interactive development:

```bash
# Start server with web GUI
keprompt server start --web-gui

# Specify port (optional)
keprompt server start --web-gui --port 8080

# Development mode with auto-reload
keprompt server start --web-gui --reload
```

Then open your browser to `http://localhost:8080`

**Features:**
- Interactive chat interface
- Real-time cost tracking
- Prompt editor with syntax highlighting
- Model selection and comparison
- Function testing and debugging
- Conversation history browser

## Core Concepts

### Prompt Files
- Stored in `prompts/` directory with `.prompt` extension
- Use simple line-based syntax starting with `.` for commands
- Support variables, functions, and multi-turn conversations

### The Prompt Language
| Command | Purpose | Example |
|---------|---------|---------|
| `.prompt` | **REQUIRED** - Define prompt metadata | `.prompt "name":"My Prompt", "version":"1.0.0"` |
| `.llm` | Configure AI model | `.llm {"model": "gpt-4o"}` |
| `.system` | Set system message | `.system You are a helpful assistant` |
| `.user` | Add user message | `.user What is the weather like?` |
| `.exec` | Send to AI and get response | `.exec` |
| `.cmd` | Call a function | `.cmd readfile(filename="data.txt")` |
| `.print` | Output to console | `.print The result is: <<last_response>>` |

### Prompt Metadata (Required)

**Every prompt file must start with a `.prompt` statement** that defines metadata:

```bash
.prompt "name":"My Prompt Name", "version":"1.0.0", "params":{"model":"gpt-4o-mini"}
```

**Required fields:**
- `name`: Human-readable prompt name (used in cost tracking)
- `version`: Semantic version for tracking changes

**Optional fields:**
- `params`: Default parameters and documentation

**Examples:**
```bash
# Simple prompt
.prompt "name":"Hello World", "version":"1.0.0"

# With parameters
.prompt "name":"Code Reviewer", "version":"2.1.0", "params":{"model":"gpt-4o", "language":"python"}

# Research assistant
.prompt "name":"Research Assistant", "version":"1.5.0", "params":{"model":"claude-3-5-sonnet-20241022", "depth":"comprehensive"}
```

### Variables
Use `<<variable>>` syntax for substitution:
```bash
# In your prompt file
.user Hello <<name>>, today is <<date>>

# Run with parameters
keprompt chats create --prompt greeting --param name "Alice" --param date "Monday"
```

### Built-in Functions
- `readfile(filename)` - Read file contents
- `writefile(filename, content)` - Write to file (with backup)
- `wwwget(url)` - Fetch web content
- `askuser(question)` - Prompt user for input
- `execcmd(cmd)` - Execute shell command

## Common Workflows

### Research Assistant
```bash
cat > prompts/research.prompt << 'EOF'
.prompt "name":"Research Assistant", "version":"1.0.0", "params":{"model":"claude-3-5-sonnet-20241022", "topic":"research_topic"}
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a research assistant. Provide thorough, well-sourced information.
.user Research this topic: <<topic>>
.cmd wwwget(url="https://en.wikipedia.org/wiki/<<topic>>")
Based on this information, provide a comprehensive overview with key facts and recent developments.
.exec
EOF

keprompt chats create --prompt research --param topic "Artificial_Intelligence"
```

### Code Review
```bash
cat > prompts/review.prompt << 'EOF'
.prompt "name":"Code Reviewer", "version":"1.0.0", "params":{"model":"gpt-4o", "codefile":"path/to/file"}
.llm {"model": "gpt-4o"}
.system You are a senior software engineer. Provide constructive code reviews.
.user Please review this code file:

.include <<codefile>>

Focus on: code quality, potential bugs, performance, and best practices.
.exec
EOF

keprompt chats create --prompt review --param codefile "src/main.py"
```

### Interactive Chat Session
```bash
# Start a conversation
CHAT_ID=$(keprompt chats create --prompt hello --json | jq -r '.data.chat_id')

# Continue the conversation
keprompt chats reply $CHAT_ID "Can you explain that in more detail?"
keprompt chats reply $CHAT_ID "What about edge cases?"

# View full conversation
keprompt chats get $CHAT_ID
```

## Working with Models

### List available models
```bash
# See all models
keprompt models get

# Filter by provider
keprompt models get --company OpenAI
keprompt models get --company Anthropic

# Search by name
keprompt models get --name "gpt-4*"
keprompt models get --name "*sonnet*"
```

### Compare costs
```bash
# Show pricing for all GPT models
keprompt models get --name "gpt*" --company OpenAI
```

### Update model registry
```bash
# Fetch latest models from providers
keprompt models update
```

## Cost Tracking & Analysis

KePrompt automatically tracks all API usage with comprehensive cost analysis.

### View Conversation Costs
```bash
# List recent conversations with costs
keprompt chats get --limit 20

# View specific chat details
keprompt chats get <chat-id>

# Get cost summary
sqlite3 prompts/chats.db "SELECT SUM(total_cost) FROM chats"
```

### Database Management
```bash
# View database info
keprompt database get

# Clean up old conversations
keprompt chats delete --days 30

# Keep only recent conversations
keprompt chats delete --count 100
```

## Custom Functions

KePrompt supports custom functions written in any language. See the detailed guide at [ks/creating-keprompt-functions.context.md](ks/creating-keprompt-functions.context.md)

### Quick Example

Create an executable in `prompts/functions/`:

```python
#!/usr/bin/env python3
import json, sys

def get_weather(city: str) -> str:
    # Your weather API logic here
    return f"Weather in {city}: Sunny, 72°F"

FUNCTIONS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"],
            "additionalProperties": False
        }
    }
]

if __name__ == "__main__":
    if sys.argv[1] == "--list-functions":
        print(json.dumps(FUNCTIONS))
    elif sys.argv[1] == "get_weather":
        args = json.loads(sys.stdin.read())
        print(get_weather(**args))
```

Make it executable:
```bash
chmod +x prompts/functions/weather
```

Use in prompts:
```bash
cat > prompts/weather_check.prompt << 'EOF'
.prompt "name":"Weather Check", "version":"1.0.0", "params":{"city":"default_city"}
.llm {"model": "gpt-4o-mini"}
.user What's the weather like in <<city>>? Based on the weather, suggest appropriate clothing.
.exec
EOF

keprompt chats create --prompt weather_check --param city "San Francisco"
```

For comprehensive documentation on creating custom functions, see [ks/creating-keprompt-functions.context.md](ks/creating-keprompt-functions.context.md)

## Conversation Management

### Create and Continue Conversations
```bash
# Start a new conversation
keprompt chats create --prompt hello

# Continue with a chat ID
keprompt chats reply a1b2c3d4 "Tell me more about that"

# Show full conversation history
keprompt chats reply a1b2c3d4 --full "Thanks for the explanation"
```

### List and View Conversations
```bash
# List all conversations
keprompt chats get

# View specific conversation
keprompt chats get a1b2c3d4

# List with filters
keprompt chats get --limit 10
```

### Clean Up
```bash
# Delete specific conversation
keprompt chats delete a1b2c3d4

# Delete old conversations
keprompt chats delete --days 30

# Keep only recent conversations
keprompt chats delete --count 100
```

## Server Management

### Start Server
```bash
# Start with web GUI
keprompt server start --web-gui

# Specify port
keprompt server start --web-gui --port 8080

# Development mode with auto-reload
keprompt server start --web-gui --reload

# Start in specific directory
keprompt server start --web-gui --directory /path/to/project
```

### Manage Servers
```bash
# List running servers
keprompt server list --active-only

# Check status
keprompt server status

# Stop server
keprompt server stop

# Stop all servers
keprompt server stop --all
```

## Output Formats

### Human-Readable (Default in Terminal)
Rich formatted tables with colors and alignment.

### Machine-Readable (JSON)
```bash
# Get JSON output
keprompt chats get --json

# Use with jq
keprompt chats get --json | jq '.data[] | select(.total_cost > 0.01)'

# Get chat ID programmatically
CHAT_ID=$(keprompt chats create --prompt hello --json | jq -r '.data.chat_id')
```

## Tips & Best Practices

### 1. Start Simple
Begin with basic prompts and gradually add complexity.

### 2. Use the Web GUI for Development
The web interface provides a better development experience with real-time feedback.

```bash
keprompt server start --web-gui --reload
```

### 3. Manage Costs
- Use cheaper models for development (`gpt-4o-mini`, `claude-3-haiku`)
- Monitor costs with `keprompt chats get`
- Check model pricing with `keprompt models get`

### 4. Organize Your Prompts
```
prompts/
├── research/
│   ├── academic.prompt
│   └── market.prompt
├── coding/
│   ├── review.prompt
│   └── debug.prompt
└── content/
    ├── blog.prompt
    └── social.prompt
```

### 5. Version Control
Keep your prompts in git to track what works best.

### 6. Test Across Models
The same prompt may work differently with different models. Test and compare.

## Troubleshooting

### Common Issues

**"No models found"**
```bash
keprompt models update
```

**"API key not found"**
```bash
# Add to .env file
echo 'OPENAI_API_KEY=sk-...' >> .env
# Or export directly
export OPENAI_API_KEY="sk-..."
```

**"Prompt not found"**
```bash
# List available prompts
keprompt prompts get
# Check prompts directory exists
ls prompts/
```

**"Server already running"**
```bash
# Check status
keprompt server status
# Stop existing server
keprompt server stop
```

### Getting Help

```bash
# Show all options
keprompt --help

# Get help for specific object
keprompt chats --help
keprompt server --help
```

## Documentation

- [CLI Interface](ks/02-cli-interface.md) - Complete command reference
- [Prompt Language](ks/03-prompt-language.md) - Writing .prompt files
- [Web GUI](ks/04-web-gui.md) - Using the web interface
- [Creating Functions](ks/creating-keprompt-functions.context.md) - Custom function development

## What's Next?

- **Explore the examples** in the `prompts/` directory
- **Try the web GUI** for interactive development
- **Create custom functions** for your specific needs
- **Integrate with your workflow** using the JSON API

## Contributing

KePrompt is open source! Contributions welcome at [GitHub](https://github.com/JerryWestrick/keprompt).

## License

[MIT](LICENSE)

---

*KePrompt: Making AI interaction simple, powerful, and cost-effective.*

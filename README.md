# KePrompt

**A powerful command-line tool for prompt engineering and AI interaction**

KePrompt lets you work with multiple AI providers (OpenAI, Anthropic, Google, and more) using simple prompt files and a unified command-line interface. No Python programming required.

## Why KePrompt?

- **One tool, many AIs**: Switch between GPT-4, Claude, Gemini, and others with a single command
- **Simple prompt language**: Write prompts using an easy-to-learn syntax
- **Comprehensive cost tracking**: Automatic SQLite-based tracking of all API usage with detailed reporting
- **Conversation management**: Save and resume multi-turn conversations
- **Function calling**: Extend prompts with file operations, web requests, and custom functions
- **Production ready**: Built-in logging, error handling, and debugging tools

## Prompt Engineering for Production

KePrompt is more than a prompting tool — it's a prompt engineering platform built around a key architectural principle: **the separation of application code and AI prompting logic**.

### Separation of Application and AI Prompting

Your application calls KePrompt; all prompting logic — model selection, system prompts, parameters, function declarations — lives in `.prompt` files. When a newer or cheaper model becomes available, you rewrite the prompt file. The application code doesn't change.

This separation turns prompt changes from code deployments into configuration updates, letting prompt engineers and developers work independently.

### Production Observability and Regression Testing

Every API call is logged in SQLite with full detail: request, response, token counts, costs, and execution timing. This production data becomes the foundation for rigorous prompt engineering:

1. **Extract** real production interactions from the database
2. **Build** regression test suites from actual usage patterns
3. **Rewrite** the prompt for a new model or optimization goal
4. **Test** the new prompt against production examples
5. **Validate** not just correctness, but also speed and cost — ensuring the new prompt meets performance and budget targets before it goes live

This closed loop — production data in, validated prompt out — is what elevates KePrompt from a "cute way to do AI prompting" to a proper prompt and knowledge engineering platform.

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

To install in developers mode use:
```bash
pip install -e ~/keprompt/ 
```



### 2. Initialize your workspace
```bash
keprompt init
```
This creates the `prompts/` directory, copies a default `hello.prompt`, installs default functions, initializes the database, and downloads the model registry — all in one command.

Use `keprompt init --force` to overwrite existing files.

### 3. Set up your API key
```bash
# Add to your .env file or export directly
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
# ... or add to ~/.env
```

### 4. Run the included hello prompt
```bash
keprompt chat new --prompt hello
```

🎉 **You should see the AI's response!** The system automatically tracks costs and saves the conversation.

Try it with different models and questions:
```bash
keprompt chat new --prompt hello --set '$.llm_model=anthropic/claude-sonnet-4-20250514'
keprompt chat new --prompt hello --set question 'tell me a joke'
keprompt chat new --prompt hello --set '$.llm_model=deepseek/deepseek-chat' --set question 'what is 2+2?'
```

## Your First Real Prompt

Let's create something more useful - a file analyzer:

```bash
cat > prompts/analyze.prompt << 'EOF'
.prompt "version":"1.0.0", "params":{"$.llm_model":"openai/gpt-4o", "filename":"file_to_analyze"}
.# Analyze any text file
.system You are an expert text analyst. Provide clear, actionable insights.
.user Please analyze this file:

.include <<filename>>

Provide a summary, key points, and any recommendations.
.exec
EOF
```

Run it with a parameter:
```bash
keprompt chats create --prompt analyze --set filename "README.md"
```

Run it with 2 parameters:
```bash
keprompt chats create --prompt analyze --set filename "README.md" --set '$.llm_model' "openrouter/openai/gpt-oss-20b"
```

Or pass variables as a JSON object file (avoids shell quoting):
```bash
echo '{"filename":"README.md","$.llm_model":"openrouter/openai/gpt-oss-20b"}' > vars.json
keprompt chats create --prompt analyze --set-from-json vars.json
```

## Modern CLI Interface

KePrompt uses an intuitive object-verb command structure:

```bash
keprompt <object> <verb> [options]
```

### Core Objects
- **init** - Initialize workspace (one-stop setup)
- **prompts** - List and manage prompt files
- **chats** - Create and manage conversations
- **models** - Browse available AI models
- **providers** - View AI providers
- **functions** - List available functions
- **database** - Manage conversation database

### Common Commands
```bash
# List available prompts
keprompt prompts get

# Create a new conversation
keprompt chats create --prompt hello --set name "Alice"

# Continue a conversation
keprompt chats reply <chat-id> "Tell me more"

# List conversations with costs
keprompt chats get

# Browse available models
keprompt models get --company OpenAI
```

See the [Knowledge Store](ks/README.md) for the full reference.

## The Prompt Language

A prompt is a file in `prompts/` ending in `.prompt`: one statement per line, each starting with `.`,
run top to bottom.

```
.prompt "version":"1.0.0", "params":{"$.llm_model":"openai/gpt-4o-mini"}
.functions readfile
.system You are a helpful assistant.
.user Summarize <<filename>> for <<audience>>.
.exec
```

- Build the conversation with `.system`, `.user`, `.assistant`, `.text`; add files and images with
  `.include` and `.image`; call the LLM with `.exec`.
- `<<name>>` substitutes a variable; `--set` / `--set-from-json` pass values in.
- The model gets no functions unless `.functions` grants them; `.cmd` runs one yourself.
- `.question` / `.evaluate` classify text with a decision model; `.guard` keeps prompt injections in
  external text out of the conversation.

**The full language, for prompt engineers: [docs/prompt-engineering.md](docs/prompt-engineering.md).**
Upgrading? [docs/migration.md](docs/migration.md).

## Common Workflows

### Research Assistant
```bash
cat > prompts/research.prompt << 'EOF'
.prompt "version":"1.0.0", "params":{"$.llm_model":"anthropic/claude-sonnet-4-20250514", "topic":"research_topic"}
.set $.llm_model anthropic/claude-sonnet-4-20250514
.system You are a research assistant. Provide thorough, well-sourced information.
.user Research this topic: <<topic>>
.cmd wwwget(url="https://en.wikipedia.org/wiki/<<topic>>")
Based on this information, provide a comprehensive overview with key facts and recent developments.
.exec
EOF

keprompt chats create --prompt research --set topic "Artificial_Intelligence"
```

### Code Review
```bash
cat > prompts/review.prompt << 'EOF'
.prompt "version":"1.0.0", "params":{"$.llm_model":"openai/gpt-4o", "codefile":"path/to/file"}
.set $.llm_model openai/gpt-4o
.system You are a senior software engineer. Provide constructive code reviews.
.user Please review this code file:

.include <<codefile>>

Focus on: code quality, potential bugs, performance, and best practices.
.exec
EOF

keprompt chats create --prompt review --set codefile "src/main.py"
```

### Interactive Chat Session
```bash
# Start a conversation
CHAT_ID=$(keprompt chats create --prompt hello --json | jq -r '.chat_id')

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

Functions are executables in `prompts/functions/`, in any language — see
[the guide, section 7](docs/prompt-engineering.md#7-functions) and the full contract in
[ks/contracts/external-functions.md](ks/contracts/external-functions.md).

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

### View Conversation Formats

KePrompt offers multiple viewing formats to help you understand and debug your conversations:

```bash
# View conversation messages (default)
keprompt chats get a1b2c3d4 --format=messages

# View prompt source code (statements)
keprompt chats get a1b2c3d4 --format=statements

# View cost summary and metadata
keprompt chats get a1b2c3d4 --format=summary

# View raw JSON data
keprompt chats get a1b2c3d4 --format=raw
```

**Format Aliases** (shortcuts for convenience):
- `--format=msg` / `msgs` / `message` → messages view
- `--format=stmt` / `stmts` / `statement` → statements view  
- `--format=sum` → summary view
- `--format=json` → raw JSON view

**Format Descriptions:**

| Format | Purpose | Shows |
|--------|---------|-------|
| `messages` | View the conversation | User/assistant dialogue with model info |
| `statements` | View source code | Prompt statements (`.user`, `.exec`, `.set`, etc.) |
| `summary` | View metrics | Costs, tokens, API calls, timing |
| `raw` | View complete data | Full JSON with all metadata |

**Examples:**
```bash
# Debug which statements were executed
keprompt chats get a1b2c3d4 --format=stmt --pretty

# Quick cost check
keprompt chats get a1b2c3d4 --format=sum --pretty

# Export conversation for analysis
keprompt chats get a1b2c3d4 --format=json > conversation.json
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
CHAT_ID=$(keprompt chats create --prompt hello --json | jq -r '.chat_id')

# Extract a value from the JSON output (example: last_response)
# (Requires jq: https://stedolan.github.io/jq/)
keprompt chat new --prompt Test --json | jq -r '.meta.variables.last_response'

# If you don't have jq, you can do the same with python3:
keprompt chat new --prompt Test --json | \
  python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["meta"]["variables"]["last_response"])'
```

## Tips & Best Practices

### 1. Start Simple
Begin with basic prompts and gradually add complexity.

### 2. Manage Costs
- Use cheaper models for development (`openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5`)
- Monitor costs with `keprompt chats get`
- Check model pricing with `keprompt models get`

### 3. Organize Your Prompts
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

### 4. Version Control
Keep your prompts in git to track what works best.

### 5. Test Across Models
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

### Getting Help

```bash
# Show all options
keprompt --help

# Get help for specific object
keprompt chats --help
```

## Documentation

For people:

- [Prompt Engineering Guide](docs/prompt-engineering.md) - The whole prompt language
- [Migration Notes](docs/migration.md) - What changes when you upgrade

For AI coding assistants (Claude Code, Cursor, ...): the [Knowledge Store](ks/README.md) is the entry
point — start there and pick a role. Worked examples are in [ks/examples/](ks/examples/README.md).

- [Prompt Language](ks/contracts/prompt-language.md) - Writing .prompt files
- [External Functions](ks/contracts/external-functions.md) - Custom function development
- [JSON Output](ks/contracts/json-envelope.md) - The `--json` envelope
- [Application Shell](ks/contracts/application-shell.md) - Driving KePrompt from an application
- [Production Database](ks/contracts/production-database.md) - What `chats.db` records
- [Architecture](ks/internals/architecture.md) - Implementation map

## What's Next?

- **Explore the examples** in the `prompts/` directory
- **Create custom functions** for your specific needs
- **Integrate with your workflow** using the JSON API

## Contributing

KePrompt is open source! Contributions welcome at [GitHub](https://github.com/JerryWestrick/keprompt).

## License

[MIT](LICENSE)

---

*KePrompt: Making AI interaction simple, powerful, and cost-effective.*



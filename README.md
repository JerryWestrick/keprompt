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

## Quick Start

### 0. Prepare Your Working Directory
```bash
# Create a new project directory, install private python environment, etc.
mkdir myproject
cd myproject
python3 -m venv .venv
activate .venv
```

### 1. Install KePrompt
```bash
pip install keprompt
```

### 2. Initialize your workspace
```bash
keprompt --init
```
This creates the `prompts/` directory and installs built-in functions.

### 3. Set up your API key
```bash
keprompt -k
```
Choose your AI provider and enter your API key (stored securely in your system keyring).

### 4. Create your first prompt
```bash
cat > prompts/hello.prompt << 'EOF'
.# My first keprompt file
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant.
.user Hello! Please introduce yourself and explain what you can help with.
.exec
EOF
```

### 5. Run your prompt
```bash
keprompt -e hello --debug
```

🎉 **You should see the AI's response!** The `--debug` flag shows detailed execution information.

## Your First Real Prompt

Let's create something more useful - a file analyzer:

```bash
cat > prompts/analyze.prompt << 'EOF'
.# Analyze any text file
.llm {"model": "gpt-4o"}
.system You are a expert text analyst. Provide clear, actionable insights.
.user Please analyze this file:
===
.include <<filename>>
===
Provide a summary, key points, and any recommendations.
.exec
EOF
```

Run it with a parameter:
```bash
keprompt -e analyze --param filename "README.md" --debug
```

## Core Concepts

### Prompt Files
- Stored in `prompts/` directory with `.prompt` extension
- Use simple line-based syntax starting with `.` for commands
- Support variables, functions, and multi-turn conversations

### The Prompt Language
| Command | Purpose | Example |
|---------|---------|---------|
| `.llm` | Configure AI model | `.llm {"model": "gpt-4o"}` |
| `.system` | Set system message | `.system You are a helpful assistant` |
| `.user` | Add user message | `.user What is the weather like?` |
| `.exec` | Send to AI and get response | `.exec` |
| `.cmd` | Call a function | `.cmd readfile(filename="data.txt")` |
| `.print` | Output to console | `.print The result is: <<last_response>>` |

### Variables
Use `<<variable>>` syntax for substitution:
```bash
# In your prompt file
.user Hello <<name>>, today is <<date>>

# Run with parameters
keprompt -e greeting --param name "Alice" --param date "Monday"
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
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a research assistant. Provide thorough, well-sourced information.
.user Research this topic: <<topic>>
.cmd wwwget(url="https://en.wikipedia.org/wiki/<<topic>>")
Based on this information, provide a comprehensive overview with key facts and recent developments.
.exec
EOF

keprompt -e research --param topic "Artificial_Intelligence"
```

### Code Review
```bash
cat > prompts/review.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a senior software engineer. Provide constructive code reviews.
.user Please review this code file:

.include <<codefile>>

Focus on: code quality, potential bugs, performance, and best practices.
.exec
EOF

keprompt -e review --param codefile "src/main.py"
```

### Content Generation
```bash
cat > prompts/blog.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a professional content writer.
.user Write the file named "blog_<<topic>.md with: 
a blog post about: <<topic>>
Target audience: <<audience>>
Tone: <<tone>>
Length: approximately <<length>> words
.exec
EOF

keprompt -e blog --param topic "AI_Tools" --param audience "developers" --param tone "informative" --param length "800"
```

## Working with Models

### List available models
```bash
# See all models
keprompt -m

# Filter by provider
keprompt -m --company openai
keprompt -m --company anthropic

# Search by name
keprompt -m gpt-4
keprompt -m "*sonnet*"
```

### Compare costs
```bash
# Show pricing for all GPT models
keprompt -m gpt --company openai
```

## Cost Tracking & Analysis

KePrompt automatically tracks all API usage with comprehensive cost analysis. No configuration required!

### Automatic Tracking
Every `.exec` statement is automatically tracked to `prompts/costs.db` with:
- **Tokens**: Input/output token counts
- **Costs**: Precise cost calculations per provider
- **Timing**: Execution duration for performance analysis
- **Metadata**: Model, provider, session IDs, parameters
- **Context**: Project name, git commit, environment

### Cost Reporting Commands
```bash
# View recent API calls
python -m keprompt.cost_cli recent --limit 10

# Cost summary for last 7 days
python -m keprompt.cost_cli summary --days 7

# Breakdown by prompt
python -m keprompt.cost_cli by-prompt --days 30

# Breakdown by model
python -m keprompt.cost_cli by-model --days 7

# Export to CSV for analysis
python -m keprompt.cost_cli export costs.csv --days 30
```

### Example Output
```
Recent Cost Entries
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Project  ┃ Prompt     ┃ Provider ┃ Model       ┃ TokIn ┃ TokOut ┃      Cost ┃ Time        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ myapp    │ analyze    │ OpenAI   │ gpt-4o      │  1250 │    340 │ $0.018500 │ 09-15 14:23 │
│ myapp    │ research   │ Anthropic│ claude-3-5  │   890 │    220 │ $0.012400 │ 09-15 14:20 │
└──────────┴────────────┴──────────┴─────────────┴───────┴────────┴───────────┴─────────────┘
```

### Project Organization
- **Auto-detection**: Uses current directory name as project
- **Manual override**: Set `KEPROMPT_PROJECT` environment variable
- **Multi-project**: Each project has its own `prompts/costs.db`

## Conversation Management

### Start a conversation
```bash
keprompt -e chat --conversation my_session --debug
```

### Continue a conversation
```bash
keprompt --conversation my_session --answer "Tell me more about the second point"
```

### Resume with logging
```bash
keprompt --conversation my_session --answer "Can you provide examples?" --debug
```

## Custom Functions

Create executable functions in any language:

```bash
# Create a custom function
cat > prompts/functions/weather << 'EOF'
#!/usr/bin/env python3
import json, sys, requests

def get_schema():
    return [{
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    }]

if sys.argv[1] == "--list-functions":
    print(json.dumps(get_schema()))
elif sys.argv[1] == "get_weather":
    args = json.loads(sys.stdin.read())
    # Your weather API logic here
    print(f"Weather in {args['city']}: Sunny, 72°F")
EOF

chmod +x prompts/functions/weather
```

Use in prompts:
```bash
cat > prompts/weather_check.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.user Use defined functions to describe what's the weather like in <<city>>?
Based on this weather, suggest appropriate clothing.
.exec
EOF

keprompt -e weather_check --param city "San Francisco"  --debug
```

## Command Reference

| Command | Description |
|---------|-------------|
| `keprompt -e <name>` | Execute prompt file |
| `keprompt -p` | List available prompts |
| `keprompt -m` | List available models |
| `keprompt -f` | List available functions |
| `keprompt -k` | Add/update API keys |
| `keprompt --debug` | Enable detailed logging |
| `keprompt --conversation <name>` | Manage conversations |
| `keprompt --param key value` | Set variables |

## Tips & Best Practices

### 1. Start Simple
Begin with basic prompts and gradually add complexity.

### 2. Use Debug Mode
Always use `--debug` when developing prompts to see what's happening.

### 3. Manage Costs
- Use cheaper models for development (`gpt-4o-mini`, `claude-3-haiku`)
- Monitor token usage with the debug output
- Check model pricing with `keprompt -m`

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
- Run `keprompt --init` to set up the workspace
- Check your internet connection for model updates

**"API key not found"**
- Run `keprompt -k` to add your API key
- Ensure you have credits/access with your AI provider

**"Function not found"**
- Run `keprompt -f` to see available functions
- Check that custom functions are executable (`chmod +x`)

**"Prompt file not found"**
- Ensure files are in `prompts/` directory with `.prompt` extension
- Use `keprompt -p` to list available prompts

### Getting Help

```bash
# Show all options
keprompt --help

# List statement types
keprompt -s

# Show prompt content
keprompt -l <promptname>

# Debug a prompt
keprompt -e <promptname> --debug
```

## What's Next?

- **Explore the examples** in the `prompts/` directory
- **Create custom functions** for your specific needs
- **Set up conversations** for complex multi-turn interactions
- **Integrate with your workflow** using shell scripts or CI/CD

## Contributing

KePrompt is open source! Contributions welcome at [GitHub](https://github.com/JerryWestrick/keprompt).

## License

[MIT](LICENSE)

---

*KePrompt: Making AI interaction simple, powerful, and cost-effective.*

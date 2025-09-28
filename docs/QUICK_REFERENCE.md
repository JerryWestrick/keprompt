# KePrompt Quick Reference

## Essential Commands

| Command                        | Description              | Example                                    |
|--------------------------------|--------------------------|--------------------------------------------|
| `keprompt -e <name>`           | Execute prompt           | `keprompt -e hello --debug`                |
| `keprompt -p`                  | List prompts             | `keprompt -p "*research*"`                 |
| `keprompt -m`                  | List models              | `keprompt -m gpt --company openai`         |
| `keprompt -f`                  | List functions           | `keprompt -f`                              |
| `keprompt -k`                  | Add API key              | `keprompt -k`                              |
| `keprompt --init`              | Initialize workspace     | `keprompt --init`                          |
| `keprompt --list-conversations`| List all conversations   | `keprompt --list-conversations`            |
| `keprompt --view-conversation` | View conversation detail | `keprompt --view-conversation my_session` |

## Prompt Language Cheat Sheet

### Basic Structure
```
.# Comment
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant
.user Hello world
.exec
```

### All Statement Types

| Statement    | Purpose             | Example                            |
|--------------|---------------------|------------------------------------|
| `.#`         | Comment             | `.# This is a comment`             |
| `.llm`       | Configure model     | `.llm {"model": "gpt-4o"}`         |
| `.system`    | System message      | `.system You are an expert`        |
| `.user`      | User message        | `.user What is AI?`                |
| `.assistant` | Assistant message   | `.assistant I can help with that`  |
| `.text`      | Add text to message | `.text Additional context`         |
| `.exec`      | Execute prompt      | `.exec`                            |
| `.cmd`       | Call function       | `.cmd execcmd(cmd="ls -la")`       |
| `.print`     | Output to console   | `.print Result: <<last_response>>` |
| `.set`       | Set variable        | `.set name "Alice"`                |
| `.debug`     | Show debug info     | `.debug ["variables"]`             |
| `.include`   | Include file        | `.include template.txt`            |
| `.image`     | Add image           | `.image photo.jpg`                 |
| `.clear`     | Delete files        | `.clear ["*.tmp"]`                 |
| `.exit`      | Stop execution      | `.exit`                            |

## Variables

### Syntax
- Default: `<<variable>>`
- Custom: Change with `.set Prefix {{` and `.set Postfix }}`

### Built-in Variables
- `<<last_response>>` - Most recent AI response
- `<<Prefix>>` - Variable delimiter start
- `<<Postfix>>` - Variable delimiter end

### Command Line Variables
```bash
keprompt -e prompt --param name "Alice" --param topic "AI"
```

## Built-in Functions

| Function            | Purpose      | Example                                                        |
|---------------------|--------------|----------------------------------------------------------------|
| `readfile`          | Read file    | `.include data.txt`                                            |
| `writefile`         | Write file   | Instruct AI to create files directly                           |
| `wwwget`            | Fetch URL    | `.cmd wwwget(url="https://example.com")`                       |
| `execcmd`           | Run command  | `.cmd execcmd(cmd="ls -la")`                                   |
| `write_base64_file` | Write base64 | `.cmd write_base64_file(filename="img.png", base64_str="...")` |

## Model Management

### List Models
```bash
# All models
keprompt -m

# Filter by company
keprompt -m --company openai
keprompt -m --company anthropic

# Filter by name
keprompt -m gpt-4
keprompt -m "*sonnet*"

# Combine filters
keprompt -m claude --company anthropic
```

### Popular Models
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `o1-preview`
- **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`
- **Google**: `gemini-1.5-pro`, `gemini-2.0-flash-exp`
- **Others**: `deepseek-chat`, `grok-beta`, `mistral-large-latest`

## Conversation Management

### Start Conversation
```bash
keprompt -e prompt --conversation session_name --debug
```

### Continue Conversation
```bash
keprompt --conversation session_name --answer "Tell me more"
```

### View Conversations (New in v1.4.0)
```bash
# List all conversations with costs
keprompt --list-conversations

# View detailed conversation history
keprompt --view-conversation session_name
```

### Conversation Features
- **Professional overview**: Tabular list with model info, message counts, and total costs
- **Enhanced readability**: LaTeX math formatting cleaned up for easy reading
- **Cost integration**: Automatic cost tracking linked to original prompts
- **Smart text wrapping**: Long content properly formatted and wrapped
- **Complete history**: Full conversation flow with role-based formatting

### Conversation Files
- Stored in: `conversations/`
- Format: `session_name.conversation`
- JSON format with messages, variables, and metadata

## Logging Modes

| Mode       | Command                      | Output                   |
|------------|------------------------------|--------------------------|
| Production | `keprompt -e prompt`         | Clean output only        |
| Log        | `keprompt -e prompt --log`   | Structured logs to files |
| Debug      | `keprompt -e prompt --debug` | Rich terminal + logs     |


## Common Patterns

### Simple Query
```
.llm {"model": "gpt-4o-mini"}
.user <<question>>
.exec
```

### File Analysis
```
.llm {"model": "gpt-4o"}
.system You are an expert analyst
.user Analyze this file:
.include <<file>>
.exec
```

### Research & Save
```
.llm {"model": "claude-3-5-sonnet-20241022"}
.user Create a file called "research_<<topic>>.md" with research on: <<topic>>
.exec
```

### Multistep Workflow
```
.llm {"model": "gpt-4o"}
.user Step 1: <<task1>>
.exec
.user Step 2 based on above and create a file called "results.md" with: <<task2>>
.exec
```

### Include Files
```
.llm {"model": "gpt-4o"}
.system You are a code reviewer
.user Review this code:
.include src/main.py

Provide feedback on quality and security.
.exec
```

### Image Analysis
```
.llm {"model": "gpt-4o"}
.system You are an image analysis expert
.user Analyze this image:
.image screenshot.png

What do you see in this image?
.exec
```

## Custom Functions

### Function Template (Python)
```python
#!/usr/bin/env python3
import json, sys

def get_schema():
    return [{
        "name": "my_function",
        "description": "What it does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param1"]
        }
    }]

if sys.argv[1] == "--list-functions":
    print(json.dumps(get_schema()))
elif sys.argv[1] == "my_function":
    args = json.loads(sys.stdin.read())
    # Your logic here
    print(f"Result: {args['param1']}")
```

### Function Template (Bash)
```bash
#!/bin/bash

if [ "$1" = "--list-functions" ]; then
    cat << 'JSON'
[{
    "name": "my_function",
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    }
}]
JSON
elif [ "$1" = "my_function" ]; then
    args=$(cat)
    param1=$(echo "$args" | python3 -c "import json, sys; print(json.load(sys.stdin)['param1'])")
    echo "Result: $param1"
fi
```

## Troubleshooting

### Common Issues
| Problem              | Solution                                          |
|----------------------|---------------------------------------------------|
| "No models found"    | Run `keprompt --init`                             |
| "API key not found"  | Run `keprompt -k`                                 |
| "Function not found" | Check `keprompt -f`, ensure executable            |
| "Prompt not found"   | Check file in `prompts/` with `.prompt` extension |
| High costs           | Use cheaper models like `gpt-4o-mini`             |

### Debug Commands
```bash
# Show prompt structure
keprompt -l promptname

# Show parsed commands
keprompt -c promptname

# Test with debug output
keprompt -e promptname --debug

# List available items
keprompt -p    # prompts
keprompt -f    # functions
keprompt -m    # models
keprompt -s    # statement types
```

## Cost Management

### Inexpensive Models for Development
- `gpt-4o-mini` - OpenAI's cheapest
- `claude-3-haiku-20240307` - Anthropic's cheapest
- `gemini-1.5-flash` - Google's fast model

### Monitor Costs
```bash
# Check pricing
keprompt -m --company openai

# Use debug mode to see token usage
keprompt -e prompt --debug
```

## Integration Examples

### Shell Script
```bash
#!/bin/bash
result=$(keprompt -e analyze --param file "$1")
echo "Analysis: $result"
```

### CI/CD Pipeline
```yaml
- name: Code Review
  run: |
    keprompt -e code_review --param pr_number "${{ github.event.number }}" --log "ci_review"
```

### Cron Job
```bash
# Daily report at 9 AM
0 9 * * * /usr/local/bin/keprompt -e daily_report --log "daily_$(date +%Y%m%d)"
```

## Best Practices

1. **Start simple** - Begin with basic prompts
2. **Use debug mode** - Always use `--debug` when developing
3. **Version control** - Keep prompts in git
4. **Organize files** - Use directories for different purposes
5. **Test functions** - Verify custom functions work independently
6. **Monitor costs** - Use cheap models for development
7. **Document prompts** - Use comments to explain complex logic
8. **Backup important conversations** - They're in `conversations/`

## Getting Help

- `keprompt --help` - Full command help
- `keprompt -s` - List statement types
- GitHub: [keprompt repository](https://github.com/JerryWestrick/keprompt)
- Issues: Report bugs and feature requests

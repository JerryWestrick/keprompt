# KePrompt Tutorial: From Beginner to Power User

This tutorial will take you from your first keprompt command to building sophisticated AI workflows. Each section builds on the previous one, so work through them in order.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Prompt Language](#understanding-the-prompt-language)
3. [Working with Variables](#working-with-variables)
4. [Using Functions](#using-functions)
5. [Managing Conversations](#managing-conversations)
6. [Creating Custom Functions](#creating-custom-functions)
7. [Advanced Workflows](#advanced-workflows)
8. [Production Tips](#production-tips)

## Getting Started

### Installation and Setup

First, let's get keprompt installed and configured:

```bash
# Install keprompt
pip install keprompt

# Verify installation
keprompt --version

# Initialize your workspace
keprompt --init
```

The `--init` command creates:
- `prompts/` directory for your prompt files
- `prompts/functions/` directory for custom functions
- Built-in function executables

### Your First API Key

You'll need an API key from at least one AI provider. Let's start with OpenAI:

1. Go to [OpenAI's API page](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to keprompt:

```bash
keprompt -k
# Select "OpenAI" from the menu
# Paste your API key when prompted
```

Your key is stored securely in your system keyring.

### Hello World

Create your first prompt file:

```bash
cat > prompts/hello.prompt << 'EOF'
.# This is a comment - my first keprompt file
.llm {"model": "gpt-4o-mini"}
.system You are a friendly assistant.
.user Hello! Please introduce yourself.
.exec
EOF
```

Run it:

```bash
keprompt -e hello --debug
```

**What happened?**
- `.#` - Comment line (ignored)
- `.llm` - Configure the AI model to use
- `.system` - Set the system message (AI's role/instructions)
- `.user` - Add a user message
- `.exec` - Send everything to the AI and get a response
- `--debug` - Show detailed execution information

## Understanding the Prompt Language

The prompt language uses simple commands that start with a dot (`.`). Let's explore each one:

### Message Types

```bash
cat > prompts/messages.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a helpful writing assistant.
.user I need help writing an email.
.assistant I'd be happy to help you write an email! What kind of email are you writing, and who is the recipient?
.user It's a professional email to my manager about a project update.
.exec
EOF
```

**Message types:**
- `.system` - Set the AI's role and behavior (role toggle)
- `.user` - Switch to user message mode (role toggle)
- `.assistant` - Switch to assistant message mode (role toggle)
- `.text` - Add text to the current message (same as plain text lines)

The Assistant Message is a response from the AI's, __or used so simulate one__.

Simulating an AI response is a useful prompting trick that causes the AI to emulate 
these outputs on later on in the prompts.

### Execution Commands

```bash
cat > prompts/execution.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.user What's 2 + 2?
.exec
.print The AI said: <<last_response>>
.exit
EOF
```

**Execution commands:**
- `.exec` - Send messages to AI and get response
- `.print` - Output text to console (for scripts/automation)
- `.exit` - Stop execution (optional - added automatically)

### Development Commands

```bash
cat > prompts/debug.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.set topic "artificial intelligence"
.debug ["variables"]
.user Tell me about <<topic>>
.exec
EOF
```

**Development commands:**
- `.debug` - Show internal state (variables, messages, etc.)
- `.set` - Set variables
- `.#` - Comments

## Working with Variables

Variables make your prompts reusable and dynamic.

### Basic Variables

```bash
cat > prompts/greeting.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a friendly assistant.
.user Hello <<name>>! Today is <<day>>. How are you?
.exec
EOF
```

Run with parameters:

```bash
keprompt -e greeting --param name "Alice" --param day "Monday"
```

### Built-in Variables

KePrompt provides several built-in variables:

```bash
cat > prompts/builtin_vars.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.user What's the weather like?
.exec
.print Last response: <<last_response>>
.set summary "The AI talked about weather"
.print Summary: <<summary>>
EOF
```

**Built-in variables:**
- `last_response` - The most recent AI response
- `Prefix` - Variable delimiter start (default: `<<`)
- `Postfix` - Variable delimiter end (default: `>>`)

### Custom Delimiters

You can change the variable delimiters:

```bash
cat > prompts/custom_delims.prompt << 'EOF'
.set Prefix {{
.set Postfix }}
.llm {"model": "gpt-4o-mini"}
.user Hello {{name}}, welcome to {{company}}!
.exec
EOF

keprompt -e custom_delims --param name "Bob" --param company "TechCorp"
```

## Using Functions

Functions extend keprompt with file operations, web requests, and more.

### Built-in Functions

Let's explore each built-in function:

#### Reading Files

```bash
# Create a test file
echo "This is a test document with important information." > test.txt

cat > prompts/file_reader.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a document analyzer.
.user Please analyze this document:
.cmd readfile(filename="test.txt")
Provide a brief summary and any insights.
.exec
EOF

keprompt -e file_reader --debug
```

#### Writing Files

```bash
cat > prompts/file_writer.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.user Write a short poem about programming.
.exec
.cmd writefile(filename="poem.txt", content="<<last_response>>")
.print Poem saved to poem.txt
EOF

keprompt -e file_writer
```

#### Web Requests

```bash
cat > prompts/web_fetch.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a web content analyzer.
.user Analyze this webpage:
.cmd wwwget(url="https://en.wikipedia.org/wiki/Artificial_intelligence")
Summarize the key points about AI from this content.
.exec
EOF

keprompt -e web_fetch --debug
```

#### User Interaction

```bash
cat > prompts/interactive.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant.
.cmd askuser(question="What topic would you like to discuss?")
.user I'd like to learn about: <<last_response>>
.exec
EOF

keprompt -e interactive
```

#### Command Execution

```bash
cat > prompts/system_info.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a system administrator assistant.
.user Here's information about the current system:
.cmd execcmd(cmd="uname -a")
.cmd execcmd(cmd="df -h")
.user Based on this system information, provide insights about the system health and available disk space.
.exec
EOF

keprompt -e system_info --debug
```

### Function Parameters

Functions use named parameters:

```bash
# Correct
.cmd readfile(filename="data.txt")
.cmd writefile(filename="output.txt", content="Hello World")

# Also correct - using variables
.cmd readfile(filename="<<input_file>>")
.cmd writefile(filename="<<output_file>>", content="<<generated_content>>")
```

## Managing Conversations

Conversations let you have multi-turn interactions with AI models.

### Starting a Conversation

```bash
cat > prompts/research_start.prompt << 'EOF'
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a research assistant. Provide thorough, well-researched information and ask follow-up questions to better understand the user's needs.
.user I'm researching renewable energy technologies for a presentation. Can you help me understand the current landscape?
.exec
EOF

# Start the conversation
keprompt -e research_start --conversation energy_research --debug
```

### Continuing a Conversation

```bash
# Continue with follow-up questions
keprompt --conversation energy_research --answer "I'm particularly interested in solar and wind power efficiency improvements in the last 5 years."

# Ask for more specific information
keprompt --conversation energy_research --answer "Can you provide some specific statistics and recent breakthroughs?"

# Request a summary
keprompt --conversation energy_research --answer "Please create a summary of our discussion that I can use for my presentation."
```

### Conversation Best Practices

1. **Use descriptive names**: `energy_research`, `code_review_session`, `content_planning`
2. **Enable logging**: Always use `--debug` to track the conversation
3. **Save important conversations**: They're stored in `conversations/` directory
4. **Resume anytime**: Conversations persist between sessions

### Advanced Conversation Example

```bash
cat > prompts/code_mentor.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a senior software engineer and mentor. Help the user learn programming concepts through interactive discussion. Ask questions to understand their level and provide appropriate guidance.
.user I'm learning Python and want to understand object-oriented programming better.
.exec
EOF

# Start mentoring session
keprompt -e code_mentor --conversation python_learning --debug

# Continue the learning session
keprompt --conversation python_learning --answer "I understand classes and objects, but I'm confused about inheritance."

keprompt --conversation python_learning --answer "Can you show me a practical example of when inheritance is useful?"
```

## Creating Custom Functions

Custom functions let you extend keprompt with any functionality you need.

### Simple Python Function

```bash
cat > prompts/functions/math_tools << 'EOF'
#!/usr/bin/env python3
import json
import sys
import math

def get_schema():
    return [
        {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string", 
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "factorial",
            "description": "Calculate factorial of a number",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {
                        "type": "integer",
                        "description": "Number to calculate factorial for"
                    }
                },
                "required": ["number"]
            }
        }
    ]

if len(sys.argv) < 2:
    print("Usage: math_tools <command>")
    sys.exit(1)

if sys.argv[1] == "--list-functions":
    print(json.dumps(get_schema()))
elif sys.argv[1] == "calculate":
    args = json.loads(sys.stdin.read())
    try:
        result = eval(args["expression"])
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
elif sys.argv[1] == "factorial":
    args = json.loads(sys.stdin.read())
    try:
        result = math.factorial(args["number"])
        print(f"Factorial of {args['number']} is {result}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print(f"Unknown function: {sys.argv[1]}")
EOF

chmod +x prompts/functions/math_tools
```

Test your function:

```bash
# Verify it's discovered
keprompt -f | grep calculate

# Use it in a prompt
cat > prompts/math_helper.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a math tutor.
.user Calculate 15 factorial:
.cmd factorial(number=15)
.user Now calculate the square root of 144:
.cmd calculate(expression="144**0.5")
.user Explain these results to a student.
.exec
EOF

keprompt -e math_helper --debug
```

### Shell Script Function

```bash
cat > prompts/functions/git_tools << 'EOF'
#!/bin/bash

if [ "$1" = "--list-functions" ]; then
    cat << 'JSON'
[
    {
        "name": "git_status",
        "description": "Get git repository status",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "git_log",
        "description": "Get recent git commits",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of commits to show"
                }
            },
            "required": ["count"]
        }
    }
]
JSON
elif [ "$1" = "git_status" ]; then
    git status --porcelain
elif [ "$1" = "git_log" ]; then
    args=$(cat)
    count=$(echo "$args" | python3 -c "import json, sys; print(json.load(sys.stdin)['count'])")
    git log --oneline -n "$count"
else
    echo "Unknown function: $1"
fi
EOF

chmod +x prompts/functions/git_tools
```

Use it:

```bash
cat > prompts/code_review.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a senior developer doing code review.
.user Here's the current git status:
.cmd git_status()
.user And here are the recent commits:
.cmd git_log(count=5)
.user Based on this information, what should I focus on in my code review?
.exec
EOF

keprompt -e code_review --debug
```

### Function Best Practices

1. **Always implement `--list-functions`**: This is how keprompt discovers your functions
2. **Use proper JSON schemas**: Define parameters clearly
3. **Handle errors gracefully**: Return meaningful error messages
4. **Make functions executable**: `chmod +x` is required
5. **Test independently**: Test your functions outside of keprompt first

## Advanced Workflows

### Multi-Step Research Pipeline

```bash
cat > prompts/research_pipeline.prompt << 'EOF'
.llm {"model": "claude-3-5-sonnet-20241022"}
.system You are a research analyst. Provide thorough, well-sourced analysis.

.# Step 1: Initial research
.user Research the topic: <<topic>>
.cmd wwwget(url="https://en.wikipedia.org/wiki/<<topic>>")
.exec

.# Step 2: Save initial findings
.cmd writefile(filename="research_<<topic>>_initial.md", content="# Initial Research: <<topic>>\n\n<<last_response>>")

.# Step 3: Deep dive analysis
.user Based on the initial research, provide a detailed analysis focusing on:
1. Current trends and developments
2. Key challenges and opportunities  
3. Future outlook
4. Recommendations for further investigation
.exec

.# Step 4: Save final report
.cmd writefile(filename="research_<<topic>>_final.md", content="# Final Analysis: <<topic>>\n\n<<last_response>>")

.print Research complete! Files saved:
.print - research_<<topic>>_initial.md
.print - research_<<topic>>_final.md
EOF

keprompt -e research_pipeline --param topic "quantum_computing" --debug
```

### Code Analysis Workflow

```bash
cat > prompts/code_analysis.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a senior software architect and security expert.

.# Step 1: Read the code
.user I need a comprehensive analysis of this code file:
.cmd readfile(filename="<<codefile>>")

.# Step 2: Initial analysis
Please provide:
1. Code quality assessment
2. Security vulnerability analysis
3. Performance considerations
4. Maintainability review
.exec

.# Step 3: Generate improvement suggestions
.user Based on your analysis, create specific improvement recommendations with code examples where appropriate.
.exec

.# Step 4: Save the analysis report
.cmd writefile(filename="analysis_<<codefile>>.md", content="# Code Analysis Report\n\n## File: <<codefile>>\n\n## Initial Analysis\n<<last_response>>\n\n## Improvement Recommendations\n[Previous response would be included here]")

.print Analysis complete! Report saved to: analysis_<<codefile>>.md
EOF

keprompt -e code_analysis --param codefile "src/main.py" --debug
```

### Content Creation Pipeline

```bash
cat > prompts/content_pipeline.prompt << 'EOF'
.llm {"model": "gpt-4o"}
.system You are a professional content creator and editor.

.# Step 1: Research the topic
.user Research and gather information about: <<topic>>
Target audience: <<audience>>
Content type: <<content_type>>
.exec

.# Step 2: Create outline
.user Based on your research, create a detailed outline for the <<content_type>> about <<topic>> for <<audience>>.
.exec

.# Step 3: Write the content
.user Now write the complete <<content_type>> following the outline. Make it engaging and appropriate for <<audience>>.
.exec

.# Step 4: Save and review
.cmd writefile(filename="<<content_type>>_<<topic>>.md", content="<<last_response>>")

.user Review the content you just created and provide:
1. A brief quality assessment
2. Suggestions for improvement
3. SEO recommendations (if applicable)
.exec

.cmd writefile(filename="<<content_type>>_<<topic>>_review.md", content="# Content Review\n\n<<last_response>>")

.print Content creation complete!
.print - Content: <<content_type>>_<<topic>>.md
.print - Review: <<content_type>>_<<topic>>_review.md
EOF

keprompt -e content_pipeline --param topic "AI_productivity_tools" --param audience "software_developers" --param content_type "blog_post" --debug
```

## Production Tips

### 1. Organize Your Prompts

Create a logical directory structure:

```bash
mkdir -p prompts/{research,coding,content,analysis,automation}

# Move prompts to appropriate directories
mv prompts/research*.prompt prompts/research/
mv prompts/code*.prompt prompts/coding/
mv prompts/blog*.prompt prompts/content/
```

### 2. Use Version Control

```bash
# Initialize git in your prompts directory
cd prompts
git init
git add .
git commit -m "Initial prompt collection"

# Track what works
git tag v1.0-working-research-prompts
```

### 3. Create Prompt Templates

```bash
cat > prompts/templates/analysis_template.prompt << 'EOF'
.# Analysis Template - Replace <<TOPIC>> with your subject
.llm {"model": "<<MODEL>>"}
.system You are an expert analyst in <<DOMAIN>>.
.user Analyze: <<TOPIC>>
.# Add your specific analysis requirements here
.exec
.cmd writefile(filename="analysis_<<TOPIC>>.md", content="<<last_response>>")
EOF
```

### 4. Cost Management

```bash
# Use cheaper models for development
.llm {"model": "gpt-4o-mini"}  # Instead of gpt-4o

# Check costs regularly
keprompt -m gpt --company openai  # See pricing

# Monitor usage with debug mode
keprompt -e expensive_prompt --debug  # Shows token usage
```

### 5. Error Handling

```bash
cat > prompts/robust_example.prompt << 'EOF'
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant. If you encounter any errors or unclear requests, explain what went wrong and suggest alternatives.

.# Use conditional logic in your prompts
.user Please help me with: <<task>>
If this request is unclear or problematic, please explain why and suggest how to improve it.
.exec

.# Always include error context
.print Task: <<task>>
.print Status: Completed
.print Response saved: <<last_response>>
EOF
```

### 6. Automation Scripts

```bash
cat > run_daily_analysis.sh << 'EOF'
#!/bin/bash

# Daily automation script
DATE=$(date +%Y-%m-%d)
LOG_DIR="logs/$DATE"
mkdir -p "$LOG_DIR"

echo "Running daily analysis - $DATE"

# Run multiple prompts with logging
keprompt -e research/market_analysis --param date "$DATE" --log "market_$DATE" > "$LOG_DIR/market.log" 2>&1
keprompt -e coding/security_scan --log "security_$DATE" > "$LOG_DIR/security.log" 2>&1
keprompt -e content/social_media --param date "$DATE" --log "social_$DATE" > "$LOG_DIR/social.log" 2>&1

echo "Analysis complete. Logs in $LOG_DIR"
EOF

chmod +x run_daily_analysis.sh
```

### 7. Testing Your Prompts

```bash
# Create a test script
cat > test_prompts.sh << 'EOF'
#!/bin/bash

echo "Testing prompts..."

# Test with minimal model first
for prompt in prompts/test_*.prompt; do
    echo "Testing $prompt"
    keprompt -e "$(basename "$prompt" .prompt)" --param model "gpt-4o-mini" --debug
    echo "---"
done

echo "All tests complete"
EOF

chmod +x test_prompts.sh
```

## Next Steps

Congratulations! You now have a solid foundation in keprompt. Here's what to explore next:

1. **Build your prompt library**: Create prompts for your common tasks
2. **Experiment with different models**: Compare results across providers
3. **Create custom functions**: Automate your specific workflows
4. **Set up conversations**: For complex, multi-turn interactions
5. **Integrate with your tools**: Use keprompt in scripts and CI/CD pipelines

## Getting Help

- **Command help**: `keprompt --help`
- **List functions**: `keprompt -f`
- **Debug prompts**: Always use `--debug` when developing
- **Check syntax**: `keprompt -l promptname` to see parsed content
- **Community**: Join the discussions on GitHub

Happy prompting! 🚀

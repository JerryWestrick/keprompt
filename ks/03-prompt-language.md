# KePrompt Prompt Language Specification

## Introduction

The KePrompt prompt language is a line-based, statement-oriented language for defining AI interactions. Files use the `.prompt` extension and consist of statements that are executed sequentially by the Virtual Machine.

## File Structure

### Basic Structure
```
.prompt <metadata>
.llm <model configuration>
.system <system message>
.user <user message>
.exec
.print <output>
.exit
```

### Complete Example
```
.prompt "name":"Math Tutor", "version":"1.0.0", "params":{"model":"openai/gpt-4o-mini", "topic":"algebra"}
.llm {"model": "openai/gpt-4o-mini"}
.system You are a helpful math tutor. Explain concepts clearly with examples.
.user I need help understanding <<topic>>. Can you explain the basics?
.exec
.print <<last_response>>
```

## Statement Types

### Meta Statements

#### `.prompt` (Required - Must Be First)
Defines prompt metadata including name, version, and parameters.

**Syntax:**
```
.prompt "name":"Prompt Name", "version":"X.Y.Z", "params":{...}
```

**Required Fields:**
- `name` - Human-readable prompt name (used in cost tracking)
- `version` - Semantic version (e.g., "1.0.0")

**Optional Fields:**
- `params` - Default parameters with documentation

**Examples:**
```
.prompt "name":"Hello World", "version":"1.0.0"

.prompt "name":"Code Reviewer", "version":"2.1.0", "params":{"model":"gpt-4o", "language":"python"}

.prompt "name":"Research Assistant", "version":"1.5.0", "params":{"model":"claude-3-5-sonnet-20241022", "topic":"AI", "depth":"comprehensive"}
```

**Purpose:**
- Cost tracking with semantic names
- Version control for prompts
- Self-documenting prompts
- Parameter definitions

---

#### `.llm` (Required)
Configures the AI model and parameters.

**Syntax:**
```
.llm {"model": "model-name", "temperature": 0.7, "max_tokens": 1000}
```

**Required:**
- `model` - Model identifier (must exist in model registry)

**Optional:**
- `temperature` - Sampling temperature (0.0-2.0)
- `max_tokens` - Maximum response tokens
- `top_p` - Nucleus sampling parameter
- Other provider-specific parameters

**Examples:**
```
.llm {"model": "openai/gpt-4o-mini"}
.llm {"model": "anthropic/claude-3-5-sonnet-20241022", "temperature": 0.3}
.llm {"model": "google/gemini-pro", "max_tokens": 2000, "temperature": 1.0}
.llm {"model": "<<model>>"}  # Using variable substitution
```

---

### Message Statements

#### `.system`
Adds a system message (AI behavior instructions).

**Syntax:**
```
.system <message text>
```

**Examples:**
```
.system You are a helpful assistant.

.system You are a professional code reviewer. Provide constructive feedback focusing on:
- Code quality and readability
- Potential bugs
- Performance considerations
- Best practices
```

**Multi-line:**
System messages automatically span multiple lines. Lines without a leading dot continue the previous message:
```
.system You are an expert data analyst.
Analyze data thoroughly and provide actionable insights.
Always include confidence levels in your conclusions.
```

You can also explicitly use `.text` for continuation (same result):
```
.system You are an expert data analyst.
.text Analyze data thoroughly and provide actionable insights.
.text Always include confidence levels in your conclusions.
```

---

#### `.user`
Adds a user message.

**Syntax:**
```
.user <message text>
```

**Examples:**
```
.user Hello! How can you help me today?

.user I need help with <<topic>>. Can you explain:
1. Basic concepts
2. Common use cases
3. Best practices
```

**With Variables:**
```
.user Analyze the file: <<filename>>
.user Research topic: <<topic>> with depth level: <<depth>>
```

---

#### `.assistant`
Adds an assistant message (for multi-turn conversations or priming).

**Syntax:**
```
.assistant <message text>
```

**Examples:**
```
.prompt "name":"Hello World", "version":"1.0.0"

.prompt "name":"Code Reviewer", "version":"2.1.0", "params":{"model":"openai/gpt-4o", "language":"python"}

.prompt "name":"Research Assistant", "version":"1.5.0", "params":{"model":"anthropic/claude-3-5-sonnet-20241022", "topic":"AI", "depth":"comprehensive"}
```

**Use Cases:**
- Priming expected response format
- Continuing multi-turn conversations
- Few-shot learning examples

---

#### `.text`
Explicitly continues the previous message (concatenates text). **Note**: This is optional - lines without a leading dot automatically continue the previous message.

**Syntax:**
```
.text <additional text>
```

**Rules:**
- Must follow `.system`, `.user`, or `.assistant`
- Appends to the last message
- Optional - same effect as lines without leading dot

**Examples:**

Using implicit continuation (no `.text` needed):
```
.user Please analyze this code:

```python
def calculate(x, y):
    return x + y
```

What improvements would you suggest?
```

Using explicit `.text` (same result):
```
.user Please analyze this code:
.text 
.text ```python
.text def calculate(x, y):
.text     return x + y
.text ```
.text 
.text What improvements would you suggest?
```

---

### Execution Statements

#### `.exec`
Executes the current conversation with the AI model.

**Syntax:**
```
.exec
```

**Behavior:**
- Sends accumulated messages to AI
- Receives response
- Updates conversation history
- Tracks costs and tokens
- Stores response in `last_response` variable

**Example:**
```
.user What is 2+2?
.exec
.print The answer is: <<last_response>>
```

**Multiple Executions:**
```
.user First question
.exec
.user Follow-up based on: <<last_response>>
.exec
```

---

#### `.exit`
Terminates prompt execution.

**Syntax:**
```
.exit
```

**Behavior:**
- Stops processing statements
- Logs final statistics
- Saves chat state (if applicable)

**Note:** Automatically added if not present

---

### Variable Statements

#### `.set`
Sets a variable value.

**Syntax:**
```
.set <variable_name> <value>
```

**Examples:**
```
.set greeting Hello, World!
.set model gpt-4o-mini
.set temperature 0.7
.set Prefix [[
.set Postfix ]]
```

**Special Variables:**
- `Prefix` - Variable substitution prefix (default: `<<`)
- `Postfix` - Variable substitution postfix (default: `>>`)
- `Debug` - Enable debug mode
- `Verbose` - Enable verbose output

**With Substitution:**
```
.set base_path /data/files
.set full_path <<base_path>>/report.txt
```

---

### Function Statements

#### `.cmd`
Executes a function and appends result to message.

**Syntax:**
```
.cmd function_name(param1=value1, param2=value2)
```

**Built-in Functions:**
- `readfile(filename)` - Read file contents
- `writefile(filename, content)` - Write to file
- `wwwget(url)` - Fetch web content
- `askuser(question)` - Interactive input
- `execcmd(cmd)` - Execute shell command

**Examples:**
```
.user Please analyze this file:
.cmd readfile(filename="data.csv")

.user Fetch this webpage:
.cmd wwwget(url="https://example.com/api/data")

.user Execute and show output:
.cmd execcmd(cmd="ls -la")
```

**With Variables:**
```
.cmd readfile(filename="<<input_file>>")
.cmd wwwget(url="<<api_endpoint>>/<<resource>>")
```

---

#### `.include`
Includes content from another file.

**Syntax:**
```
.include <filename>
```

**Examples:**
```
.user Analyze this code:
.include src/main.py

.system You are a document analyzer. Here is the document:
.include <<document_path>>
```

---

### Image Statements

#### `.image`
Adds an image to the conversation (for vision-capable models).

**Syntax:**
```
.image <filename>
```

**Examples:**
```
.image screenshot.png
.image /path/to/diagram.jpg
.image <<image_path>>
```

**Requirements:**
- Model must support vision (e.g., gpt-4o, claude-3-opus)
- File must be accessible
- Common formats: PNG, JPG, JPEG, GIF, WebP

---

### Output Statements

#### `.print`
Outputs text to STDOUT (production output channel).

**Syntax:**
```
.print <text>
```

**Examples:**
```
.print Hello, World!
.print The result is: <<last_response>>
.print Model: <<model_name>>, Cost: $<<VM.total_cost>>
```

**Use Cases:**
- Final output to user
- Formatted results
- Status messages

**Note:** Separate from debug logging (which goes to STDERR)

---

### Debug Statements

#### `.debug`
Displays VM state for debugging.

**Syntax:**
```
.debug [elements]
```

**Elements:**
- `all` - Show everything
- `header` - VM properties
- `llm` - LLM configuration
- `messages` - Message history
- `statements` - Statement list
- `variables` - Variable dictionary

**Examples:**
```
.debug ["all"]
.debug ["messages", "variables"]
.debug ["llm"]
```

---

#### `.#` (Comment)
Comment line - ignored during execution.

**Syntax:**
```
.# <comment text>
```

**Examples:**
```
.# This is a comment
.# TODO: Add error handling
.# Author: John Doe
.# Version: 2.0.0 - Added multi-model support
```

---

### Utility Statements

#### `.clear`
Deletes files matching patterns.

**Syntax:**
```
.clear ["pattern1", "pattern2", ...]
```

**Examples:**
```
.clear ["logs/*.log"]
.clear ["temp/*", "cache/*"]
```

**Warning:** Destructive operation - use with caution

---

## Variable Substitution

### Basic Syntax
Variables are enclosed in configurable delimiters (default: `<<` and `>>`).

**Examples:**
```
.set name Alice
.user Hello <<name>>!
```

**Result:** "Hello Alice!"

### Nested Substitution
```
.set base /data
.set file report.txt
.user Please read: <<base>>/<<file>>
```

**Result:** "Please read: /data/report.txt"

### Dictionary Access
```
.set config {"host": "localhost", "port": 8080}
.user Connect to: <<config.host>>:<<config.port>>
```

**Result:** "Connect to: localhost:8080"

### VM Namespace (Read-Only)
Access VM properties using `VM.` prefix:

**Available Properties:**
- `VM.chat_id` - Current chat identifier
- `VM.model_name` - Current model name
- `VM.provider` - Current provider
- `VM.interaction_no` - API call count
- `VM.cost_in` - Input cost
- `VM.cost_out` - Output cost
- `VM.total_cost` - Total cost
- `VM.toks_in` - Input tokens
- `VM.toks_out` - Output tokens
- `VM.total_tokens` - Total tokens
- `VM.filename` - Prompt filename
- `VM.prompt_name` - Prompt name
- `VM.prompt_version` - Prompt version

**Examples:**
```
.print Chat ID: <<VM.chat_id>>
.print Total cost so far: $<<VM.total_cost>>
.print Using model: <<VM.model_name>> (<<VM.provider>>)
.print Tokens used: <<VM.total_tokens>> (in: <<VM.toks_in>>, out: <<VM.toks_out>>)
```

### Configurable Delimiters
Change delimiters using `.set`:

```
.set Prefix [[
.set Postfix ]]
.user Hello [[name]]!
```

**Use Cases:**
- Avoid conflicts with existing syntax
- Template compatibility
- Personal preference

---

## Control Flow

### Automatic Completion
The VM automatically adds missing completion statements:

**Case 1:** Ends with `.exit`
```
.user Hello
.exit
```
→ No changes

**Case 2:** Ends with `.exec`
```
.user Hello
.exec
```
→ Adds:
```
.print <<last_response>>
.exit
```

**Case 3:** Ends with anything else
```
.user Hello
```
→ Adds:
```
.exec
.print <<last_response>>
.exit
```

### Multi-Turn Conversations
```
.user First question
.exec
.user Based on: <<last_response>>, tell me more
.exec
.user Finally, summarize everything
.exec
```

---

## Best Practices

### 1. Always Include Metadata
```
.prompt "name":"My Prompt", "version":"1.0.0"
```

### 2. Use Descriptive Variable Names
```
.set input_file data/report.csv
.set output_format pdf
.set analysis_depth comprehensive
```

### 3. Comment Your Prompts
```
.# Purpose: Analyze sales data and generate monthly report
.# Author: Jane Smith
.# Last Modified: 2025-11-04
```

### 4. Structure for Readability
```
.# Configuration
.llm {"model": "gpt-4o"}

.# System Context
.system You are a data analyst...

.# Load Data
.user Analyze this data:
.cmd readfile(filename="data.csv")

.# Execute Analysis
.exec

.# Output Results
.print <<last_response>>
```

### 5. Handle Parameters Properly
```
.prompt "name":"Analyzer", "version":"1.0.0", "params":{"input_file":"data.csv", "format":"json"}
.set file <<input_file>>
.set fmt <<format>>
```

### 6. Use Functions for File Operations
```
.# Read input
.cmd readfile(filename="<<input_file>>")

.# Process with AI
.exec

.# Save output
.cmd writefile(filename="<<output_file>>", content="<<last_response>>")
```

---

## Common Patterns

### Interactive Tutorial
```
.prompt "name":"Math Tutor", "version":"1.0.0"
.llm {"model": "openai/gpt-4o-mini"}
.system You are a patient math tutor.
.user Explain <<topic>>
.exec
.cmd askuser(question="Do you have any questions?")
.exec
```

### File Analysis
```
.prompt "name":"File Analyzer", "version":"1.0.0", "params":{"file":"README.md"}
.llm {"model": "openai/gpt-4o"}
.system You are a document analyzer.
.user Analyze this file:
.include <<file>>
.exec
```

### Web Research
```
.prompt "name":"Web Researcher", "version":"1.0.0", "params":{"url":"https://example.com"}
.llm {"model": "anthropic/claude-3-5-sonnet-20241022"}
.system You are a research assistant.
.user Research this page:
.cmd wwwget(url="<<url>>")
.text Provide a comprehensive summary.
.exec
```

### Multi-Model Comparison
```
.prompt "name":"Model Comparison", "version":"1.0.0"
.set question What is quantum computing?

.# Test with GPT-4
.llm {"model": "openai/gpt-4o"}
.user <<question>>
.exec
.set gpt4_response <<last_response>>

.# Test with Claude
.llm {"model": "anthropic/claude-3-5-sonnet-20241022"}
.user <<question>>
.exec
.set claude_response <<last_response>>

.print GPT-4: <<gpt4_response>>
.print Claude: <<claude_response>>
```

---

## Error Handling

### Common Errors

**Missing `.prompt` statement:**
```
Error: First statement must be .prompt with name and version
```

**Invalid model:**
```
Error: Model 'invalid-model' not found
```

**Missing API key:**
```
Error: API key not found for provider OpenAI
```

**Variable not defined:**
```
Error: Variable 'undefined_var' is not defined
```

**Invalid function:**
```
Error: Function 'invalid_func' is not defined
```

---

## Advanced Features

### Dynamic Model Selection
```
.set model openai/gpt-4o-mini
.llm {"model": "<<model>>"}
```

### Conditional Logic (via AI)
```
.user Based on <<condition>>, should I proceed? Answer only YES or NO.
.exec
.# Process response and act accordingly
```

### Template Reuse
```
.# Load template
.include templates/system_prompt.txt
.user <<user_question>>
.exec
```

---

## See Also

- [02-cli-interface.md](02-cli-interface.md) - Running prompts via CLI
- [04-vm-architecture.md](04-vm-architecture.md) - How prompts are executed
- [12-function-system.md](12-function-system.md) - Creating custom functions

---

*Last Updated: 2025-11-04*
*For KePrompt v1.9.2*

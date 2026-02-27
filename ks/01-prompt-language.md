# KePrompt Prompt Language - LLM Reference

## Core Architecture

**Model Loading**: Model instantiation occurs ONLY at `.exec` time. Model can be specified via:
1. `.prompt` params (default)
2. `.set model` (override default)
3. `.exec` params (override for that call, permanent update to vdict)

**All overrides are permanent** - they update `vm.vdict` and affect subsequent `.exec` calls.

## Statement Types

### `.prompt` (Required, First Statement)
```
.prompt "name":"PromptName", "version":"1.0.0", "params":{...}
```
- `name` (required): Semantic name for cost tracking
- `version` (required): Semantic version
- `params` (optional): Default variables including model
  - `params.model`: Default model name (e.g., "openai/gpt-4")
  - Other params become variables in vm.vdict

**Example:**
```
.prompt "name":"Test", "version":"1.0", "params":{"model":"openai/gpt-4", "temperature":0.7}
```

### `.exec` - Execute LLM Call
```
.exec                           # Uses model from vdict
.exec {"model":"..."}            # Override model (permanent)
.exec modelname                  # Shorthand override
```

**Behavior:**
- Loads model from params OR vdict['model']
- Gets API key for provider
- Makes API call
- Updates `last_response` variable
- **If params provided**: Permanently updates vm.vdict

**Multi-model example:**
```
.prompt "name":"Compare", "version":"1.0", "params":{"model":"openai/gpt-4"}
.user Question 1
.exec                                  # Uses gpt-4

.user Question 2
.exec {"model":"anthropic/claude-3.5"} # Switches to claude (permanent)

.user Question 3
.exec                                  # Uses claude (not gpt-4!)
```

### `.set` - Set Variable
```
.set variable_name value
```

**Model setting:**
```
.set model openai/gpt-4
.exec  # Uses gpt-4
```

Special variables: `Prefix`, `Postfix`, `Debug`, `Verbose`

### `.user` - User Message
```
.user <text>
```
Multi-line: lines without leading dot continue previous message.

### `.system` - System Message
```
.system <text>
```
Multi-line same as `.user`.

### `.assistant` - Assistant Message
```
.assistant <text>
```
For few-shot examples or conversation history. Creates assistant message with text content.

### `.tool_call` - Tool/Function Call (Manual)
```
.tool_call function_name(param=value,...) id=call_id
```
Manually create assistant message with tool call. Used for:
- Debugging tool interactions
- Testing function handling
- Creating example conversations with tools
- Conversation replay

**Example:**
```
.tool_call readfile(filename="data.txt") id=call_abc123
```

Creates `AiMessage(role='assistant', content=[AiCall(...)])`.

### `.tool_result` - Tool Result (Manual)
```
.tool_result id=call_id name=function_name
result content (can be multi-line)
```
Manually create tool message with function result. Used for:
- Providing pre-computed results
- Testing LLM response to tool results
- Creating complete conversation examples

**Example:**
```
.tool_result id=call_abc123 name=readfile
File contents: Lorem ipsum dolor sit amet...
```

Creates `AiMessage(role='tool', content=[AiResult(...)])`.

### `.print` - Output to STDOUT
```
.print <text>
```
Uses variable substitution. Production output channel.

### `.cmd` - Execute Function
```
.cmd function_name(param=value)
.cmd function_name(param=value) as variable_name
```

Built-in functions:
- `readfile(filename)` - Read file
- `writefile(filename, content)` - Write file  
- `wwwget(url)` - Fetch URL
- `execcmd(cmd)` - Execute shell

**Without `as`:** Result appends to current message + stored in `last_response`
**With `as`:** Result stored ONLY in variable + `last_response`

### `.include` - Include File
```
.include <filename>
```
Appends file content to current message.

### `.image` - Add Image
```
.image <filename>
```
For vision models. Formats: PNG, JPG, JPEG, GIF, WebP.

### `.text` - Continue Message
```
.text <additional text>
```
Optional - same effect as lines without leading dot.

### `.#` - Comment
```
.# comment text
```
Ignored during execution.

### `.debug` - Show VM State
```
.debug ["all"]
.debug ["messages", "variables", "llm", "header", "statements"]
```

### `.clear` - Delete Files
```
.clear ["pattern1", "pattern2"]
```
Uses glob patterns. Destructive.

### `.exit` - Terminate
```
.exit
```
Auto-added if missing.

## Variable Substitution

**Syntax:** `<<variable>>` (configurable via Prefix/Postfix)

**Dictionary access:** `<<dict.key>>`

**VM namespace (read-only):** `VM.property`
- `VM.chat_id`, `VM.model_name`, `VM.provider`
- `VM.interaction_no`
- `VM.cost_in`, `VM.cost_out`, `VM.total_cost`
- `VM.toks_in`, `VM.toks_out`, `VM.total_tokens`
- `VM.filename`, `VM.prompt_name`, `VM.prompt_version`

## Auto-Completion Logic

**Ends with `.exit`:** No changes
**Ends with `.exec`:** Adds `.print <<last_response>>` + `.exit`
**Ends with anything else:** Adds `.exec` + `.print <<last_response>>` + `.exit`

## Common Patterns

**Basic:**
```
.prompt "name":"Hello", "version":"1.0", "params":{"model":"openai/gpt-4"}
.user Hello
.exec
```

**Model via .set:**
```
.prompt "name":"Test", "version":"1.0"
.set model openai/gpt-4
.user Hello
.exec
```

**Multi-turn:**
```
.user First question
.exec
.user Follow-up: <<last_response>>
.exec
```

**File analysis:**
```
.user Analyze:
.cmd readfile(filename="data.txt")
.exec
```

**Multi-model (permanent switches):**
```
.set model openai/gpt-4
.user Question for GPT-4
.exec

.exec {"model":"anthropic/claude-3.5"}  # Switches to Claude
.user Question for Claude
.exec  # Still uses Claude

.exec {"model":"openai/gpt-4o"}  # Switches to GPT-4o
.exec  # Uses GPT-4o
```

## Error Messages

- "No model specified" → Need `.prompt` params, `.set model`, or `.exec` param
- "Model 'X' not found" → Invalid model name
- "API key not found for provider X" → Missing API key in config
- "Variable 'X' not defined" → Undefined variable in substitution

---
*KePrompt v2.0 - Model loading moved to .exec*


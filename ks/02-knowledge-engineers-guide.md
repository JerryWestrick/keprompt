# KePrompt for Knowledge Engineers

A practical guide to prompt engineering with KePrompt, from fundamentals to advanced techniques.

## Table of Contents

1. [Understanding the Foundation](#understanding-the-foundation)
2. [Core Techniques](#core-techniques)
3. [Advanced Patterns](#advanced-patterns)
4. [Best Practices](#best-practices)
5. [Real-World Examples](#real-world-examples)

---

## Understanding the Foundation

### How Statements Work

KePrompt uses a **statement-to-message** execution model:

```
Statement (source code) → execute() → Message (conversation data)
```

Each statement in a `.prompt` file is an instruction that, when executed, creates or modifies messages in the conversation.

**Key Insight:** The LLM never sees statements. It only sees messages.

### The Message Accumulation Model

Messages accumulate in `vm.prompt.messages[]` as statements execute:

```python
# After these statements execute:
.user "Hello"        # → messages[0] = AiMessage(role='user', ...)
.assistant "Hi!"     # → messages[1] = AiMessage(role='assistant', ...)
.user "How are you?" # → messages[2] = AiMessage(role='user', ...)
```

**Critical Rule:** `.exec` sends ALL accumulated messages to the LLM, not just the latest one.

### When .exec Happens vs Doesn't

This is the **fundamental distinction** in KePrompt:

**WITHOUT .exec:**
```
.user "What is 2+2?"
.assistant "4"
# Messages created, but NO API call
# This is a "fake" conversation turn
```

**WITH .exec:**
```
.user "What is 5+5?"
.exec
# API call happens, sends ALL messages (including fakes!)
# LLM sees the entire conversation history
```

### The Three-Layer Architecture

1. **Statements** (Source Code) - What you write in `.prompt` files
2. **Messages (Universal)** (Data) - Provider-agnostic conversation format
3. **Messages (Company)** (API) - Provider-specific format (ephemeral)

Only layers 1 and 2 are stored. Layer 3 is generated on-demand for each API call.

---

## Core Techniques

### Few-Shot Learning

**Definition:** Teaching the LLM by example rather than instruction.

**How it works:** Add `.assistant` statements WITHOUT `.exec` to create "fake" conversation history that the LLM learns from.

#### Basic Example

```
.prompt "name":"JSONFormatter", "version":"1.0"
.system Format all responses as JSON with "answer" and "explanation" keys.

# Example 1 (few-shot)
.user What is 2+2?
.assistant {"answer": 4, "explanation": "Two plus two equals four"}

# Example 2 (few-shot)
.user What is the capital of France?
.assistant {"answer": "Paris", "explanation": "Paris is the capital city of France"}

# Real question
.user What is 5+5?
.exec
# LLM sees 5 messages and learns the JSON pattern
```

**Result:** The LLM responds in JSON format because it learned from the examples.

#### Why This Works

The LLM receives:
```
System: Format all responses as JSON...
User: What is 2+2?
Assistant: {"answer": 4, ...}      ← LLM thinks it said this
User: What is the capital of France?
Assistant: {"answer": "Paris", ...}  ← LLM thinks it said this
User: What is 5+5?
```

The LLM has **no way to know** the first two assistant messages are fake. It treats them as its own previous responses and continues the pattern.

#### Few-Shot Pattern Library

**1. Format Teaching**
```
.user Input: "hello world"
.assistant Output: "HELLO WORLD"

.user Input: "goodbye"
.assistant Output: "GOODBYE"

.user Input: "<<text_to_process>>"
.exec
```

**2. Reasoning Pattern**
```
.user 15 + 27
.assistant Let me break this down:
- 15 + 27
- 10 + 20 = 30
- 5 + 7 = 12
- 30 + 12 = 42
Answer: 42

.user 23 + 56
.exec
# LLM shows step-by-step reasoning
```

**3. Structured Output**
```
.user Analyze: "The cat sat on the mat"
.assistant {
  "subject": "cat",
  "verb": "sat",
  "location": "mat",
  "sentiment": "neutral"
}

.user Analyze: "<<user_sentence>>"
.exec
```

**4. Error Handling**
```
.user What is the square root of -1?
.assistant Error: Cannot compute square root of negative number. Please provide a positive number.

.user What is the square root of 16?
.assistant Answer: 4

.user What is the square root of <<number>>?
.exec
```

### Multi-Turn Conversations

Build on previous responses using the `<<last_response>>` variable:

```
.prompt "name":"Researcher", "version":"1.0"

.user What is photosynthesis?
.exec
# Response stored in <<last_response>>

.user Explain this to a 5-year-old: <<last_response>>
.exec
# LLM sees both Q&A pairs and simplifies previous answer

.user What are 3 key takeaways from your explanation?
.exec
# Context continues building
```

**Important:** Each `.exec` includes ALL previous messages. The conversation context grows with each turn.

### Variable Management

#### Setting Variables

**Method 1: In .prompt params**
```
.prompt "name":"Test", "version":"1.0", "params":{"model":"openai/gpt-4", "tone":"professional"}
.user Please respond in a <<tone>> manner.
.exec
```

**Method 2: Using .set**
```
.set user_name "Alice"
.set max_words 100
.user Hello, my name is <<user_name>>. Please respond in under <<max_words>> words.
.exec
```

**Method 3: From function results**
```
.cmd readfile(filename="config.json") as config
.user The configuration is: <<config>>
.exec
```

#### Variable Scope

Variables in `vm.vdict` persist for the entire VM execution. They are:
- Set by `.prompt` params
- Modified by `.set`
- Updated by `.cmd ... as variable`
- Accessible via `<<variable>>`

#### Read-Only VM Properties

Access VM state via the `VM.` namespace:

```
.print Current chat ID: <<VM.chat_id>>
.print Model used: <<VM.model_name>>
.print Cost so far: $<<VM.total_cost>>
.print Tokens used: <<VM.total_tokens>>
```

### Function Integration

#### Basic Function Call

```
.user Please analyze this file:
.cmd readfile(filename="data.txt")
.exec
# File contents appended to message, LLM analyzes
```

#### Storing Function Result

```
.cmd readfile(filename="data.txt") as file_content
.user The file contains: <<file_content>>
Please summarize it.
.exec
```

**Difference:**
- **Without `as`:** Result appends to current message
- **With `as`:** Result stored in variable only (not appended)

#### Chaining Functions

```
.cmd wwwget(url="https://example.com") as webpage
.cmd writefile(filename="backup.html", content="<<webpage>>")
.user Analyze this webpage: <<webpage>>
.exec
```

#### Built-In Functions

- `readfile(filename)` - Read file contents
- `writefile(filename, content)` - Write to file
- `execcmd(cmd)` - Execute shell command

#### Custom Functions

Place Python scripts in `prompts/functions/` directory. See [creating-keprompt-functions.context.md](creating-keprompt-functions.context.md) for details.

---

## Advanced Patterns

### Model Switching Strategies

#### Single-Model Prompt

```
.prompt "name":"Task", "version":"1.0", "params":{"model":"openai/gpt-4"}
.user Question
.exec
```

#### Multi-Model Comparison

```
.prompt "name":"Compare", "version":"1.0"

.set question "Explain quantum computing"

# Try GPT-4
.set model openai/gpt-4
.user <<question>>
.exec
.set gpt4_response <<last_response>>

# Try Claude
.set model anthropic/claude-3.5-sonnet
.user <<question>>
.exec
.set claude_response <<last_response>>

# Compare
.user Compare these two explanations:
GPT-4: <<gpt4_response>>
Claude: <<claude_response>>
.exec
```

#### Cost-Optimized Pipeline

```
.prompt "name":"Pipeline", "version":"1.0"

# Use cheap model for initial draft
.set model openai/gpt-4o-mini
.user Write a draft essay about AI safety.
.exec

# Use expensive model for refinement
.set model openai/gpt-4
.user Improve this draft: <<last_response>>
.exec
```

### Tool Use Teaching

Teach LLMs to use tools via examples with `.tool_call` and `.tool_result`:

```
.prompt "name":"ToolTeacher", "version":"1.0"
.system You have access to a readfile function. Use it to read files when asked.

# Example 1: Show tool usage pattern
.user Read config.json
.tool_call readfile(filename="config.json") id=call_001
.tool_result id=call_001 name=readfile
{"setting": "value", "enabled": true}
.assistant The config file contains setting: value and enabled: true.

# Example 2: Another example
.user What's in data.txt?
.tool_call readfile(filename="data.txt") id=call_002
.tool_result id=call_002 name=readfile
Sample data: 123, 456, 789
.assistant The data file contains sample numbers: 123, 456, and 789.

# Real usage
.user Read my-file.txt
.exec
# LLM learns to use readfile tool from examples
```

**Key Points:**
- `.tool_call` creates assistant message with function call
- `.tool_result` creates tool message with result
- No `.exec` between them = example conversation
- LLM learns the pattern and generates real tool calls

### Context Management

#### Limiting Context Size

```
.prompt "name":"Summarizer", "version":"1.0"

# Read large file
.cmd readfile(filename="large-doc.txt") as full_doc

# Summarize in chunks
.user Summarize this in 100 words: <<full_doc>>
.exec
.set summary <<last_response>>

# Use summary instead of full doc
.user Based on the summary: <<summary>>, answer: What are the key points?
.exec
```

#### Context Reset

Start fresh conversation mid-prompt (advanced technique):

```
# First conversation
.user Question 1
.exec

# "Reset" by not referencing previous turns
# New context starts here
.system You are a different assistant now.
.user Completely new question
.exec
```

Note: Messages still accumulate, but you control what the LLM focuses on.

### Prompt Composition

#### Using .include

```
# prompts/standard-instructions.txt contains:
# "Be concise. Use bullet points. Cite sources."

.prompt "name":"Research", "version":"1.0"
.system Instructions:
.include prompts/standard-instructions.txt

.user Research: <<topic>>
.exec
```

#### Template Prompts

```
# template.prompt
.prompt "name":"Template", "version":"1.0"
.system You are a <<role>> assistant.
.user <<task>>
.exec

# Use with variables:
# keprompt chat new --prompt template --set role "financial" --set task "Analyze Q4 earnings"
```

### Dynamic Prompt Generation

```
.prompt "name":"Dynamic", "version":"1.0"

# Load examples from file
.cmd readfile(filename="examples.json") as examples_json

# Parse and use (assuming examples contain Q&A pairs)
.system Learn from these examples: <<examples_json>>

.user <<actual_question>>
.exec
```

---

## Best Practices

### Cost Optimization

**1. Use Cheaper Models for Simple Tasks**
```
# Draft with mini, refine with full
.set model openai/gpt-4o-mini
.user Generate 10 title options
.exec

.set model openai/gpt-4
.user Pick the best title and explain why: <<last_response>>
.exec
```

**2. Minimize Token Usage**
```
# Bad: Sending full document every turn
.user Analyze this: <<huge_doc>>
.exec
.user What about section 2? <<huge_doc>>
.exec

# Good: Summarize once, reference summary
.user Summarize: <<huge_doc>>
.exec
.set summary <<last_response>>

.user What about section 2? Context: <<summary>>
.exec
```

**3. Cache Expensive Results**
```
.cmd readfile(filename="expensive-api-result.json") as cached_result
.user Use this cached data: <<cached_result>>
.exec
```

### Quality vs Speed Tradeoffs

**Fast & Cheap (gpt-4o-mini, claude-haiku):**
- Simple classifications
- Formatting tasks
- Draft generation
- Repetitive tasks

**Balanced (gpt-4o, claude-sonnet):**
- General purpose
- Creative writing
- Code generation
- Analysis

**Slow & Expensive (gpt-4, claude-opus):**
- Complex reasoning
- Critical decisions
- Final polishing
- High-stakes content

### Debugging Techniques

#### 1. Use .debug Statement

```
.user Test question
.assistant Test answer
.debug ["messages", "variables"]
# Shows exactly what messages accumulated
```

#### 2. Print Messages Before .exec

```
.set test_question "What is AI?"
.user <<test_question>>
.print About to send: <<test_question>>
.exec
```

#### 3. Test Few-Shot Examples Separately

```
# Test that examples alone don't trigger .exec
.user Example input
.assistant Example output
.exit  # Stop here to verify messages created correctly
```

#### 4. Use --vm-debug Flag

```bash
keprompt chat new --prompt test --vm-debug
# Shows statement execution flow
```

### Testing Strategies

#### 1. Unit Test Individual Patterns

```
# test-json-format.prompt
.prompt "name":"TestJSON", "version":"1.0"
.system Format as JSON

.user Test: 2+2
.assistant {"answer": 4}

.user What is 5+5?
.exec
.print Result: <<last_response>>
# Verify JSON format in output
```

#### 2. Integration Test Multi-Step

```
# test-pipeline.prompt
.prompt "name":"TestPipeline", "version":"1.0"

.cmd readfile(filename="test-data.txt") as data
.user Process: <<data>>
.exec

.user Summarize: <<last_response>>
.exec
# Verify entire pipeline works
```

#### 3. Cost Test with Mini Models

```
.set model openai/gpt-4o-mini
# Develop and test with cheap model

# .set model openai/gpt-4
# Switch to production model when ready
```

---

## Real-World Examples

### Example 1: Data Analysis Pipeline

```
.prompt "name":"DataAnalyzer", "version":"1.0", "params":{"model":"openai/gpt-4"}

# Load data
.cmd readfile(filename="sales-data.csv") as sales_data

# Analyze
.user Analyze this sales data and identify trends:
<<sales_data>>

Please provide:
1. Top 3 insights
2. Anomalies or concerns
3. Recommendations
.exec

# Store analysis
.set analysis <<last_response>>
.cmd writefile(filename="analysis-report.txt", content="<<analysis>>")

# Generate visualizations suggestions
.user Based on this analysis:
<<analysis>>

Suggest 3 data visualizations that would be most effective.
For each, specify:
- Chart type
- X and Y axes
- Key insight it would reveal
.exec

.print Final report saved to analysis-report.txt
```

### Example 2: Multi-Step Reasoning

```
.prompt "name":"Researcher", "version":"1.0", "params":{"model":"anthropic/claude-3.5-sonnet"}

# Teach reasoning pattern with examples
.user Question: Should we invest in solar panels?
.assistant Let me think through this systematically:

1. Financial Analysis:
   - Initial cost: High ($15-25K)
   - Savings: $100-200/month
   - ROI: 7-12 years

2. Environmental Impact:
   - Reduces carbon: ~4 tons/year
   - Clean energy: ~80% of usage

3. Practical Considerations:
   - Roof suitable: Need assessment
   - Maintenance: Minimal
   - Weather dependent: Yes

Conclusion: If planning to stay 10+ years and roof is suitable, likely worth it.

# Real question
.user Question: <<user_question>>
.exec
```

### Example 3: Function-Calling Workflow

```
.prompt "name":"FileProcessor", "version":"1.0"

# Teach tool use pattern
.system You can use readfile(filename) and writefile(filename, content) functions.

.user Read config.json
.tool_call readfile(filename="config.json") id=call_001
.tool_result id=call_001 name=readfile
{"theme": "dark", "language": "en"}
.assistant The config shows theme is dark and language is English.

# Real workflow
.user Read input.txt, convert to uppercase, and save as output.txt
.exec
# LLM will:
# 1. Generate readfile call
# 2. Receive result
# 3. Process text
# 4. Generate writefile call
```

### Example 4: Comparative Model Usage

```
.prompt "name":"ModelCompare", "version":"1.0"

.set topic "quantum computing"

# Fast model for breadth
.set model openai/gpt-4o-mini
.user List 10 key concepts in <<topic>>, one sentence each.
.exec
.set concepts <<last_response>>

# Smart model for depth
.set model openai/gpt-4
.user From these concepts:
<<concepts>>

Choose the 3 most important and explain each in detail for a beginner.
.exec
.set detailed <<last_response>>

# Creative model for analogy
.set model anthropic/claude-3.5-sonnet
.user Create 3 intuitive analogies to explain these concepts:
<<detailed>>
.exec

.print Complete educational content generated!
```

### Example 5: Error Handling Pattern

```
.prompt "name":"RobustProcessor", "version":"1.0"

# Teach error handling
.user Process: invalid data
.assistant Error: Input validation failed. Please provide data in CSV format with headers: name, value, date.

.user Process: name,value,date
alice,100,2024-01-01
.assistant Success: Processed 1 row. Summary: alice contributed 100 on 2024-01-01.

# Real usage with validation
.cmd readfile(filename="<<input_file>>") as data
.user Process this data:
<<data>>

If any errors, explain what's wrong and how to fix it.
If successful, provide a summary.
.exec
```

---

## Summary

### Key Takeaways

1. **Statements create messages** - The LLM only sees messages, not statements
2. **`.exec` sends everything** - All accumulated messages, including "fake" examples
3. **Few-shot learning is free** - Add examples without `.exec`, no API cost
4. **Variables persist** - Set once, use many times
5. **Functions extend capability** - Use `.cmd` to integrate external data/tools
6. **Model switching is easy** - Change models mid-conversation for optimal cost/quality
7. **Tool use can be taught** - Use `.tool_call` and `.tool_result` to show patterns

### Next Steps

1. **Practice basic patterns** - Start with simple few-shot examples
2. **Experiment with variables** - Use `<<variable>>` substitution
3. **Try function integration** - Use `.cmd readfile()` to process files
4. **Test model switching** - Compare outputs from different models
5. **Build complex workflows** - Combine techniques for real tasks

### Additional Resources

- [01-prompt-language.md](01-prompt-language.md) - Complete statement reference
- [03-statements-and-messages.md](03-statements-and-messages.md) - Deep architecture dive
- [creating-keprompt-functions.context.md](creating-keprompt-functions.context.md) - Custom functions

---

*KePrompt Knowledge Engineer's Guide v1.0*
*For KePrompt v2.0+*



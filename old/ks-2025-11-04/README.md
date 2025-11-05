# KePrompt Knowledge Store - LLM Context

**Purpose**: Rapid context restoration for LLMs working with KePrompt codebase.

## Essential Reading Order

1. **[what-is-keprompt.md](what-is-keprompt.md)** - Core understanding: what KePrompt is and why it exists
2. **[architecture-overview.md](architecture-overview.md)** - System components and relationships
3. **[json-api-system.md](json-api-system.md)** - Modern command interface (primary user interaction)
4. **[session-management.md](session-management.md)** - Conversation persistence and database backend

## Quick Context Restoration Paths

### For Integration Questions
→ `what-is-keprompt.md` → `json-api-system.md` → `integration-patterns.md`

### For Architecture Questions  
→ `architecture-overview.md` → `vm-execution-model.md` → `ai-provider-system.md`

### For Debugging Issues
→ `debugging-tools.md` → `session-management.md` → `database-system.md`

### For Feature Development
→ `development-workflows.md` → `function-system.md` → `configuration.md`

## Key Insights for LLM Context

- **KePrompt = Prompt Virtual Machine**: Executes `.prompt` files with AI interactions
- **Backend-as-Prompts**: AI logic in version-controlled `.prompt` files, separate from app code
- **JSON API Primary**: Modern REST-style commands (`get`, `create`, `update`, `delete`)
- **Session-Centric**: Database-backed conversation persistence and resumption
- **Production-Ready**: Cost tracking, logging, database management, TUI tools
- **Multi-Provider**: Abstracts OpenAI, Anthropic, Google, Mistral, DeepSeek, XAI, OpenRouter

## File Manifest

**Core Understanding**
- `what-is-keprompt.md` - Essential concept and value proposition
- `architecture-overview.md` - System structure and components
- `prompt-language.md` - `.prompt` file format and statements

**Modern Features**
- `json-api-system.md` - REST-style command interface
- `session-management.md` - Conversation persistence system
- `cost-tracking.md` - Financial monitoring and analysis
- `database-system.md` - SQLite backend and data management

**Developer Experience**
- `cli-interface.md` - Complete command reference
- `development-workflows.md` - How developers use KePrompt
- `integration-patterns.md` - Application integration methods
- `debugging-tools.md` - Troubleshooting and inspection tools

**Technical Details**
- `vm-execution-model.md` - Prompt virtual machine internals
- `ai-provider-system.md` - Multi-provider abstraction layer
- `function-system.md` - Built-in and custom function extensibility
- `configuration.md` - Setup, API keys, model definitions

## Context Restoration Strategy

1. **Start with `what-is-keprompt.md`** for fundamental understanding
2. **Read `json-api-system.md`** for modern usage patterns
3. **Reference specific files** based on the task at hand
4. **Use cross-references** to build comprehensive understanding

This knowledge store reflects KePrompt as it exists today: a sophisticated, production-ready prompt execution engine with database backend, session management, and comprehensive tooling.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KePrompt is a CLI tool and framework for prompt engineering across multiple AI providers (OpenAI, Anthropic, Google, DeepSeek, Mistral, XAI, OpenRouter). It features a custom `.prompt` DSL, a virtual machine executor, chat persistence via SQLite, cost tracking, and a web GUI. Version 2.4.0.

## Build & Development Commands

```bash
# Install for development (editable mode with dev deps)
pip install -e ".[dev]"

# Initialize workspace (required before first use)
keprompt database create
keprompt models update

# Run all tests
pytest test/

# Run a single test file
pytest test/epicure/prompts/functions/simulation_functions.py

# Format code
black keprompt/
isort keprompt/

# Build package
python3 -m build

# Release to PyPI (interactive)
python3 release.py
```

## Architecture

The system follows a layered architecture: CLI → JSON API → Managers → VM/Providers → Database.

### Request Flow

1. **CLI** (`keprompt.py`) parses `keprompt <object> <verb> [options]` commands using argparse with `rich_argparse`. Auto-detects output format: Rich tables for TTY, JSON when piped.
2. **JSON API** (`api.py`) routes commands to manager classes (`ChatManager`, `ModelManager`, `PromptManager`, etc.) that return structured JSON.
3. **Chat Manager** (`chat_manager.py`) handles chat lifecycle (create/reply/get/delete), serializes VM state to the database for multi-turn conversations.
4. **VM** (`keprompt_vm.py`) executes `.prompt` files statement-by-statement. This is the core engine (~1000+ lines). It manages variables, messages, model selection, and dispatches to AI providers. Statements: `.prompt`, `.exec`, `.user`, `.system`, `.assistant`, `.tool_call`, `.tool_result`, `.cmd`, `.set`, `.print`, `.include`, `.image`, `.debug`, `.clear`, `.exit`.
5. **AI Providers** (`AiProvider.py` base, `AiOpenAi.py`, `AiAnthropic.py`, etc.) each implement `prepare_request()`, `to_company_messages()`, `to_ai_message()`, `extract_token_usage()`, and `calculate_costs()`.
6. **Database** (`database.py`) uses Peewee ORM with SQLite by default. Tables: `Chat` (8-char ID, messages, serialized VM state), `CostTracking` (per-call costs/tokens), `ServerRegistry` (HTTP server management).

### Key Subsystems

- **Model Manager** (`ModelManager.py`): Model registry with pricing, provider routing, capability detection. Loads from `prompts/functions/model_prices_and_context_window.json`, updated via `keprompt models update`.
- **Config** (`config.py`): Loads from `~/.keprompt/config.toml`, `keprompt.toml`, or `.keprompt.toml`. Also loads `.env` (default `~/.env`) for API keys.
- **Function System** (`keprompt_function_space.py`): Built-in functions (`readfile`, `writefile`, `wwwget`, `execcmd`) plus dynamic loading from `prompts/functions/`. Used for LLM tool calling.
- **HTTP Server** (`http_server.py`): FastAPI-based REST API with web GUI, managed via `ServerRegistry`.
- **Output Formatter** (`output_formatter.py`): Formats responses as Rich tables or JSON based on TTY detection.

## Prompt Language (DSL)

`.prompt` files use a line-based syntax with `.` prefixed statements. Variable substitution uses `<<variable>>` syntax. The `.exec` statement triggers an LLM call. VM state is accessible via `<<VM.chat_id>>`, `<<VM.model_name>>`, `<<VM.total_cost>>`, etc.

Example:
```
.prompt "name":"Hello", "version":"1.0.0", "params":{"model":"gpt-4o"}
.system You are a helpful assistant.
.user Hello <<name>>, what can you help with?
.exec
.print Response: <<last_response>>
```

The language spec is documented in `ks/03-prompt-language.md`.

## Key Directories

- `keprompt/` — Main Python package
- `ks/` — Knowledge store: prompt language spec (`01`), engineering guide (`02`), statements/messages architecture (`03`), custom function protocol (`creating-keprompt-functions.context.md`)
- `prompts/` — User workspace: `.prompt` files, `chats.db`, custom functions
- `test/` — Test files and example prompts

## API Keys

Set via environment variables or `~/.env`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `XAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`.
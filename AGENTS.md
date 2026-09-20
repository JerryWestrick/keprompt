# AGENTS.md

This file provides guidance to Cursor when working with code in this repository.

## Project Overview

KePrompt is a CLI tool and framework for prompt engineering across multiple AI providers (OpenAI, Anthropic, Google, DeepSeek, Mistral, XAI, Cerebras, OpenRouter). It features a custom `.prompt` DSL, a virtual machine executor, chat persistence via SQLite, and cost tracking. Version 3.1.0.

## Build & Development Commands

```bash
# Install for development (editable mode with dev deps)
pip install -e ".[dev]"

# Initialize workspace (required before first use)
# Creates prompts/ and prompts/functions/, copies bundled defaults, initializes
# the database, updates the model registry, and loads functions.
keprompt init

# Run all tests
pytest test/

# Run a single test file
pytest test/test_llm_options.py

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
4. **VM** (`keprompt_vm.py`) executes `.prompt` files statement-by-statement. This is the core engine (~1,700 lines). It manages variables, messages, model selection, and dispatches to AI providers. Statements: `.prompt`, `.functions`, `.exec`, `.user`, `.system`, `.assistant`, `.text`, `.tool_call`, `.tool_result`, `.cmd`, `.set`, `.print`, `.include`, `.image`, `.debug`, `.clear`, `.exit`, `.#`.
5. **AI Providers** (`AiProvider.py` base, `AiOpenAi.py`, `AiAnthropic.py`, etc.) each implement `prepare_request()`, `to_company_messages()`, `to_ai_message()`, `extract_token_usage()`, and `calculate_costs()`.
6. **Database** (`database.py`) uses Peewee ORM with SQLite by default. Tables: `Info` (schema version), `Chat` (8-char ID, messages, serialized VM state, aggregates), `CostTracking` (one row per billed API round trip, keyed `(chat_id, msg_no, round_trip)` — a single `.exec` running a tool loop produces several). SQLite schema migrations live in `keprompt/migrations/`, driven by the transition registry in `migrate_sqlite.py`.

### Key Subsystems

- **Model Manager** (`ModelManager.py`): Model registry with pricing, provider routing, capability detection. Loads from `prompts/functions/model_prices_and_context_window.json`, updated via `keprompt models update`.
- **Config** (`config.py`): Loads from `~/.keprompt/config.toml`, `keprompt.toml`, or `.keprompt.toml`. Also loads `.env` (default `~/.env`) for API keys.
- **Function System** (`keprompt_function_space.py`): Built-in functions (`readfile`, `writefile`, `wwwget`, `execcmd`) plus dynamic loading from `prompts/functions/`. Used for LLM tool calling.
- **Output Formatter** (`output_formatter.py`): Formats responses as Rich tables or JSON based on TTY detection.

## Prompt Language (DSL)

`.prompt` files use a line-based syntax with `.` prefixed statements. Variable substitution uses `<<variable>>` syntax. The `.exec` statement triggers an LLM call. The `.functions` statement declares which functions the model can use (no `.functions` = no functions, safe default). VM state is accessible via `<<VM.chat_id>>`, `<<VM.model_name>>`, `<<VM.total_cost>>`, etc. As of v3.0.0, model request options belong in the `llm_options` dict and nowhere else — `temperature`, `max_tokens`, `top_p`, and `top_k` as top-level variables stop execution.

Example:
```
.prompt "name":"Hello", "version":"1.0.0", "params":{"model":"openai/gpt-4o", "llm_options":{"temperature":0.2}}
.system You are a helpful assistant.
.user Hello <<name>>, what can you help with?
.exec
.print Response: <<last_response>>
```

The language spec is documented in `ks/contracts/prompt-language.md`.

## Key Directories

- `keprompt/` — Main Python package
- `ks/` — Knowledge store; authoritative on design intent and public contracts (source is authoritative on current mechanics). Start at `ks/README.md` and pick a role. `ks/roles/` — maintainer, application-builder, prompt-engineer, production-optimizer. `ks/contracts/` — prompt language, external functions, JSON envelope, application shell, production database. `ks/internals/` — architecture, VM/messages, providers/models, persistence. The flat `01`/`02`/`03` files are redirect stubs.
- `DEFECTS.md` — record of discovered defects, with status and code paths
- `prompts/` — User workspace: `.prompt` files, `chats.db`, custom functions
- `test/` — Test files and example prompts

## API Keys

Set via environment variables or `~/.env`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `XAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`.
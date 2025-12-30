# KePrompt Knowledge Store

This directory contains comprehensive documentation about the KePrompt system for AI assistants and developers.

## What is KePrompt?

KePrompt is a sophisticated command-line tool and framework for prompt engineering and AI interaction. It provides a unified interface to multiple AI providers (OpenAI, Anthropic, Google, DeepSeek, Mistral, XAI, OpenRouter) with comprehensive features for production use.

## Documentation Structure

### Core Documentation
- **[01-overview.md](01-overview.md)** - High-level system architecture and design philosophy
- **[02-cli-interface.md](02-cli-interface.md)** - Complete command-line interface documentation
- **[03-prompt-language.md](03-prompt-language.md)** - The .prompt file language specification
- **[04-web-gui.md](04-web-gui.md)** - Web-based graphical interface
- **[05-knowledge-engineers-guide.md](05-knowledge-engineers-guide.md)** - Practical prompt engineering guide

## Quick Navigation

### For Knowledge Engineers (Prompt Designers)
Start with:
1. [05-knowledge-engineers-guide.md](05-knowledge-engineers-guide.md) - **Practical guide with examples**
2. [03-prompt-language.md](03-prompt-language.md) - Statement reference
3. [01-overview.md](01-overview.md) - System architecture

### For AI Assistants
Start with:
1. [01-overview.md](01-overview.md) - Understand the system
2. [03-prompt-language.md](03-prompt-language.md) - Learn the language
3. [05-knowledge-engineers-guide.md](05-knowledge-engineers-guide.md) - Practical techniques

### For Developers
Start with:
1. [01-overview.md](01-overview.md) - Architecture overview
2. [02-cli-interface.md](02-cli-interface.md) - CLI implementation
3. [03-prompt-language.md](03-prompt-language.md) - Language specification

### For End Users
Start with:
1. [02-cli-interface.md](02-cli-interface.md) - Command-line usage
2. [05-knowledge-engineers-guide.md](05-knowledge-engineers-guide.md) - Writing effective prompts
3. [04-web-gui.md](04-web-gui.md) - Using the web interface

## Key Features

### Object-First CLI Design
The new command-line interface follows REST principles with object-first syntax:
```bash
keprompt <object> <verb> [options]
```

Examples:
```bash
keprompt prompts get
keprompt models get --provider OpenRouter
keprompt chats create --prompt math-tutor
keprompt chats reply <chat-id> "Tell me more"
keprompt server start --web-gui
```

### Dual Output Modes
- **Human Mode (--pretty)**: Rich formatted tables for terminal use
- **Machine Mode (--json)**: Structured JSON for programmatic use
- **Auto-detection**: TTY = pretty, pipe = JSON

### Comprehensive Chat Management
- Create chats from prompts with parameters
- Continue conversations with context
- List and filter chat history
- Full conversation persistence with cost tracking

### Multi-Server Support
- Run multiple HTTP servers per directory
- Automatic process management and registry
- Health checking and status monitoring
- Optional web GUI per server

### Production-Ready Features
- Comprehensive cost tracking with SQLite
- Multi-mode logging (PRODUCTION, LOG, DEBUG)
- Error handling and validation
- API key management via .env files

## Recent Updates

### Version 1.9.2 Changes
- **New CLI Syntax**: Object-first REST-style commands
- **JSON API**: Unified API layer for all operations
- **Chat System**: Full chat lifecycle management
- **Server Management**: Multi-server HTTP support with web GUI
- **Dual Output**: Automatic format detection for human/machine use

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Interface                            │
│              (keprompt.py - argparse)                       │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    JSON API Layer                            │
│         (api.py - handles all commands)                      │
├─────────────┬───────────┬──────────────┬────────────────────┤
│  Resource   │  System   │    Chat      │    Server          │
│  Discovery  │   Mgmt    │   Manager    │   Manager          │
└─────────────┴───────────┴──────────────┴────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Core Components                             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ VM (Virtual  │ Model        │ Database     │ HTTP Server    │
│ Machine)     │ Manager      │ Manager      │ (FastAPI)      │
└──────────────┴──────────────┴──────────────┴────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Providers                                │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ OpenAI   │ Anthropic│ Google   │ DeepSeek │ Mistral, XAI... │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

## File Organization

### Project Structure
```
keprompt/
├── keprompt/           # Main package
│   ├── __init__.py
│   ├── __main__.py
│   ├── keprompt.py     # CLI entry point
│   ├── api.py          # JSON API layer
│   ├── chat_manager.py # Chat lifecycle
│   ├── keprompt_vm.py  # Virtual Machine
│   ├── AiProvider.py   # Base provider
│   ├── AiOpenAi.py     # OpenAI implementation
│   ├── AiAnthropic.py  # Anthropic implementation
│   ├── ModelManager.py # Model registry
│   ├── database.py     # Database layer
│   ├── http_server.py  # REST API server
│   └── ...
├── prompts/            # User prompt files
│   ├── *.prompt        # Prompt files
│   ├── functions/      # Custom functions
│   ├── chats.db        # Chat database
│   └── sessions.db     # Legacy sessions
├── web-gui/            # Web interface
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── ks/                 # This knowledge store
└── docs/               # Additional documentation
```

## Usage Patterns

### Basic Workflow
1. Initialize workspace: `keprompt prompts get`
2. Set API key: Configure provider credentials
3. Create prompt: Write .prompt file
4. Execute: `keprompt chats create --prompt <name>`
5. Continue: `keprompt chats reply <id> "message"`

### Advanced Workflows
- HTTP server with GUI: `keprompt server start --web-gui`
- Cost analysis: Query chats.db for detailed tracking
- Multi-turn conversations: Use chat management commands
- Custom functions: Create executable tools in functions/

## Learning Path

1. **Start Here**: Read [01-overview.md](01-overview.md) for the big picture
2. **CLI Basics**: Review [02-cli-interface.md](02-cli-interface.md)
3. **Write Prompts**: Study [03-prompt-language.md](03-prompt-language.md)
4. **Understand Execution**: Read [04-vm-architecture.md](04-vm-architecture.md)
5. **API Integration**: Explore [05-json-api.md](05-json-api.md)
6. **Advanced Features**: Dive into specific topics as needed

## Glossary

- **VM**: Virtual Machine - executes prompt statements
- **Statement**: A single line in a .prompt file (e.g., `.user`, `.exec`)
- **Chat**: A conversation instance with full persistence
- **Session**: Legacy term for chat/conversation
- **Provider**: AI API service (OpenAI, Anthropic, etc.)
- **Model**: Specific AI model (gpt-4o, claude-3-5-sonnet, etc.)
- **Function**: Callable tool for prompts (built-in or custom)
- **Server Registry**: System for managing multiple HTTP servers

## Version Information

- Current Version: 1.9.2
- Python: 3.8+
- Key Dependencies: Rich, FastAPI, Uvicorn, Peewee, python-dotenv

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/JerryWestrick/keprompt
- Documentation: See individual topic files in this directory

---

*Last Updated: 2025-11-04*
*For KePrompt v1.9.2*

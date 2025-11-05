# KePrompt System Overview

## Introduction

KePrompt is a sophisticated command-line framework for prompt engineering and AI interaction. It provides a unified, production-ready interface to multiple AI providers with comprehensive features for development, deployment, and cost management.

## Design Philosophy

### 1. **Unified Multi-Provider Interface**
One tool to interact with all major AI providers:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus/Haiku)
- Google (Gemini Pro, Gemini Flash)
- DeepSeek
- Mistral AI
- XAI (Grok)
- OpenRouter (aggregator)

### 2. **Object-First REST-Style CLI**
Following REST principles with intuitive syntax:
```bash
keprompt <object> <verb> [options]
```

This aligns with modern API design and makes the system predictable and easy to learn.

### 3. **Dual Output Modes**
- **Human Mode** (`--pretty`): Rich formatted tables for terminal use
- **Machine Mode** (`--json`): Structured JSON for programmatic use
- **Auto-detection**: Automatically selects format based on TTY

### 4. **Production-Ready from Day One**
- Comprehensive cost tracking and reporting
- Multi-mode logging (PRODUCTION, LOG, DEBUG)
- Error handling and validation
- API key management via .env files
- Database persistence for all interactions

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Interface Layer                       │
├──────────────────────┬──────────────────────────────────────┤
│    CLI (Terminal)    │    HTTP REST API + Web GUI           │
└──────────────────────┴──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Command Parser Layer                        │
│           (keprompt.py - argparse + normalization)          │
└──────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    JSON API Layer                            │
│              (api.py - unified interface)                    │
├───────────┬──────────┬──────────────┬──────────────────────┤
│ Resource  │ System   │   Chat       │   Server             │
│ Discovery │ Mgmt     │   Manager    │   Manager            │
└───────────┴──────────┴──────────────┴──────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Core Components                             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ VM           │ Model        │ Database     │ Function       │
│ (Executor)   │ Manager      │ Manager      │ System         │
└──────────────┴──────────────┴──────────────┴────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  AI Provider Layer                           │
│              (Unified abstraction)                           │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ OpenAI   │ Anthropic│ Google   │ DeepSeek │ Others...       │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

### Key Components

#### 1. CLI Interface (`keprompt.py`)
- Entry point for all command-line operations
- Argument parsing with rich help formatting
- Command normalization (aliases → canonical forms)
- Output format detection and routing

#### 2. JSON API Layer (`api.py`)
- Unified interface for all operations
- Standardized JSON response format
- Error handling and validation
- Manager routing (Resource, System, Chat, Server)

#### 3. Virtual Machine (`keprompt_vm.py`)
- Executes .prompt files statement by statement
- Manages execution state and context
- Variable substitution and scoping
- Statement type dispatch

#### 4. Chat Manager (`chat_manager.py`)
- Full lifecycle management (create, update, delete)
- Conversation persistence
- Cost tracking integration
- State serialization/deserialization

#### 5. Model Manager (`ModelManager.py`)
- Centralized model registry
- Pricing information
- Capability detection
- Provider routing

#### 6. Database Manager (`database.py`)
- SQLite-based persistence
- Chat storage and retrieval
- Cost tracking records
- Query and reporting

#### 7. HTTP Server (`http_server.py`)
- FastAPI-based REST API
- Optional web GUI serving
- CORS support
- Health monitoring

## Data Flow

### Executing a Prompt

```
1. User Command
   keprompt chats create --prompt math-tutor --param topic "algebra"
   
2. CLI Parsing (keprompt.py)
   - Parse arguments
   - Normalize command aliases
   - Detect output format
   
3. JSON API Routing (api.py)
   - Route to ChatManager
   - Build argparse.Namespace
   
4. Chat Manager (chat_manager.py)
   - Create VM instance
   - Load prompt file
   - Set parameters
   
5. VM Execution (keprompt_vm.py)
   - Parse .prompt file
   - Execute statements sequentially
   - Call AI provider via AiPrompt
   
6. AI Provider (AiOpenAi.py, etc.)
   - Format request for provider
   - Send HTTP request
   - Parse response
   
7. Response Processing
   - Update VM state
   - Track costs
   - Log execution
   
8. Persistence (database.py)
   - Save chat state
   - Record cost data
   - Update metadata
   
9. Output
   - Format response (table or JSON)
   - Display to user
```

### Chat Continuation

```
1. User Command
   keprompt chats reply <chat-id> "Explain quadratic formula"
   
2. Load Existing Chat
   - Query database
   - Deserialize VM state
   - Restore messages
   
3. Add New Message
   - Create .user statement
   - Add .exec statement
   
4. Execute from Resume Point
   - Continue from last IP
   - Call AI provider
   - Update state
   
5. Save Updated State
   - Serialize new state
   - Update database
   - Track additional costs
```

## Key Design Patterns

### 1. **Statement Pattern**
Each .prompt file consists of statements that are executed sequentially:
```python
class StmtPrompt:
    def execute(self, vm: VM) -> None:
        # Base implementation
        
class StmtUser(StmtPrompt):
    def execute(self, vm: VM) -> None:
        # Specialized implementation
```

### 2. **Provider Abstraction**
All AI providers implement a common interface:
```python
class AiProvider:
    def ask(self, messages) -> response
    def stream(self, messages) -> iterator
```

### 3. **Manager Pattern**
Each major feature has a manager class:
- `ChatManager` - Chat lifecycle
- `ModelManager` - Model registry
- `DatabaseManager` - Persistence
- `ServerManager` - HTTP servers

### 4. **Dual Output Pattern**
All commands support both human and machine formats:
```python
if args.pretty:
    return rich_table
else:
    return json_structure
```

### 5. **Normalization Pattern**
All command aliases are normalized to canonical forms:
```python
def normalize_command_aliases(args):
    if args.chat_command in ['list', 'show', 'view']:
        args.chat_command = 'get'
```

## File Structure

### Source Code Organization

```
keprompt/
├── __init__.py           # Package initialization
├── __main__.py           # python -m keprompt entry
├── keprompt.py           # CLI interface
├── api.py                # JSON API layer
├── chat_manager.py       # Chat operations
├── keprompt_vm.py        # Virtual machine
├── Prompt.py             # Prompt metadata
├── AiPrompt.py           # Message formatting
├── AiProvider.py         # Provider base class
├── AiOpenAi.py           # OpenAI implementation
├── AiAnthropic.py        # Anthropic implementation
├── AiGoogle.py           # Google implementation
├── AiDeepSeek.py         # DeepSeek implementation
├── AiMistral.py          # Mistral implementation
├── AiXai.py              # XAI implementation
├── AiOpenRouter.py       # OpenRouter implementation
├── ModelManager.py       # Model registry
├── database.py           # Database layer
├── config.py             # Configuration
├── http_server.py        # REST API server
├── server_registry.py    # Server management
├── function_loader.py    # Function system
├── keprompt_functions.py # Built-in functions
├── keprompt_builtins.py  # Core builtins
├── keprompt_logger.py    # Logging system
├── cost_tracker.py       # Cost tracking
├── cost_cli.py           # Cost reporting
└── ...
```

### Runtime Directory Structure

```
project/
├── prompts/              # User workspace
│   ├── *.prompt          # Prompt files
│   ├── chats.db          # Chat database
│   ├── functions/        # Custom functions
│   │   ├── functions.json
│   │   └── custom_*      # User functions
│   └── logs/             # Execution logs
├── logs/                 # Alternative log location
└── .keprompt/            # Configuration (optional)
```

## Configuration

### API Keys
Stored in .env file (default: ~/.env):
```bash
# Add keys to ~/.env file
echo 'OPENAI_API_KEY=sk-...' >> ~/.env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> ~/.env

# Or use environment variables directly:
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Model Registry
JSON files in package data:
```
prompts/functions/model_prices_and_context_window.json
```

Updated via:
```bash
keprompt models update --provider OpenAI
```

## Execution Modes

### 1. Production Mode (Default)
- Clean output to STDOUT
- Development logs to STDERR
- Automatic cost tracking
- No verbose debugging

### 2. Log Mode (`--debug`)
- Detailed statement logging
- Execution traces
- API call details
- File logging enabled

### 3. Debug Mode (Internal)
- VM state inspection
- Statement-by-statement traces
- Variable dumps
- Full exception traces

## Extension Points

### 1. Custom Functions
Add executable scripts in `prompts/functions/`:
```bash
#!/usr/bin/env python3
# Custom function implementation
```

### 2. New AI Providers
Implement `AiProvider` interface:
```python
class AiNewProvider(AiProvider):
    def ask(self, messages):
        # Provider-specific implementation
```

### 3. Custom Statements
Add to `StatementTypes` dictionary:
```python
class StmtCustom(StmtPrompt):
    def execute(self, vm: VM):
        # Custom logic
```

### 4. Database Extensions
Add new Peewee models:
```python
class CustomTracking(BaseModel):
    # Additional tracking fields
```

## Security Considerations

### 1. API Key Management
- .env file storage (default: ~/.env)
- Environment variable support
- Never logged or displayed
- Secure transmission only

### 2. Command Execution
- Function validation
- Path sanitization
- Permission checking
- Sandbox considerations

### 3. Database Security
- Local SQLite files
- File permissions
- No remote access
- Encryption available

## Performance Characteristics

### Execution Speed
- CLI startup: ~100-300ms (model loading)
- Command execution: <50ms (excluding API calls)
- Database queries: <10ms (local SQLite)
- API calls: Variable (provider-dependent)

### Memory Usage
- Base: ~50-100 MB (Python runtime + deps)
- With chat history: +10-50 MB per session
- Model registry: ~5 MB
- Minimal growth during execution

### Scalability
- Handles 1000s of prompts efficiently
- SQLite supports millions of chat records
- Server can handle multiple concurrent requests
- Function system is dynamically loaded

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock AI provider responses
- Database operations
- Parser validation

### Integration Tests
- End-to-end command flows
- Multi-provider scenarios
- Cost tracking accuracy
- State persistence

### Manual Testing
- Real AI provider interactions
- Cost validation
- User workflow testing
- Performance profiling

## Future Directions

### Planned Features
- Streaming responses for long outputs
- Batch processing capabilities
- Advanced conversation branching
- Team collaboration features
- Cloud synchronization
- Plugin system

### Under Consideration
- GUI desktop application
- Mobile companion app
- Integration with IDEs
- Marketplace for prompts/functions
- Enterprise features

## Getting Help

### Documentation
- This knowledge store (ks/)
- README.md for quick start
- Individual module docstrings
- Example prompts in prompts/

### Community
- GitHub Issues
- Discussions
- Contributing Guide
- Release Notes

---

**Next Steps:**
- Review [02-cli-interface.md](02-cli-interface.md) for command-line usage
- Study [03-prompt-language.md](03-prompt-language.md) for writing prompts
- Explore [04-vm-architecture.md](04-vm-architecture.md) for execution details

*Last Updated: 2025-11-04*
*For KePrompt v1.9.2*

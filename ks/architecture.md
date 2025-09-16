# KePrompt Architecture

## Core Components

### 1. Prompt Virtual Machine (VM)
- **Location**: `keprompt/keprompt_vm.py`
- **Purpose**: Parses and executes `.prompt` files line by line
- **Key Features**: Variable substitution, statement execution, conversation state management
- **Statements**: `.llm`, `.user`, `.system`, `.exec`, `.cmd`, `.print`, `.set`, `.include`, etc.

### 2. AI Provider Abstraction Layer
- **Location**: `keprompt/AiProvider.py` (base class), `keprompt/Ai*.py` (implementations)
- **Purpose**: Unified interface across different AI services
- **Providers**: OpenAI, Anthropic, Google, Mistral, DeepSeek, XAI, OpenRouter
- **Responsibilities**: API formatting, authentication, response parsing, token counting, cost calculation

### 3. Model Registry
- **Location**: `keprompt/AiRegistry.py`
- **Purpose**: Dynamic model discovery and management
- **Features**: Model metadata (costs, context limits, capabilities), provider mapping
- **Data Source**: JSON files in `prompts/models/` directory

### 4. Function System
- **Location**: `keprompt/keprompt_functions.py`, `keprompt/function_loader.py`
- **Purpose**: Extensible function calls from within prompts
- **Built-ins**: `readfile()`, `writefile()`, `wwwget()`, `execcmd()`, `askuser()`
- **Custom Functions**: Executable files in `prompts/functions/` directory

### 5. Logging & Monitoring
- **Location**: `keprompt/keprompt_logger.py`
- **Purpose**: Structured logging for debugging and production monitoring
- **Modes**: Production, Debug, Log-to-file
- **Captures**: Token usage, costs, function calls, conversation flow

## Data Flow

1. **CLI Invocation**: `keprompt -e prompt_name --param key value`
2. **VM Initialization**: Load prompt file, parse global variables
3. **Statement Execution**: Process each line (`.user`, `.system`, `.exec`, etc.)
4. **Provider Selection**: Route to appropriate AI provider based on `.llm` statement
5. **API Communication**: Format request, make API call, parse response
6. **Function Execution**: Handle `.cmd` statements via function system
7. **Output Generation**: Return results via stdout or logging system

## Key Relationships

- **VM** orchestrates execution and manages state
- **AiProvider** implementations handle provider-specific API details
- **AiRegistry** provides model metadata and routing
- **FunctionLoader** discovers and executes custom functions
- **Logger** captures execution details across all components

## Extension Points

- **New AI Providers**: Implement `AiProvider` base class
- **Custom Functions**: Add executable files to `prompts/functions/`
- **New Statement Types**: Extend VM with new `.statement` handlers
- **Model Definitions**: Add JSON files to `prompts/models/`

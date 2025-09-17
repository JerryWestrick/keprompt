# KePrompt Core Concepts

## Backend-as-Prompts Philosophy

### Separation of Concerns
- **Application Code**: Handles business logic, data processing, user interfaces
- **Prompt Files**: Contains AI interaction logic, model configuration, conversation flow
- **Integration Layer**: CLI calls bridge the two domains

### Benefits
- **Independent Development**: Prompt engineers and application developers work in parallel
- **Model Agnostic**: Switch AI providers without touching application code
- **Version Control**: Prompts are versioned alongside code, enabling proper release management
- **Testing**: Prompts can be tested independently with different models and parameters

## CLI-First Design

### Why CLI is Primary Interface
- **Universal Integration**: Any programming language can call subprocess
- **Simple Deployment**: No additional services or dependencies required
- **Debugging**: `--debug` flag provides immediate feedback during development
- **Shell Integration**: Easy to use in scripts, CI/CD pipelines, cron jobs
- **Containerization**: Works seamlessly in Docker containers and serverless environments

### Integration Pattern
```bash
# Application calls KePrompt via subprocess
keprompt -e customer_support --param message "Help me" --param user_id "123"
```

## Prompt Language Design

### Statement-Based Execution
- **Declarative**: Each line declares what should happen (`.user`, `.system`, `.exec`)
- **Sequential**: Statements execute in order, building conversation context
- **Variable Substitution**: `<<variable>>` syntax for dynamic content
- **Function Calls**: `.cmd function_name(param=value)` for external operations

### Required Prompt Metadata
**Every prompt file must start with a `.prompt` statement** containing structured metadata:
```
.prompt "name":"Semantic Name", "version":"1.0.0", "params":{"model":"gpt-4o-mini"}
```
- **name**: Human-readable prompt name (used in cost tracking and reports)
- **version**: Semantic version for tracking prompt evolution
- **params**: Optional parameter documentation and defaults

### Key Statements
- `.prompt` - **REQUIRED** - Define prompt metadata (name, version, parameters)
- `.llm {"model": "gpt-4o"}` - Configure AI model and parameters
- `.system` - Set system/assistant instructions
- `.user` - Add user message to conversation
- `.exec` - Send conversation to AI and get response
- `.cmd` - Call built-in or custom functions
- `.print` - Output text to console
- `.set` - Assign variables for later use

## Production Considerations

### Cost Management
- **Token Tracking**: Every API call logs input/output tokens and costs
- **Model Comparison**: Built-in tools to compare pricing across providers
- **Budget Controls**: Monitoring and alerting for cost thresholds

### Reliability
- **Error Handling**: Graceful failure modes with detailed error messages
- **Conversation State**: Save/resume multi-turn conversations
- **Logging**: Comprehensive execution logs for debugging and monitoring
- **Fallback Strategies**: Ability to retry with different models on failure

### Scalability
- **Stateless Execution**: Each prompt execution is independent
- **Parallel Processing**: Multiple prompt executions can run concurrently
- **Resource Efficiency**: Minimal memory footprint and fast startup time

## Development Workflow

### Prompt Engineering Cycle
1. **Write**: Create `.prompt` file with desired AI interaction
2. **Test**: Run with `keprompt -e prompt_name --debug`
3. **Iterate**: Refine based on output quality and cost
4. **Integrate**: Application calls via CLI with real parameters
5. **Monitor**: Track performance and costs in production

### Team Collaboration
- **Prompt Engineers**: Focus on AI interaction design and optimization
- **Application Developers**: Focus on business logic and integration
- **DevOps**: Handle deployment, monitoring, and cost optimization
- **QA**: Test prompt reliability across different models and scenarios

# KePrompt Project Overview

## What KePrompt Is
KePrompt is a command-line tool that serves as a "prompt virtual machine" - it executes `.prompt` files containing AI interactions using a custom domain-specific language. It abstracts away the complexity of different AI providers (OpenAI, Anthropic, Google, etc.) behind a unified interface.

## Core Value Proposition
**Backend-as-Prompts**: KePrompt enables teams to implement AI-powered backend logic using prompts instead of traditional code, with complete separation between application code and prompt engineering.

## Key Characteristics
- **CLI-First**: Primary interface is command-line, making it universally integrable across programming languages
- **Provider Agnostic**: Switch between AI models/providers without changing application code
- **Production Ready**: Built-in logging, cost tracking, conversation management, and error handling
- **Function System**: Extensible with built-in functions (file ops, web requests) and custom functions
- **Cost Conscious**: Token usage tracking and model comparison tools

## Primary Use Cases
1. **Application Integration**: Applications call `keprompt -e prompt_name --param key value` via subprocess
2. **Prompt Development**: Engineers use `--debug` flag for rapid iteration and testing
3. **Production AI Services**: Reliable AI backend services with proper monitoring and cost control
4. **Model Migration**: Easy switching between AI providers as models improve or costs change

## Architecture Philosophy
- Prompts are first-class citizens, version controlled alongside code
- AI logic lives in `.prompt` files, business logic stays in application code
- CLI provides universal integration point for any programming language
- Extensible function system allows custom integrations and workflows

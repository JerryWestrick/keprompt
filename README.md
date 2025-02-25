# KEPrompt

A prompt engineering tool for interacting with various large language model APIs.

## Features

- Supports multiple LLM providers (Anthropic, OpenAI, Google, MistralAI, DeepSeek, XAI)
- Command line interface for executing prompt templates
- Integrated function calling
- API key management via system keyring
- Rich terminal output

## Installation

```bash
pip install keprompt
```

## Usage

```bash
# List available models
keprompt -m

# List available functions
keprompt -f

# List available prompts
keprompt -p

# Execute a prompt
keprompt -e "PromptName"
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/keprompt.git
cd keprompt

# Install with Poetry
poetry install

# Run the tool
poetry run keprompt
```

## License

[MIT](LICENSE)


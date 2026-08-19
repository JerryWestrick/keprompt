# KePrompt Knowledge Store Purpose

This directory is the LLM interface to KePrompt. It is written for frontier models, not as end-user documentation.

After reading this knowledge store, an LLM should be able to:

- understand the KePrompt runtime and `.prompt` language;
- generate and modify prompts;
- generate and modify executable function toolchains;
- understand, modify, and validate KePrompt itself;
- operate and test the resulting system.

## Enterprise Prompt Development

KePrompt stores production conversations, execution state, model usage, cost, and timing in `prompts/chats.db`.

The intended workflow is:

1. Read this knowledge store.
2. Analyze the supplied production `chats.db`.
3. Derive representative production examples and evaluation criteria.
4. Change prompts and functions to achieve the requested goals.
5. Test the changes against the production examples.
6. Report effectiveness, regressions, cost, and timing with comparative statistics.
7. Repeat with alternative or newer models to find quality improvements or cost reductions.

Use KePrompt's existing prompts, functions, runtime, and SQLite evidence to perform this work. Do not assume a separate testing framework or new product feature is required.
# Role: Application Prompt Engineer

Goal: create or change an application's prompts and executable function toolchains.

## Required reading

1. The application's own KS: business intent, invariants, data ownership, and evaluation goals.
2. [`../contracts/prompt-language.md`](../contracts/prompt-language.md)
3. [`../contracts/external-functions.md`](../contracts/external-functions.md)
4. [`../contracts/application-shell.md`](../contracts/application-shell.md) when running tests.

## Responsibility split

- LLM: language understanding, semantic interpretation, and presentation.
- Functions: deterministic lookup, validation, side effects, and access to application systems.
- Application/database: business rules and authoritative state.

Do not teach the model data or rules that an authoritative function or database should resolve. Function names, descriptions, schemas, implementations, and prompt narrative must remain aligned.

## Workflow

1. Read the application KS and current prompt/function files.
2. State the intended behavior and invariants before editing.
3. Change the smallest appropriate layer.
4. Validate function discovery and standalone execution.
5. Run the prompt through the same shell command used by the application.
6. Inspect the JSON answer and saved chat, including tool calls and results.
7. Test normal, ambiguous, and failure cases.
8. For production-derived comparison, follow [`production-optimizer.md`](production-optimizer.md).

Use `.functions` with least privilege. No `.functions` statement means the model receives no tools.
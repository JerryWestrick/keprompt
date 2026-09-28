# Role: Application Prompt Engineer

Goal: create or change an application's prompts and executable function toolchains.

## Required reading

1. The application's own KS: business intent, invariants, data ownership, and evaluation goals. If it does not exist yet, start it from [`../examples/application-ks.md`](../examples/application-ks.md).
2. [`../contracts/prompt-language.md`](../contracts/prompt-language.md)
3. [`../contracts/external-functions.md`](../contracts/external-functions.md)
4. [`../contracts/application-shell.md`](../contracts/application-shell.md) when running tests.
5. [`../examples/`](../examples/README.md): worked prompts for `.question` dispatch and `.guard`.

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

## Classifying with an LDM

Use `.question` + `.evaluate` when a cheap, selection-only decision should shape the prompt — e.g.
which instructions or tools to load — rather than asking the LLM to choose among many similar ones.
Write the options from the application KS's domain; an LDM can only pick one of them. Gate on
`confidence` where a wrong pick is costly. Example: [`../examples/intent-dispatch.prompt`](../examples/intent-dispatch.prompt).

## Guarding external text

1. List every channel external text enters by: `--set` / `--set-from-json` (`#._cmdargs`), reply
   messages (`#._userinput`), `.include` (`#._include`), and each function in `.functions` or `.cmd`
   (`#.<function>`). A channel with no guard passes; model output needs none.
2. Write each guard's criteria from what this prompt legitimately does, per channel. A generic
   "is this an instruction to an AI?" rejects legitimate imperative traffic.
3. Choose the `fail:` threshold as policy: the more irreversible the actions the prompt can take,
   the lower it goes. Record the choice in the application KS.
4. Test with real traffic, including operator traffic: every guard execution is a `guard` message in
   `prompts/chats.db` (see [`../contracts/production-database.md`](../contracts/production-database.md)),
   so passes and rejections can be collected with SQL and replayed as a test set.

Example: [`../examples/guarded-assistant.prompt`](../examples/guarded-assistant.prompt).


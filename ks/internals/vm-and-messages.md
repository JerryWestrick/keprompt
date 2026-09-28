# VM and Messages

`VM` in `keprompt_vm.py` owns statements, variables, model state, universal messages, counters, and pending cost rows.

## Lifecycle

1. Resolve a logical prompt under `prompts/`.
2. Parse lines into `Stmt*` instances using `StatementTypes`.
3. Execute sequentially using `vm.ip`.
4. Message statements append provider-independent `AiMessage` parts.
5. `.exec` selects a model, calls `AiPrompt.ask()`, runs the provider tool loop, and records each billed request.
6. `ChatManager.save_chat()` serializes statements, messages, variables, VM state, aggregates, and pending costs.
7. Reply restores the VM, appends `.user` and `.exec`, executes, and saves the same chat identity.

## Message layers

```text
.prompt statements -> universal AiMessage/Ai*Part -> provider-specific request
```

Only statements and universal state are persisted. Provider formats are generated per request.

## Adding or changing a statement

Update the `Stmt*` implementation and `StatementTypes`; preserve substitution, logging, serialization, auto-completion, and reply behavior. Update `contracts/prompt-language.md` and add tests.

Do not confuse `.exec` statements with billed round trips: a tool loop can issue multiple requests.

## One execute, two units

`StmtExec.execute()` is the whole execute for every model. `.evaluate` (`StmtEvaluate`) subclasses it and differs only in hooks: `resolve_model`, `refuse_wrong_mode`, `model_loaded`, `before_call` (the content), `after_call` (where answers go) and `output_scope` (where outputs such as `_provider_selected_model` land: `$` for `.exec`, the question set for `.evaluate`). Before adding anything LDM-specific, look for the slot the LLM path already has. Design record: `design/ldm-execute.md`.

A guard run is the same execute again: `GuardRun` subclasses `StmtEvaluate` and is started by `VM.guard(channel, text, guard=None)`, not by a statement. The channels call it — `.guard _cmdargs`, a reply's `.user`, `.include`, `.cmd`, and the tool loop in `AiProvider.call_functions()` (outside its `try`, so a rejection is not handed back to the model as a function error). It can fire inside another execute, so `VM.execute_unit_preserved()` keeps that execute's model registers and `vm.prompt` state. Its request is numbered in the enclosing statement's round trips: `VM.next_round_trip()` is the one counter per statement.

Text-adding statements write to `AiPrompt.current_message()` — the last conversation message — never to an `ldm` or `guard` record, which sit in the same list.

Each unit's model follows one pattern with a different scope: `.exec`'s line model is kept in `$.llm_model` for the prompt; a question set's model (from its `.question` or `.evaluate` line) is kept in `?.<name>._model` for that set, falling back to `$.ldm_model`.

## The prompt's name

`prompt_name_for(filename)` in `keprompt_vm.py` is the only rule: the file's basename, or `chat` with no file. It names `vm.prompt_name`, the log, `chats.prompt_name`, `cost_tracking.prompt_semantic_name` and the prompt listing. A `"name"` on the `.prompt` line is ignored with a warning.
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
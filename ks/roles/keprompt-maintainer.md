# Role: KePrompt Maintainer

Goal: understand, modify, validate, package, or release KePrompt itself.

## Required reading

1. [`../internals/architecture.md`](../internals/architecture.md)
2. The internal document for the subsystem being changed.
3. Every public contract affected by the change.

## Workflow

1. Inspect the implementation and callers before editing.
2. Preserve the application shell/JSON boundary unless intentionally changing its contract.
3. Preserve prompt/message serialization and chat continuity.
4. Add or update tests for changed behavior.
5. Update affected KS contracts in the same change.
6. Run:

```bash
./.venv/bin/python -m pytest test/
./.venv/bin/python -m keprompt --version
./.venv/bin/python -m keprompt prompts get --json
```

7. For packaging changes, build with `python -m build` and inspect the wheel contents.

Do not add application-specific business behavior to KePrompt. KePrompt supplies the runtime, contracts, persistence, and model/tool abstraction; applications supply intent and business rules.
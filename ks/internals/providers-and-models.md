# Providers and Models

`ModelManager` loads the model registry, maps model keys to `AiModel`, and maps providers to adapter classes.

Each `AiProvider` adapter implements:

- provider request URL, headers, and body;
- universal-to-provider message conversion;
- provider response-to-universal conversion;
- token extraction;
- cost calculation.

`AiProvider.call_llm()` owns the request/tool-result loop. Each HTTP request appends one entry to `AiPrompt.round_trips`; `StmtExec` folds that ledger into VM totals and pending database rows.

When changing a provider:

1. Preserve universal message semantics, including tool IDs and results.
2. Verify tool filtering uses `vm.allowed_functions`.
3. Verify token and elapsed-time extraction on success and error.
4. Verify pricing units against the registry.
5. Add mocked tests; never require paid API calls in the normal suite.

Known limitation: token extraction is input/output only. Provider cache creation/read token classes are not separately priced.
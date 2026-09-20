# Providers and Models

`ModelManager` loads the model registry, maps model keys to `AiModel`, and maps providers to adapter classes.

Each `AiProvider` adapter implements:

- provider request URL, headers, and body;
- universal-to-provider message conversion;
- provider response-to-universal conversion;
- token extraction;
- cost calculation.

`AiProvider.call_llm()` owns the request/tool-result loop. Each HTTP request appends one entry to `AiPrompt.round_trips`; `StmtExec` folds that ledger into VM totals and pending database rows.

## The system prompt

A `.system` statement produces a universal message with role `system`. Providers do not agree on how to carry it, so each adapter must place it deliberately:

| Mechanism | Providers |
|---|---|
| Top-level `system` request parameter | anthropic |
| Top-level `system_instruction` | gemini |
| A `{"role": "system"}` entry in `messages` | openai, openrouter, deepseek, mistral, xai, cerebras |

Anthropic does not accept a `system` role in `messages` and never as `messages[0]`; it must be the top-level parameter. Adapters using a top-level field set `self.system_message` in `to_company_messages()` and read it back in `prepare_request()` — `call_llm()` always calls them in that order, and the provider instance is built fresh per `.exec`. `AiProvider.system_text()` flattens a system message's text parts; use it rather than `content[0].text`, because consecutive `.system` statements merge into one message with several parts.

Never fold the system prompt into a user message. Every provider KePrompt supports has a real mechanism.

When changing a provider:

1. Preserve universal message semantics, including tool IDs and results.
2. Verify tool filtering uses `vm.allowed_functions`.
3. Verify token and elapsed-time extraction on success and error.
4. Verify pricing units against the registry.
5. Verify the system prompt reaches the request, and that a prompt with no `.system` still builds.
6. Add mocked tests; never require paid API calls in the normal suite.

Known limitation: token extraction is input/output only. Provider cache creation/read token classes are not separately priced.
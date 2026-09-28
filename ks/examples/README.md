# Examples

Worked `.prompt` files for the features the contracts define. Each runs as written from an
application root after `keprompt init` (TypeSafe and OpenAI keys required).

| File | Shows |
|---|---|
| [`intent-dispatch.prompt`](intent-dispatch.prompt) | `.question` + `.evaluate` to classify a request, then `.include` only that intent's instructions |
| [`guarded-assistant.prompt`](guarded-assistant.prompt) | `.guard` on command-line input, reply messages and a tool's results, with domain-anchored criteria |
| [`application-ks.md`](application-ks.md) | A template for an application's own knowledge store |

Contracts: [`../contracts/prompt-language.md`](../contracts/prompt-language.md) (LDM questions, Guards).

# JSON Output Contract

With `--json`, KePrompt writes one JSON envelope to stdout.

```json
{
  "success": true,
  "data": {},
  "error": null,
  "stdout": null,
  "meta": {
    "schema_version": 1,
    "command": "chat",
    "args": {},
    "variables": null,
    "timestamp": "...Z",
    "version": "2.16.1"
  },
  "ai_response": "...",
  "chat_id": "abcdefgh"
}
```

- `data`: manager payload on success; `null` on failure.
- `error`: `null` on success; error object or message on failure.
- `stdout`: output produced by prompt `.print` statements, otherwise `null`.
- `meta.variables`: returned VM variables when the manager exposes them.
- `ai_response` and `chat_id`: present for chat responses when available.

On an executed command failure, KePrompt emits a failure envelope, writes a concise diagnostic to stderr, and exits non-zero. Argument parsing errors may occur before JSON mode is established; they exit non-zero with stderr and may produce no JSON.

Consumers must check exit status, tolerate missing optional fields, and use `ai_response` as the primary answer field.
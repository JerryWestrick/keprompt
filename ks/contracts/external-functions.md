# External Function Contract

KePrompt discovers executable files in `prompts/functions/`. One executable may expose multiple functions.

## Discovery

```bash
./prompts/functions/provider --list-functions
```

Return a JSON array of function definitions:

```json
[{
  "name": "lookup_customer",
  "description": "Resolve a customer name and return current details",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Customer text from the user"}
    },
    "required": ["name"],
    "additionalProperties": false
  }
}]
```

Discovery runs with `cwd=prompts/functions` and a 10-second timeout. Invalid, failing, non-executable, or timed-out providers are not loaded. Function names must be unique; the first discovered definition wins.

## Execution

```bash
echo '{"name":"ACME"}' | ./prompts/functions/provider lookup_customer
```

- First argument: function name.
- stdin: one JSON object of arguments.
- stdout with exit 0: result returned to the LLM or `.cmd`.
- non-zero exit: function failure.
- Execution runs from the application root and has a 120-second timeout.
- `--version` is recommended for diagnostics.

Current implementation inherits provider stderr rather than capturing it into the function result. Emit concise stderr diagnostics, but do not depend on their exact text reaching the LLM.

## Required alignment

Keep these synchronized:

1. Discovery schema and descriptions.
2. Executable implementation.
3. Prompt narrative naming the function or its semantic arguments.
4. Application KS invariants affected by the function.

Descriptions are part of the model-facing API. Put semantic intent in them; keep deterministic resolution and business rules in code or the authoritative application data layer.

## Validation

```bash
chmod +x prompts/functions/provider
./prompts/functions/provider --list-functions | jq .
echo '{"name":"ACME"}' | ./prompts/functions/provider lookup_customer
keprompt functions get --json
```
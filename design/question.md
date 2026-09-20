# Design: `.question` — System One calls from a prompt

Status: designed, not built. Dated 2026-09-20.

Not in `ks/` deliberately — the knowledge store is for current public behaviour and explicitly
excludes speculative features. This moves into `ks/contracts/prompt-language.md` when it ships.

---

## The problem it solves

Epicure translates user intent into toolchain calls with gpt-oss-120b. As the routine count grows
— add-client, modify-client, products, providers, orders, special pricing, costs-to-provider — the
context fills with mutually similar definitions and selection accuracy degrades. The model is being
asked to discriminate among thirty near-identical options while also doing the work.

The fix is to classify first, cheaply, and load only what the classification selected.

## What TypeSafe / Jev is

A "System One" model: it makes fast structured decisions instead of generating text. One request
carries a `state` plus a set of named `questions`; every question is evaluated in parallel and in
isolation against that same state. It never emits text — all three primitives select.

| Primitive | Asks | Returns |
|---|---|---|
| `choice` | pick one of these options | the option + probabilities |
| `score` | rate against a rubric | a score + legend + probabilities |
| `noul` | is this statement true | 0.0–1.0 |

Every answer also carries a calibrated `confidence`.

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>

{ "state": "...", "model": "jev-latest",
  "questions": { "<name>": {"type": "...", "instructions": "...", "criteria": {}} } }

→ { "model": "jev-1.13.0",
    "answers": { "<name>": {type, confidence, probabilities, …} },
    "usage": {"input_tokens": n, "output_tokens": n} }
```

Constraints worth knowing: a `choice` takes at most 255 options, and `state` may be a structured
object rather than a plain string.

**It cannot extract.** There is no primitive that returns a span it located — this is the deliberate
anti-hallucination property. A value is reachable only two ways: enumerate the candidates and let it
pick (their regex-then-`pick()` cookbook), or decompose the value into enumerable fields and
reassemble in code (their date cookbook asks seven `choice` questions and rebuilds the date in
Python). Anything whose domain is neither finite nor decomposable stays out of reach.

## The statement

```
.question <<user-text>> as intent
    object: choice: [Order|Client|Product|Provider|...]
    action: choice: [create|read|update|delete]

.include safe <<intent.action.value>>-<<intent.object.value>>.md
```

Non-message statement, in the same family as `.functions` and `.set` — it does not add anything to
the conversation. State comes from the statement value, questions from the indented body, and the
whole response lands in the named variable.

### Answer shape

Normalised into KePrompt's own shape rather than passed through raw, the same way `AiMessage`
normalises chat providers:

```
<<intent.action.value>>          choice → "create"     score → 2      noul → 0.87
<<intent.action.confidence>>     0.0–1.0
<<intent.action.type>>           "choice" | "score" | "noul"
<<intent.action.probabilities>>  {...}
```

`value` rather than `choice` so that all three primitives read identically and a prompt author does
not need to know which primitive answered.

Must be plain JSON-native nested dicts. A custom object with `__str__`/`__getitem__` would give the
same syntax and survive `substitute()` — but not persistence: both serializers fall back to
`str(value)` when `json.dumps` raises, and nothing in the persistence layer reconstructs types on
load (`AiModel` and `Path` are stringified one-way). It would work within a run and silently
degrade on reply.

### Dispatch

`.include <<intent.action.value>>-<<intent.object.value>>.md` is dispatch without control flow — the
variable part is in the data, not the control path. **This works before conditionals exist**, so the
feature is not blocked on the language change. Confidence gating is the enhancement that waits.

## What already works

| Mechanism | Where |
|---|---|
| Arbitrary-depth variable access `<<a.b.c>>` | `substitute()` splits on `.` and walks, `keprompt_vm.py:360-364` |
| Storing a dict in a variable | `set_variable()` is a plain assignment, `:314` |
| Nested dicts surviving save/restore | `_make_serializable` recurses; `model_info` and `context_usage` already do this |
| `.include` substituting its path | `StmtInclude`, `:1372` |
| Per-request, per-model costing | `calculate_costs()` runs per request; `_record_round_trips` writes `model`/`provider` per row. Mixed models in one chat already work |
| Primary key | `msg_no` is the statement index, so `(chat_id, msg_no, 1)` is unique for a `.question` |

## What has to change

**Parser — the body will not attach.** `parse_prompt` strips every line (`:441`), so indentation
cannot carry meaning. A line not starting with `.` becomes `.text` (`:446`), and a `.text` merges
into the previous statement only when that statement is one of
`['.assistant', '.system', '.text', '.user']` (`:461`). `.question` is not in that list, so the
question definitions would become standalone `.text` statements and `StmtText` would append them to
the conversation — silently sending the question definitions to the LLM as message content. This is
the same failure mode that made the README's obsolete `.llm` lines get sent as literal text.

**Model registry — Jev cannot be priced.** `_load_all_models()` reads exactly one file,
`./prompts/functions/model_prices_and_context_window.json`, and keeps only entries whose
`litellm_provider` matches a registered handler's `litellm_provider` attribute. `keprompt models
update` downloads that file wholesale from LiteLLM and overwrites it; the old per-provider JSONs are
explicitly deprecated. TypeSafe will not be in LiteLLM, so:

- a local overlay merged after `models update` and not clobbered by it, and
- an `AiTypeSafe` handler declaring `litellm_provider = "typesafe"`, or the overlay entry is
  filtered out and `get_model()` raises "not found in configuration".

Overlay entries must use LiteLLM's field names, since that is what the loader reads
(`ModelManager.py:151-162`):

```json
{ "typesafe/jev-latest": {
    "litellm_provider": "typesafe",
    "input_cost_per_token": 0.0000xx,
    "output_cost_per_token": 0.0,
    "max_input_tokens": 0,
    "mode": "systemone" } }
```

Jev prices per input token with output free, so `output_cost_per_token: 0.0` and the existing
`tokens_out * output_cost` arithmetic needs no special case.

This is not TypeSafe-specific — any provider outside LiteLLM's coverage (local Ollama, an internal
endpoint, a private fine-tune) hits the same wall.

**Provider abstraction is a partial fit.** Of `AiProvider`'s five abstract methods,
`extract_token_usage` and `calculate_costs` work as-is — Jev returns `usage.input_tokens` /
`output_tokens`. The other three do not: `to_company_messages` has no message list to convert,
`to_ai_message` has no text reply to build, and `call_llm`'s tool loop is inert. Jev behind `.exec`
fights the abstraction; as its own statement it does not.

**`mode` is a free discriminator.** It is loaded into `AiModel` and carried through, but nothing
branches on it. Tagging Jev `mode: "systemone"` lets `.question` refuse a chat model and `.exec`
refuse a System One model, using a field that already round-trips.

## Open

- Where `.question` gets its model name from — `.prompt` params, a statement argument, or a default.
- Whether `.question` registers as a provider under `ModelManager` or sits outside it.
- API key handling: `TYPESAFE_API_KEY` through `config.py` alongside the others.
- What happens when `<<action>>-<<object>>.md` names a combination with no file. `readfile` wraps
  and re-raises, so an unmapped pair is a hard `VMExecutionError`. Loud rather than silent, but the
  combination space is larger than the set of files anyone will write.

## Related, decided in the same session, not yet written up

**Guard against prompt injection.** Purpose is to guard context; mechanism is "never return bad
text", checked at acquisition inside `FunctionSpace` so that all four context-entry routes are
covered by one invariant. Guarded by default. Model-invoked calls exempt by set
(`.functions wwwget safe=localhost,www.my.domain.com`); author-invoked calls exempt per call
(`.include [safe] filename`) — the asymmetry follows from who writes the arguments. A failed check
returns an explanation in place of the content, following the existing denied-function pattern at
`AiProvider.py:239`. `.image` explicitly out of scope. Enabling refactor: the tool loop calls
`FunctionSpace.functions.functions[name](**args)` directly, bypassing `.call()`; routing it through
`.call()` gives a single chokepoint. Note `.cmd` is not bounded by `.functions` at all, so a
declaration there does not govern author-invoked calls.

**Conditionals.** `.then` / `.else` / `.end-if`, forward jumps only, so `ip` still strictly increases
and termination needs no step counter or fuel. `ip == len(stmts)` becomes the sole halt condition and
`.exit` sets it, removing the separate `break` in `execute()`. Targets resolve at parse time. Loops
deliberately deferred — they would need backward jumps, and nothing currently bounds execution.
Dead code to remove first: `execute_from()` is never called and is not ip-driven, so jumps would
silently not work inside it.

**Also outstanding:** `.functions` does not substitute variables (`:1602` takes `self.value` raw
where `StmtExec` calls `vm.substitute()`), so `.functions <<computed>>` fails today. One-line fix,
and `resolve_function_names` already handles `module.*` globs.

# Migration Notes

What changes for your prompts, your application and your database when you upgrade. Newest first.
Databases migrate automatically the first time a new KePrompt opens them, after taking a backup.

---

## 4.4.0 — `.guard`

**New:** `.guard` keeps injected external text out of the conversation. See
[the guide, section 10](prompt-engineering.md#10-guarding-against-prompt-injection-guard). Prompts
without `.guard` behave as before.

**Changed:**

- **`chat reply --set` values** now enter exactly as on `chat create`: JSON types are kept, `--set`
  wins over `--set-from-json`, and values are **not** substituted. Before, a reply's `--set` values
  went in as `.set` statements — strings, with `<<...>>` expanded. If you relied on `<<name>>` inside
  a reply's `--set` value, pass the final value instead.
- **`.text` right after an `.evaluate`** now adds to the message before it. Before, it started a new
  user message. (`.include` and `.cmd` likewise always add to the last conversation message.)

**Database:** no schema change. Guard runs are `guard` records in `messages_json` and rows in
`cost_tracking`.

## 4.3.0 — prompt names, question-set models, the model that answered

**Changed:**

- **A prompt's name is its file's basename.** A `"name"` field in `.prompt` is ignored with a
  warning; remove it. Chats and cost rows written before 4.3.0 carry the old `"name"`, so reports
  grouped by prompt name may show one prompt under two names across the upgrade.
- **A question set's model belongs to the set.** `ldm_model` on an `.evaluate` line is now kept at
  `?.<Set>._model` for later evaluations of that set; before, it applied to that one call. It never
  touches `$.ldm_model` or other sets.
- **Renamed memory paths:**

  | Before | Now |
  |---|---|
  | `?.<Set>._ldm_model` (the set's model) | `?.<Set>._model` |
  | `?.<Set>._model` (the model that answered) | `?.<Set>._provider_selected_model` |

  Update any prompt that reads them.

**New:** `$._provider_selected_model` after every `.exec` — the model version that actually answered.

**Fixed:** Gemini models could not be called at all (every request got a 404).

**Database:** `cost_tracking` gains `provider_selected_model` (null on older rows). Stored chats are
rewritten to the new names: the LDM record's `model_served` becomes `provider_selected_model`, and the
question-set keys are renamed as in the table above.

## 4.2.0 — `.question` and `.evaluate`; `$.llm_model`

**New:** `.question` and `.evaluate` — classify text with an LDM (decision model) and branch on the
answer. See [the guide, section 9](prompt-engineering.md#9-classifying-with-an-ldm-question-and-evaluate).
TypeSafe needs `TYPESAFE_API_KEY`, and its models come from `prompts/functions/model_overlay.json`
(copied by `keprompt init`; copy it from the package's `defaults/functions/` into an existing
workspace).

**Changed:** the model setting is **`$.llm_model`**. `model` still works everywhere — `.prompt`
params, `.set`, `--set`, `--set-from-json`, `<<model>>` — but writes a deprecation warning. Replace:

```
.prompt "version":"1.0", "params":{"model":"openai/gpt-4o"}          # before
.prompt "version":"1.0", "params":{"$.llm_model":"openai/gpt-4o"}    # now
```

On the command line: `--set '$.llm_model=openai/gpt-4o'` (quote it: `$` is special to the shell).

## 4.0.0 — multi-line quotes

**New:** `<<<ID … >>>ID` takes a statement's text verbatim. See
[the guide, section 5](prompt-engineering.md#5-multi-line-quotes).

**Changed:** `<<<` followed by an identifier on a statement line now opens a quote. A prompt that
used `<<<word` as literal text must change it (for example by moving the text into a quote with a
different identifier).

## 3.0.0 — `llm_options`

**Changed:** model request options live only in `llm_options`. `temperature`, `max_tokens`, `top_p`
and `top_k` as top-level variables stop execution.

```
.prompt "version":"1.0", "params":{"temperature":0.2}                       # before — now an error
.prompt "version":"1.0", "params":{"llm_options":{"temperature":0.2}}       # now
```

## 2.12.0 — `.functions`

**Changed:** the model has **no access to any functions by default**. If a prompt relies on tool
calling — built-ins like `readfile`, `writefile`, `wwwget`, `execcmd`, or custom functions — declare
them with `.functions` before the `.exec` that needs them. Prompts that don't use tool calling are
unaffected.

**Why:** without `.functions`, every `.exec` had implicit access to all loaded functions, so a
delegated sub-agent or a carelessly written prompt could call `execcmd` or `writefile` without
restriction. `.functions` enforces least privilege.

```
.prompt "version":"1.0.0"
.functions readfile, wwwget, writefile
.system You are a research assistant.
.user Look up <<topic>> and save a summary.
.exec
```

| Scenario | `.functions` line |
|---|---|
| Read-only file access | `.functions readfile` |
| Web research | `.functions wwwget` |
| File read + write | `.functions readfile, writefile` |
| Shell commands | `.functions execcmd` |
| Custom function | `.functions my_custom_func` |
| No tool calling needed | no `.functions` line |

Find prompts that use `.exec` but have no `.functions`:

```bash
grep -rL '\.functions' prompts/*.prompt | xargs grep -l '\.exec'
```

# Migration Notes

What changes for your prompts, your application and your database when you upgrade. Newest first.
Databases migrate automatically the first time a new KePrompt opens them, after taking a backup.

---

## 5.0 — Ready for Prod: `.sub`, local models, the chat log

**New:**

- **`.sub [guard=#._name] path`** runs a file of keprompt lines on this prompt, then continues with
  the next line. The path is substituted, so an `.evaluate` answer can pick the file. A bare name opens
  under `prompts/`; a path with a directory, or an absolute path, opens as written. The file does not
  start with `.prompt` and gets no automatic `.exec`. It shares the caller's variables, messages and
  function grant, so a `.functions` line in it is the grant the caller's next `.exec` sees. See
  [the guide, section 8](prompt-engineering.md#8-files-and-images). Its text is judged on the new **`#._sub`** guard
  channel before it runs.
- **`<<VM.output_flag>>`** is `--json` or `--pretty`, matching how this keprompt was run. Pass it to a
  child keprompt started through `.cmd`; otherwise the child sees a pipe and answers in JSON.
- **Local OpenAI-compatible servers** (provider `ollama`). Declare each model in
  `prompts/functions/model_overlay.json` with `"litellm_provider": "ollama"` and `"source"` set to the
  server's base URL including `/v1`; requests go to `<source>/chat/completions`.
- **`keprompt-chats`**, a second command installed with the package, opens `prompts/chats.db` in a
  browser on port 8765 (`--port` chooses another). Each chat expands to its statements, calls and
  results.

**Changed:**

- **`.exit` inside a `.sub` file stops the whole prompt**, the caller included.
- **`.print` keeps plain line breaks.** Before, Rich Markdown joined lines separated by a single
  newline into one paragraph. Tables, headings, lists, quotes and code fences render as before.
- **An external function's stderr** now comes back as the error text when the function fails. Before,
  it went to the terminal and the error was a Python `'NoneType' object has no attribute 'strip'`.
- **`ollama/...` rows in LiteLLM's model file are ignored.** They name no server; only models declared
  in the overlay are loaded for this provider.

**Database:** no schema change.

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

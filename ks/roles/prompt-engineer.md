# Role: Application Prompt Engineer

Goal: create or change an application's prompts and executable function toolchains.

## Required reading

1. The application's own KS: business intent, invariants, data ownership, and evaluation goals. If it does not exist yet, start it from [`../examples/application-ks.md`](../examples/application-ks.md).
2. [`../contracts/prompt-language.md`](../contracts/prompt-language.md)
3. [`../contracts/external-functions.md`](../contracts/external-functions.md)
4. [`../contracts/application-shell.md`](../contracts/application-shell.md) when running tests.
5. [`../examples/`](../examples/README.md): worked prompts for `.question` dispatch and `.guard`.

## Responsibility split

- LLM: language understanding, semantic interpretation, and presentation.
- Functions: deterministic lookup, validation, side effects, and access to application systems.
- Application/database: business rules and authoritative state.

Do not teach the model data or rules that an authoritative function or database should resolve. Function names, descriptions, schemas, implementations, and prompt narrative must remain aligned.

## Workflow

1. Read the application KS and current prompt/function files.
2. State the intended behavior and invariants before editing.
3. Change the smallest appropriate layer.
4. Validate function discovery and standalone execution.
5. Run the prompt through the same shell command used by the application.
6. Inspect the JSON answer and saved chat, including tool calls and results. `keprompt-chats` walks that chat's statements and the calls inside `.exec`.
7. Test normal, ambiguous, and failure cases.
8. For production-derived comparison, follow [`production-optimizer.md`](production-optimizer.md).

Use `.functions` with least privilege. No `.functions` statement means the model receives no tools.

## Classifying with an LDM

Use `.question` + `.evaluate` when a cheap, selection-only decision should shape the prompt — e.g.
which instructions or tools to load — rather than asking the LLM to choose among many similar ones.
`.sub` runs the lines for that choice on this prompt, so the fragment can set the `.functions` grant.
`.include` still only pastes text.
Write the options from the application KS's domain; an LDM can only pick one of them. Gate on
`confidence` where a wrong pick is costly. Example: [`../examples/intent-dispatch.prompt`](../examples/intent-dispatch.prompt).

After the classification, both of these are valid. The engineer picks by whether the job needs a reply.

- `.sub` when the next message has to continue this work. The work stays in this chat, so the reply lands in the context that did it. The prompt is one assembly: each result is a fragment, the classifier arms the pieces, and a test runs the assembly.
- `.cmd execcmd(...)` when the job is one shot. Each result is a whole prompt, built and tested on its own, with no include hierarchy. At runtime the classifier only chooses which prompt to run. A reply to the classifier chat does not continue that prompt.

Continuing the first chat with the second chat's answer is an AgentDirector. It is not this choice. See [`../../design/agentic-director.md`](../../design/agentic-director.md).

## Guarding external text

1. List every channel external text enters by: `--set` / `--set-from-json` (`#._cmdargs`), reply
   messages (`#._userinput`), `.include` (`#._include`), `.sub` (`#._sub`), and each function in `.functions` or `.cmd`
   (`#.<function>`). A channel with no guard passes; model output needs none.
2. Write each guard's criteria from what this prompt legitimately does, per channel. A generic
   "is this an instruction to an AI?" rejects legitimate imperative traffic.
3. Choose the `fail:` threshold as policy: the more irreversible the actions the prompt can take,
   the lower it goes. Record the choice in the application KS.
4. Test with real traffic, including operator traffic: every guard execution is a `guard` message in
   `prompts/chats.db` (see [`../contracts/production-database.md`](../contracts/production-database.md)),
   so passes and rejections can be collected with SQL and replayed as a test set.

Example: [`../examples/guarded-assistant.prompt`](../examples/guarded-assistant.prompt).

## Epicure classify (in progress, 2026-10-29)

One LDM call picks the object and the action. `.sub` then runs only that cell's fragment, so the LLM sees that schema and that function grant. `.include` pastes the file as text and does not run it.

Run from `test/classifier/`. Prompt: `test/classifier/prompt/classifier.prompt`. Fragment name: `epicure-classify-<object>-<action>.lines`. A bare `.sub` name opens under `prompts/`, so that fragment is `../../test/classifier/prompts/classify-order-read.lines`. Only that cell exists. It grants `epicure_tools.select` and puts a `.system` up containing the select instruction and the `orders` table alone. The caller then `.user`s the question and `.exec`s (`$.llm_model` `cerebras/gpt-oss-120b`). The question set `Route` uses `typesafe/jev-latest`.

| Axis | Options |
|---|---|
| object | `client`, `provider`, `product`, `order`, `order_item` |
| action | `create`, `read`, `update`, `delete`, `copy` |

Chats in `test/prompts/chats.db`:

- `688212ae` — "list all orders with total over 1,000 mxn" → `order` / `read`, confidence 1.0. `select` ran `SELECT * FROM orders WHERE total > 1000`. The tool result is a valid 23-column markdown table. The assistant reply is not: its separator row has 24 cells and the header and body have 23. `markdown-it` (Rich `Markdown`, tables enabled) then emits no `table_open`, so `.print` and the reply render as a paragraph of pipes. `.print` and the assistant text both go through `rich.markdown.Markdown`.
- The week-filtered question works: "list all orders with total over 1,000 mxn from week 2026-10-29".

Still on disk, and still what `test/test_classify_request.py` expects: `test/prompts/epicure.prompt` classifies `kind` (`maintenance`, `change_week`, `new_order`, `change_order`, `query`) and `.sub`s `epicure_<kind>.lines`, which a bare name opens as `test/prompts/epicure_<kind>.lines`. The `.print` in `classifier.prompt` is still the two-line probabilities dump. The other object–action fragments are not written.


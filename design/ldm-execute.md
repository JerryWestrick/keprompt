# Design: an LDM call is an execute

Status: architecture agreed 2026-09-23; implemented in 4.2.0 (2026-09-24) and 4.3.0 (2026-09-27) —
see the "Implemented" sections at the end.

Settled with Jerry after the first build of `.evaluate` put LDM calls on a parallel path (their own
table, save, query and view code), which left LDM rows orphaned when a chat was deleted. The error
was treating LDM calls differently from LLM calls. This document is what the design now works
within. Where it conflicts with `design/question.md` (notably "Executing it: No abstraction" and
"Provider abstraction is a partial fit"), this document wins.

---

## Architectural points

1. An LDM call (`.evaluate`) is just another type of execute (`.exec`). In the database and in
   code it is the same; only the methods that build the API content differ.
2. The term is LDM, everywhere.
3. One concept, one implementation. A parallel path counts as a defect.
4. Confirm the architecture parts a change touches before looking at how to implement it.
5. We do not supply web chats and other applications that use this tool.
6. The `.prompt` language is an assembler, and the model is the virtual CPU. An execute is one
   cycle, whichever model runs it.
7. `chats.db` is a public integration surface. But keprompt helps with listing chats and the other
   functions the programmer needs.
8. Every LDM call's parameters and results are stored so they can be queried with LLM calls, for
   tests, studies and stats.
9. `.question` is in the same family as `.prompt` and `.functions`: it sets global variables for
   later use. The variables it creates are just more complex.
10. `.evaluate` is an execute, like `.exec`: the same model resolution, provider path, per-call
    record, VM totals, logging and chat lifecycle. What differs is the content. `.evaluate` takes
    the pre-prepared dictionary from `.question` and adds the state, which is the user's input. Its
    answers land in the `?.` question namespace instead of the message list.
11. Memory and the model value:
    - Command-line args (`--set`, `--set-from-json`) feed memory before the prompt runs.
    - `.prompt` params are defaults, applied only where the command line hasn't set a value.
    - Special values live in memory under reserved names: `model`, `llm_options`,
      `Prefix`/`Postfix`, `Debug`/`Verbose`, and `_prompt`, reached through `$` and `?`. `VM.*` is
      read-only.
    - `.question` sets up its question set in memory under `?.<Set>`.
    - `.set` can modify all memory.
    - The model value is read from memory, and `.exec` and `.evaluate` can each override it on
      their own line.
12. There is no replay. We supply the database. Every call, LLM or LDM, is stored there, and the
    shape of the data is designed so it can be used for stats, checking errors, building
    information, making repeatable tests and so on.
13. **One model registry.** It is the only place that says what a model is. Every model, LLM or
    LDM, is described and costed there, wherever its definition comes from. The execute path acts
    on what the registry says about the model.
14. **One provider path.** Every model is reached through a provider. Providers differ only in how
    they build the request and read the response.

## Decisions, 2026-09-24

- **An LDM call is stored as a special message in the message list.** `.exec` treats it as a
  no-op when building LLM content; `.evaluate` uses it as its parameters.
- **The special message holds both the parameters (question set and state) and the answers.**
- **Answers also land in the `?.` question namespace** (decided long before this document), so a
  prompt reads them as `<<?.Intent.action.value>>`. The special message is the record; the
  namespace is what the prompt reads.
- **The model value is not shared.** Two memory values, `llm_model` (for `.exec`) and `ldm_model`
  (for `.evaluate`), with identical command-line handling. Revises point 11's single model value.
- **`model` is renamed `llm_model`.** `model` is still accepted but deprecated: every use of
  `model` is treated as `llm_model` and writes a warning. They are one value, so there is no
  precedence between them.
- **No default `ldm_model`.** A missing `ldm_model` is an error, the same as `.exec` with no
  `llm_model`.
- **How `.evaluate` finds its model** (settled 2026-09-24, replacing the earlier "`.question`
  takes no model"), first match wins:
  1. the model on the `.evaluate` line
  2. otherwise the model on the `.question` line
  3. otherwise `$.ldm_model`, set by `.set` or a command-line arg
- **A question set's model is scoped to the set** (settled 2026-09-27, replacing the rule above).
  It is the `.exec` pattern with a narrower scope: `.exec`'s scope is the prompt, a question set's
  scope is the set. `.question Intent <model>` and `.evaluate ?.Intent {"ldm_model":"..."}` both
  write the model into `Intent`'s own model slot, where it stays for later `.evaluate ?.Intent`
  calls. Neither touches `$.ldm_model` or any other question set. `.evaluate ?.Intent` uses
  `Intent`'s slot, otherwise `$.ldm_model`. The slot is `?.Intent._model`: `?` is the LDM,
  `Intent` says which one, `_model` is its model — only LDMs live under `?`, so `_ldm_` would be
  redundant (settled 2026-09-27).
- **The model that answered** (settled 2026-09-27) is filled with the model asked for, then
  overwritten if the provider identifies a different one. It lives at
  `?.Intent._provider_selected_model`. If model resolution
  fails before the call, the `.evaluate` is illegal and the prompt stops.
- **One name everywhere** (settled 2026-09-27): `provider_selected_model`. The `ldm` message's
  `model_served` field is renamed to it, so the record and `?.Intent._provider_selected_model` agree.
- **`.exec` captures `provider_selected_model` too** (settled 2026-09-27, by point 10): filled with
  the model asked for, overwritten if the provider identifies a different one. In memory it is
  `_provider_selected_model` in both scopes: `$._provider_selected_model` for `.exec`,
  `?.Intent._provider_selected_model` for `.evaluate ?.Intent`. In both it is a temporary output
  value, overwritten by each call. In the record it is also stored in `cost_tracking`, on every
  row, LLM or LDM (settled 2026-09-27). An `ldm` message keeps it as well.

## The machine: one VM with an LDM coprocessor (2026-09-24)

One VM, not two. The LDM is a coprocessor on the same machine: one instruction stream, one `ip`,
one memory, one chat, one message list, one record and one set of totals. The LLM and the LDM are
the execution units; each has its own section, like registers, holding only what is specific to it.

- **`.question` saves coprocessor register values** — the question-set definitions, into memory
  (point 9: it sets global variables for later use).
- **`.evaluate` loads the coprocessor values and executes them.** The answers land in the `?.`
  question namespace, where the program reads them.
- **`question` is not under `VM`.** `?.` stays in memory, `?` → `_prompt.question`: the question
  sets and their answers are program data, not machine state.
- **The LLM model is `$.llm_model`**, not under `VM`. (The LDM fallback is `$.ldm_model`.)
- Open: where the options live — Jerry said `?.ldm_options`; not yet confirmed against `llm_options`.
  Implemented without it: `llm_options` is unchanged and LDM calls take no options.

## Implemented, 2026-09-24

- `.evaluate` is a subclass of `.exec`'s statement. The shared execute is one method; the two differ
  only in hooks: which model, which mode is refused, what the content is, where the result goes.
- TypeSafe is `AiTypeSafe(AiProvider)`, registered for `typesafe`. `keprompt/typesafe.py` is gone.
  The shared `call_llm` asks the provider which messages it builds from (`select_messages`) and
  which options it takes (`request_options`); an LLM is sent `llm_messages()`, the LDM its message.
- The `ldm_calls` table is gone. The 4.1.0 and 4.2.0 migrations make no schema change.
- Choices made in implementing, for Jerry to confirm:
  - (Settled by Jerry, 2026-09-24) `.evaluate` takes the same JSON params as `.exec`:
    `.evaluate ?.Set {"ldm_model":"..."} <<<STATE`, or with an inline state after the object.
    One shared parser serves both statements.
  - (Superseded 2026-09-27 by "A question set's model is scoped to the set".) The `.question`
    line's model was kept at `?.Intent._ldm_model`, and the `.evaluate` line model was used for that
    call only. `?.Intent._model` stays "the model that actually answered", as the namespace section
    defines it.
  - In `.prompt` params and `--set`, the new spelling is the path itself: `"$.llm_model"`.

## Implemented, 2026-09-27 (4.3.0)

- The set's model is `?.Intent._model` (`SET_MODEL_KEY`); the `.evaluate` line writes it, as the
  `.question` line does.
- One provider hook, `AiProvider.provider_selected_model(response)`, reads the model that answered
  from every response: `model`, or `modelVersion` for Gemini; the model asked for if absent. It feeds
  the round-trip record (so `cost_tracking.provider_selected_model`) and the LDM part.
- The shared execute writes the last round trip's value to `<scope>._provider_selected_model`; the
  one hook that differs is `output_scope`: `$` for `.exec`, the set for `.evaluate`.
- Migration 4.2.0 → 4.3.0 adds the column and renames stored keys: the LDM part's `model_served`,
  and in stored memory a set's `_model` → `_provider_selected_model`, then `_ldm_model` → `_model`.

# <Application> Knowledge Store

The application's own KS: what KePrompt's KS cannot know. Keep it short and current; the prompt
engineer reads it first (see `roles/prompt-engineer.md`).

## Purpose

What the application does, for whom, and through which channels (web, WhatsApp, CLI, ...).

## Domain

The entities and the actions on them, in the users' own words — e.g. Client, Product, Order, Week;
create, read, update, delete. This list is also the scope that `.question` choices and `.guard`
criteria are written from.

## Invariants

Rules that must always hold, and who enforces each: the application or database (authoritative),
a function (deterministic), or the LLM (interpretation only).

## Division of responsibility

- LLM: understanding and presentation.
- Functions (`prompts/functions/`): lookup, validation, side effects — list them.
- Application/database: business rules and authoritative state.

## External text and guards

Every channel external text arrives by, and its guard: `#._cmdargs`, `#._userinput`, `#._include`,
`#.<function>`. What legitimate traffic on each channel looks like — including operator traffic,
not only customers — and the fail threshold chosen, with why.

## Evaluation

The test sets and how they are built from `prompts/chats.db` (`ldm` and `guard` messages,
`cost_tracking`), the expected outcomes, and the current results.

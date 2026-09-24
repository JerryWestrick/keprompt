# Prompt Language Contract

`.prompt` files are line-based programs. A statement starts with `.`; following non-statement lines continue its value, or a multi-line quote takes it verbatim. Variables use `<<name>>` by default; dictionaries use `<<name.key>>`.

## Statements

| Statement | Effect |
|---|---|
| `.prompt "name":"N", "version":"V", "params":{...}` | Required first statement; metadata and defaults |
| `.functions f1, module.*, module.f2` | Tools allowed during `.exec`; last declaration wins |
| `.system text` | Add system message |
| `.user text` | Add user message |
| `.assistant text` | Add assistant message without an API call; useful for examples |
| `.text text` | Append text to the current text-capable message |
| `.exec` / `.exec model` / `.exec {"llm_model":"..."}` | Call the LLM; a model on the line updates `$.llm_model` for later calls |
| `.question Name [model] <<<ID ... >>>ID` | Declare a named question set, optionally with the LDM that answers it |
| `.evaluate ?.Name [{"ldm_model":"..."}] state` / `... <<<ID` | Call an LDM on a declared set and a state; answers land in the set |
| `.set name value` | Substitute, then store a string variable |
| `.cmd function(args)` | Execute function; append result to current message and set `last_response` |
| `.cmd function(args) as name` | Execute function; store result without appending it |
| `.include path` | Append file content to current message |
| `.image path` | Add image content |
| `.tool_call ...` / `.tool_result ...` | Manually represent tool examples or replay context |
| `.print text` | Application output; captured in JSON envelope `stdout` |
| `.debug ...` | Display VM state |
| `.clear [...]` | Delete matching files; destructive |
| `.exit` | Stop execution |
| `.# text` | Comment |

## Multi-line quotes

Any statement may take its value from a multi-line quote. `<<<ID` on the statement line opens one; a
line containing exactly `>>>ID` closes it. `ID` is yours to choose — any run of non-space characters
— so content that would otherwise collide with the terminator is handled by picking a different one.

Standard heredoc semantics: the opener does not have to end the line, and anything after it stays
part of the statement, while the terminator must stand alone.

```
.system <<<SYS
You are a helpful assistant.

    Indentation and blank lines are preserved.
.exit here is content, not a statement.
>>>SYS
```

Inside the quote the line is content, not syntax: no whitespace stripping, no blank-line skipping,
and no `.keyword` dispatch. For statements whose operand simply is the text, the quoted body
replaces the marker in the value — so `.set name <<<ID` keeps the name ahead of the quoted value,
`.user Hello <<<ID` keeps the leading text, and `.system <<<ID trailing` keeps the trailing text.
A statement that parses its own line instead keeps the body separate, so pages of quoted text never
land in the part it has to read.

- The delimiters are fixed literals resolved at parse time. They are deliberately **not** bound to
  `Prefix` / `Postfix`, which are runtime variables — changing those moves `<<name>>` and leaves
  `<<<ID>>>` where it is.
- Because it is resolved at parse time, quoted text is never re-parsed. Substituted content
  containing `>>>ID` cannot close a quote.
- Variables inside the quote are substituted normally when the statement executes.
- An unclosed quote is a parse error naming the opening line.
- `<<<'ID'` with a quoted identifier is reserved for a future non-interpolating form and is
  currently rejected.

## LDM questions

`.question` saves a named question set in memory, like `.prompt` and `.functions` set values for
later use. `.evaluate` is an execute, like `.exec`: it adds the state, calls the LDM, and the call is
recorded, billed and totalled exactly as an LLM call is. What differs is the content — an LDM selects
from the set's options rather than generating text.

```
.question Intent <<<END
    object: choice
        instructions: Which entity is the user acting on?
        Order: an order / pedido / remision, or the items on one
        Client: a customer of the business
>>>END

.evaluate ?.Intent <<<STATE
#15 TERCER
1 domo de violas
>>>STATE

.include <<?.Intent.object.value>>-<<?.Intent.action.value>>.md
```

The body is a multi-line quote because criteria are two levels deep and continuation lines are
stripped. A question line is `name: choice|score|noul`; indented under it, `instructions:` is
reserved and every other `key: text` is an option and its criterion. A deeper line that is not
`key: text` continues the previous one, so criteria can run to paragraphs.

A `choice` takes up to 255 options. A `score` takes an ordered rubric — levels are positional, so
the keys are labels for reading and the answer is the position as 0.0–1.0 plus a `legend`. A `noul`
takes no options at all: it asks whether its instructions are true of the state.

Answers land in the set, so there is no destination argument. Reads use `value`, not the primitive's
own name, so all three read alike:

| Path | Holds |
|---|---|
| `?.Set.question.value` | `choice` → the option, `score` → 0.0–1.0 position in the rubric, `noul` → 0.0–1.0 |
| `?.Set.question.type` | which primitive answered |
| `?.Set.question.confidence` | `choice`/`score` only — a `noul` value *is* its own answer, so this is absent |
| `?.Set.question.probabilities` | `choice`/`score` only |
| `?.Set.question._definition` | the question as asked: type, instructions, criteria |
| `?.Set._model` / `?.Set._usage` | the model that actually answered, and its tokens |
| `?.Set._ldm_model` | the model named on the `.question` line, if any |

Re-evaluating a set replaces its answers.

`.evaluate` uses the first model it finds:

1. `ldm_model` in the `.evaluate` line's params, the same JSON params `.exec` takes:
   `.evaluate ?.Intent {"ldm_model":"typesafe/jev-latest"} <<<STATE`. The object's closing brace
   ends it, so an inline state can follow. It applies to that call only.
2. otherwise the model on the `.question` line
3. otherwise `$.ldm_model`, from `.set`, `.prompt` params or the command line

No model anywhere is an error. A chat model is refused, as `.exec` refuses an LDM.

Each call is stored as an `ldm` message in the chat's message list, holding the set, the questions,
the state, the model asked for, the answers, the model that answered and its usage. An LLM is never
sent `ldm` messages; two messages an `ldm` message separated reach the LLM merged, as if it were not
there.

## Reserved names

A leading `_` at the top level of the variable dictionary belongs to KePrompt. `_prompt` is the
machinery, with `_prompt.question` holding the LDM subsystem. Inside a question set, `_` is
reserved too, so a question may not be named `_definition`.

Two fixed-literal shorthands expand in any path — they are not configurable, and not affected by
`Prefix`/`Postfix`:

| Sigil | Expands to |
|---|---|
| `$` | `_prompt` |
| `?` | `_prompt.question` |

Each execution unit's model lives under `_prompt`: `$.llm_model` for `.exec` and `$.ldm_model` for
`.evaluate`. They are separate, so a prompt using both never re-sets one for the other.

`model` is the deprecated spelling of `$.llm_model`. Every use — `.prompt` params, `.set`, `--set`,
`--set-from-json`, `<<model>>`, a saved chat — is treated as `$.llm_model` and writes a warning.

`.set` writes any memory, including dotted and `$.`/`?.` paths: `.set $.ldm_model typesafe/jev-latest`.
`.prompt` params and `--set` take the same paths: `"params":{"$.llm_model":"openai/gpt-4o"}`,
`--set '$.llm_model=openai/gpt-4o'`.

`llm_options`, `last_response`, `Prefix` and `Postfix` have not moved under `_prompt`.

## Execution rules

- Statements execute sequentially and build universal messages.
- `.exec` sends all accumulated messages, not only the latest one.
- Consecutive same-role messages may merge.
- `last_response` is updated by model and function execution.
- Variables persist for the VM/chat. CLI `--set-from-json FILE` and `--set` override prompt defaults (`--set` wins on matching keys).
- Substitution delimiters are the VM variables `Prefix` (default `<<`) and `Postfix` (default `>>`). `.set Prefix` / `.set Postfix`, or the same names via CLI `--set` / `--set-from-json`, change the markers for later substitution.
- Without `.functions`, the model receives no tools. `.cmd` is direct program execution and is not model tool access.
- If `.exit` is absent, the VM adds completion statements: after `.exec`, print and exit; otherwise execute, print, and exit.
- `llm_options` is always present as a dict. It is the only place for model request options, including `temperature`, `max_tokens`, `top_p`, and `top_k`. Set it on `.prompt` `params`. Every `.exec` merges it onto the request. Those four names as top-level variables stop execution: move them into `llm_options`.

## Read-only VM values

Common values include `<<VM.chat_id>>`, `<<VM.model_name>>`, `<<VM.provider>>`, `<<VM.prompt_name>>`, `<<VM.prompt_version>>`, `<<VM.total_cost>>`, `<<VM.toks_in>>`, `<<VM.toks_out>>`, and `<<VM.interaction_no>>`.

Model names are registry keys, normally `provider/model-name`. Use `keprompt models get --json` to inspect current choices; do not rely on hard-coded model lists in documentation.
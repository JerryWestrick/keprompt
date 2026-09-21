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
| `.exec` / `.exec model` / `.exec {"model":"..."}` | Call the model; model overrides update variables for later calls |
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

Any statement may take its value from a multi-line quote. `<<<ID` as the last thing on the
statement line opens one; a line containing exactly `>>>ID` closes it. `ID` is yours to choose, so
content that would otherwise collide with the terminator is handled by picking a different one.

```
.system <<<SYS
You are a helpful assistant.

    Indentation and blank lines are preserved.
.exit here is content, not a statement.
>>>SYS
```

Inside the quote the line is content, not syntax: no whitespace stripping, no blank-line skipping,
and no `.keyword` dispatch. The quoted text replaces the marker in the statement's value, so
`.set name <<<ID` keeps the name ahead of the quoted value and `.user Hello <<<ID` keeps the
leading text.

- The delimiters are fixed literals resolved at parse time. They are deliberately **not** bound to
  `Prefix` / `Postfix`, which are runtime variables — changing those moves `<<name>>` and leaves
  `<<<ID>>>` where it is.
- Because it is resolved at parse time, quoted text is never re-parsed. Substituted content
  containing `>>>ID` cannot close a quote.
- Variables inside the quote are substituted normally when the statement executes.
- An unclosed quote is a parse error naming the opening line.
- `<<<'ID'` with a quoted identifier is reserved for a future non-interpolating form and is
  currently rejected.

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
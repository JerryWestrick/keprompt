# Migration: Adding `.functions` to Your Prompts

**Applies to:** KePrompt v2.12.0+

## What Changed

As of v2.12.0, the model has **no access to any functions by default**. If your prompt relies on tool calling (built-in functions like `readfile`, `writefile`, `wwwget`, `execcmd`, or custom functions), you must explicitly declare them with a `.functions` statement.

Prompts that don't use tool calling are unaffected.

## Why

Without `.functions`, every `.exec` had implicit access to all loaded functions. This meant a delegated sub-agent or a prompt you didn't write carefully could call `execcmd` or `writefile` without restriction. The `.functions` statement enforces least-privilege — the model can only use what you explicitly allow.

## How to Migrate

Add a `.functions` line listing the functions the model needs. Place it before the first `.exec` that should have access.

### Before
```
.prompt "name":"Researcher", "version":"1.0.0"
.system You are a research assistant.
.user Look up <<topic>> and save a summary.
.exec
```

### After
```
.prompt "name":"Researcher", "version":"1.0.0"
.functions readfile, wwwget, writefile
.system You are a research assistant.
.user Look up <<topic>> and save a summary.
.exec
```

## Quick Reference

| Scenario | `.functions` line |
|---|---|
| Read-only file access | `.functions readfile` |
| Web research | `.functions wwwget` |
| File read + write | `.functions readfile, writefile` |
| Shell commands | `.functions execcmd` |
| Full access (use sparingly) | `.functions readfile, writefile, wwwget, execcmd` |
| Custom function | `.functions my_custom_func` |
| No tool calling needed | No `.functions` line needed |

## Finding Prompts That Need Updating

Any `.prompt` file that uses `.exec` and expects the model to call functions needs a `.functions` statement. Look for prompts where the system/user message references tools or where you previously relied on implicit function access.

```bash
# Find prompts that have .exec but no .functions
grep -rL '\.functions' prompts/*.prompt | xargs grep -l '\.exec'
```

# KePrompt Knowledge Store

This is the LLM interface to KePrompt. Read only the path required for your role.

## Choose a role

| Task | Start here | Then read |
|---|---|---|
| Modify KePrompt itself | [`roles/keprompt-maintainer.md`](roles/keprompt-maintainer.md) | Relevant `internals/` and affected `contracts/` |
| Build KePrompt into an application | [`roles/application-builder.md`](roles/application-builder.md) | `contracts/application-shell.md`, then prompt/function contracts |
| Create or change an application's prompts/functions | [`roles/prompt-engineer.md`](roles/prompt-engineer.md) | The application's KS, then prompt/function contracts |
| Improve an application from production evidence or test newer models | [`roles/production-optimizer.md`](roles/production-optimizer.md) | The application's KS and `contracts/production-database.md` |

Operational diagnosis belongs to the role owning the failing boundary: application shell, prompt/function behavior, or KePrompt implementation.

## Document classes

- `contracts/`: exact public behavior. One authoritative document per contract.
- `roles/`: task workflow; links to contracts instead of repeating them.
- `internals/`: implementation architecture for changing KePrompt.

Application-specific business intent and invariants belong in that application's own KS.

## Authority and maintenance

- The KS is authoritative on design intent and public contracts.
- Source code is authoritative on current mechanics. If code and KS disagree, surface and resolve the mismatch.
- Update the affected contract when behavior changes.
- Keep this store short, current, and KePrompt-specific. Do not add generic LLM tutorials or speculative features.
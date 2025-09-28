# KePrompt Knowledge Store

This directory contains structured context information designed to help AI assistants quickly understand and work with the KePrompt project.

## Purpose

The `ks/` (knowledge store) directory provides concise, AI-optimized documentation that enables rapid context restoration for development work. Unlike human documentation, these files focus on architectural decisions, design patterns, and key relationships that are essential for understanding the codebase.

## Files Overview

### Core Understanding
- **[project-overview.md](project-overview.md)** - What KePrompt is and its core value proposition
- **[architecture.md](architecture.md)** - System components and their relationships
- **[core-concepts.md](core-concepts.md)** - Backend-as-prompts philosophy and CLI-first design

### Design Context
- **[key-decisions.md](key-decisions.md)** - Important architectural choices and their rationale
- **[development-patterns.md](development-patterns.md)** - Common integration patterns and workflows
- **[directory-architecture.md](directory-architecture.md)** - Project directory structure analysis and recommendations

### Feature Documentation
- **[conversation-management.md](conversation-management.md)** - Professional conversation viewing system (v1.4.0)

## Quick Context Restoration

For AI assistants working on KePrompt:

1. **Start with project-overview.md** to understand what KePrompt does
2. **Read architecture.md** to understand how components interact
3. **Review core-concepts.md** for the backend-as-prompts philosophy
4. **Check key-decisions.md** for context on why things are designed this way
5. **Reference development-patterns.md** for common implementation patterns

## Key Insights for AI Context

- **KePrompt is a CLI-first prompt execution engine** that abstracts AI providers
- **Backend-as-prompts** means AI logic lives in `.prompt` files, separate from application code
- **Universal integration** via subprocess calls makes it language-agnostic
- **Production focus** with built-in cost tracking, logging, and conversation management
- **File-based configuration** enables version control and portability

## Maintenance

This knowledge store should be updated when:
- Major architectural changes are made
- New core concepts are introduced
- Important design decisions are made or changed
- Common development patterns evolve

The goal is to maintain a concise, accurate representation of the project's essential context for AI development assistance.

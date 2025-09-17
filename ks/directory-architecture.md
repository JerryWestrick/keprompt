# KePrompt Directory Architecture Analysis

## Overview
This document analyzes the current directory structure of KePrompt projects and provides architectural recommendations for optimal organization of different types of data and artifacts.

## Current Directory Structure

```
/project/
├── prompts/              # Static prompt assets + execution artifacts
│   ├── functions/        # Custom function definitions and executables
│   ├── models/          # AI model configuration files
│   ├── logs/            # General execution logs
│   ├── logs-xxx/        # Specific prompt execution logs
│   ├── costs.db         # Cost tracking database
│   └── *.prompt         # Prompt files
├── conversations/        # Dynamic conversation data
│   └── *.conversation   # JSON conversation files
└── [other project files]
```

## Architectural Analysis

### ✅ Well-Placed Components

#### `conversations/` at Project Root
**Decision: APPROVED - Keep at project root**

**Rationale:**
- **Clear separation of concerns**: Static prompt assets vs. dynamic conversation data
- **Different access patterns**: Prompts are browsed/selected, conversations are managed/continued
- **Different lifecycle**: Prompts are version-controlled, conversations are session-specific
- **Security considerations**: Prompts can be shared, conversations are often private
- **Backup strategies**: Different retention policies make sense

**Benefits:**
- Clear mental model: `prompts/` = "What can I run?", `conversations/` = "What have I been doing?"
- Follows industry patterns (similar to `.git/` separate from source files)
- Supports future scalability (multiple conversation stores, archiving, etc.)

#### `prompts/functions/` and `prompts/models/`
**Decision: APPROVED - Keep in prompts/**

**Rationale:**
- Direct dependencies of prompt execution
- Shared configuration across multiple prompts
- System-level infrastructure components
- Static assets that belong with prompt definitions

### 🤔 Problematic Components

#### `prompts/logs/` and `prompts/logs-xxx/`
**Decision: NEEDS IMPROVEMENT - Consider reorganization**

**Current Issues:**
- **Mixed concerns**: Static prompt files mixed with dynamic log files
- **Directory cluttering**: Runtime artifacts clutter the prompts directory
- **Scalability problems**: Logs can grow very large over time
- **Cleanup complexity**: Hard to clean logs without affecting prompts
- **Information duplication**: Conversation content exists in both logs and conversation files

#### `prompts/costs.db`
**Decision: ACCEPTABLE - But could be improved**

**Current State**: Works but could be better organized
**Future Consideration**: Move to dedicated data directory

## Critical Architectural Issue: Logs vs. Conversations

### Information Duplication Problem

**Current Overlap:**
```bash
# This command creates BOTH:
keprompt -e prompt --conversation session --debug
# → prompts/logs-prompt/     (debug output with conversation flow)
# → conversations/session.conversation  (structured conversation data)
```

**Duplication Analysis:**
- **logs-xxx/**: Contains conversation flow as human-readable debug output
- **conversations/**: Contains conversation flow as structured JSON data
- **Result**: Same information stored twice in different formats

### Different Use Cases

**Logs are for**: "What happened during execution?"
- Execution traces and diagnostics
- Debug information for developers
- Performance metrics
- Error messages and troubleshooting

**Conversations are for**: "What's the current conversation state?"
- Persistent conversation state for continuation
- Structured data for programmatic access
- User session management
- Conversation history and analysis

### Lifecycle Inconsistencies

**Logs**: Created only with `--debug` or `--log` flags
**Conversations**: Created always when using `--conversation`
**Problem**: Sometimes you have logs without conversations, sometimes conversations without logs

## Recommended Future Architecture

### Phase 1: Current v1.4.0 (Stable)
Keep current structure for stability, but establish clear data source priorities:

```
/project/
├── prompts/              # Static assets + execution artifacts (current)
│   ├── functions/        # ✅ Keep
│   ├── models/          # ✅ Keep  
│   ├── logs/            # 🤔 Keep for now
│   ├── logs-xxx/        # 🤔 Keep for now
│   ├── costs.db         # 🤔 Keep for now
│   └── *.prompt         # ✅ Keep
├── conversations/        # ✅ PRIMARY source for conversation data
└── [other files]
```

**Implementation Strategy:**
- **conversations/** as primary source for conversation viewing
- **logs-xxx/** as supplementary debug information only
- **Independence**: Conversation features work without logs

### Phase 2: Future Enhancement (v1.5.0+)

```
/project/
├── prompts/              # Static prompt assets only
│   ├── functions/        # Custom functions
│   ├── models/          # Model configurations
│   └── *.prompt         # Prompt files
├── conversations/        # Dynamic conversation data
│   └── *.conversation   # JSON conversation files
├── logs/                # Execution diagnostics only
│   ├── execution/       # General execution logs
│   └── debug/          # Debug-specific logs (no conversation duplication)
└── data/                # System data
    └── costs.db         # Cost tracking database
```

**Benefits of Future Architecture:**
- **Clear separation**: Static assets, dynamic sessions, execution logs, system data
- **No duplication**: Conversation content only in conversations/
- **Scalability**: Each directory can grow independently
- **Maintenance**: Easy to clean/archive different types of data
- **Backup strategies**: Different retention policies for different data types

## Implementation Guidelines

### For v1.4.0 Conversation Management
- **Primary data source**: Always use `conversations/` directory
- **Supplementary information**: Reference logs if available, but don't depend on them
- **Self-contained**: Conversation viewing must work without logs
- **Consistency**: All conversation-related features use the same data source

### For Future Versions
- **Migration planning**: Provide smooth upgrade path
- **Backward compatibility**: Support old structure during transition
- **Documentation**: Clear migration guide for users
- **Testing**: Ensure all features work with new structure

## Architectural Principles

### Separation of Concerns
- **Static vs. Dynamic**: Separate static assets from runtime data
- **Source vs. Artifacts**: Separate source files from generated artifacts
- **User vs. System**: Separate user-facing data from system internals

### Data Lifecycle Management
- **Different retention policies**: Prompts (permanent), conversations (session-based), logs (temporary)
- **Different backup strategies**: Version control vs. user data vs. diagnostic data
- **Different access patterns**: Browse vs. continue vs. debug

### Scalability Considerations
- **Growth patterns**: Logs and conversations can grow large
- **Performance**: Directory structure should support efficient access
- **Maintenance**: Easy cleanup and archiving of different data types

## Decision Summary

1. **✅ conversations/ at project root**: APPROVED - Excellent architectural decision
2. **✅ prompts/functions/ and prompts/models/**: APPROVED - Proper placement
3. **🤔 prompts/logs/ directories**: NEEDS IMPROVEMENT - Consider future reorganization
4. **🤔 prompts/costs.db**: ACCEPTABLE - Could be improved in future versions

## Migration Considerations

### Breaking Changes Required for Full Cleanup
- Code updates to look for logs in new locations
- Documentation updates across all materials
- Migration scripts for existing installations
- Backward compatibility support during transition

### Recommended Approach
- **Phase 1**: Stabilize current structure, establish clear data source priorities
- **Phase 2**: Plan and execute architectural improvements with proper migration
- **Communication**: Clear roadmap and migration guide for users

This architectural analysis provides the foundation for maintaining a clean, scalable, and maintainable directory structure as KePrompt continues to evolve.

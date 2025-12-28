# KePrompt TUI - Terminal User Interface

## Overview

The KePrompt TUI provides an interactive terminal interface for managing KePrompt sessions, models, prompts, and system operations. Built with Textual, it offers a modern, keyboard-driven experience that teaches users the KePrompt command syntax.

## Launch

```bash
keprompt tui
```

## Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│ KePrompt TUI v1.6.0                                         │
├─────────────────────────────────────────────────────────────┤
│ [Sessions][Models][Prompts][Database][System][Results]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Tab Content Area                                           │
│  • Sessions: Session management (Coming Soon)              │
│  • Models: AI model browser (Coming Soon)                  │
│  • Prompts: Prompt file manager (Coming Soon)              │
│  • Database: Database tools (Coming Soon)                  │
│  • System: System management (Coming Soon)                 │
│  • Results: ✅ FULLY FUNCTIONAL command output             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Command: get sessions                             [Ctrl+P]  │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### ✅ Functional Features
- **Command Line Interface**: Bottom input accepts KePrompt commands without "keprompt" prefix
- **Auto-completion/Look-ahead**: Real-time command suggestions as you type
- **Tab Completion**: Press `Tab` to cycle through available command completions
- **Command Palette**: Press `Ctrl+P` to open command palette with fuzzy search
- **Results Display**: Rich formatting of JSON responses, tables, and errors
- **Command History**: Use ↑/↓ arrows to navigate through command history (50 commands)
- **Visual Suggestions**: Live suggestion display shows available commands and parameters
- **Keyboard Shortcuts**: F1-F6 for tab switching, Ctrl+C to quit

### 🚧 Coming Soon (Placeholder Tabs)
- **Sessions Tab**: Interactive session management with chat interface
- **Models Tab**: Filterable model browser with provider/company filters
- **Prompts Tab**: Prompt file browser with syntax highlighting
- **Database Tab**: Database statistics and cleanup tools
- **System Tab**: Workspace and system management

## Usage Examples

### Command Line (Bottom Input)
```
get sessions                           # List all sessions
get models --provider OpenAI          # List OpenAI models
create session --prompt math-tutor    # Create new session
update session abc123 --answer "Hi"   # Continue conversation
get prompts                           # List all prompts
```

### Command Palette (Ctrl+P)
1. Press `Ctrl+P`
2. Type command (e.g., "get sessions")
3. Press Enter to execute

## Educational Design

The TUI is designed to teach KePrompt CLI syntax:
- **In TUI**: Type `get sessions`
- **In Terminal**: User naturally knows to type `keprompt get sessions`

This creates a smooth learning path from visual interface to command-line mastery.

## Technical Details

### Architecture
- **Framework**: Textual (Python TUI framework)
- **Integration**: Direct calls to KePrompt JSON API
- **Command Execution**: Uses existing `handle_json_command()` function
- **Display**: Rich formatting with syntax highlighting and tables

### File Structure
- `keprompt/tui_app.py` - Main TUI application
- `keprompt/keprompt.py` - Integration with main CLI (handles `keprompt tui`)

### Dependencies
All dependencies are already in `requirements.txt`:
- `textual>=0.41.0` - TUI framework
- `rich>=13.0.0` - Text formatting (used by Textual)

## Development Roadmap

### Phase 1: ✅ Complete
- [x] TUI skeleton with all tabs
- [x] Command line interface
- [x] Command palette
- [x] Results tab with rich display
- [x] Integration with main CLI

### Phase 2: Sessions Tab
- [ ] Session list with metadata
- [ ] Session detail view
- [ ] Chat interface for continuing sessions
- [ ] Session creation dialog

### Phase 3: Models Tab
- [ ] Filterable model table
- [ ] Provider/company filters
- [ ] Model comparison view
- [ ] Cost information display

### Phase 4: Additional Tabs
- [ ] Prompts tab with file browser
- [ ] Database tab with statistics
- [ ] System tab with management tools

## Testing

```bash
# Test TUI imports
python -c "from keprompt.tui_app import KePromptTUI; print('Success')"

# Test command integration
keprompt --help  # Should show TUI in help

# Launch TUI (interactive)
keprompt tui
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+P` | Open command palette |
| `Ctrl+C` | Quit application |
| `F1-F6` | Switch between tabs |
| `↑/↓` | Navigate command history |
| `Enter` | Execute command |
| `Tab` | Navigate between UI elements |

The TUI provides immediate value as a command executor and learning tool, with a clear path for progressive enhancement of each tab.

# KePrompt v1.4.0 Release Notes

## 🎉 Major Release: Professional Conversation Management

**Release Date**: September 17, 2025  
**Version**: 1.4.0  
**Previous Version**: 1.3.1

---

## 🚀 New Features

### Professional Conversation Viewing System

**Two powerful new commands for conversation management:**

#### 1. List All Conversations (`--list-conversations`)
```bash
keprompt --list-conversations
```

**Features:**
- **Professional tabular overview** of all conversations
- **Model information** and message counts
- **Last updated timestamps** for easy tracking
- **Integrated cost tracking** with total costs per conversation
- **Semantic name resolution** for cost analysis

**Example Output:**
```
                                 Available Conversations                                 
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Name         ┃ Model                    ┃ Messages ┃ Last Updated        ┃ Total Cost ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ math-tutor   │ gpt-4o-mini              │       12 │ 2025-09-17 09:31:36 │  $0.000458 │
│ research-ai  │ claude-3-5-sonnet        │        8 │ 2025-09-17 08:15:22 │  $0.012340 │
└──────────────┴──────────────────────────┴──────────┴─────────────────────┴────────────┘
```

#### 2. View Detailed Conversation (`--view-conversation <name>`)
```bash
keprompt --view-conversation my_session
```

**Features:**
- **Complete conversation summary** with model, cost, and metadata
- **Enhanced readability** with LaTeX cleanup and smart text wrapping
- **Cost integration** showing total calls, costs, and token usage
- **Relationship tracking** linking to original prompt files
- **Professional formatting** with role-based color coding

---

## 🎯 Enhanced Readability Features

### LaTeX Math Formatting Cleanup
**Problem Solved:** Mathematical content in conversations (especially educational content) was extremely hard to read due to LaTeX formatting.

**Before (Hard to Read):**
```
\(\displaystyle \frac{2x + 3}{6}\) as a sum (or difference) of simpler fractions.
```

**After (Easy to Read):**
```
(2x + 3)/(6) as a sum (or difference) of simpler fractions.
```

### Smart Text Wrapping
- **Intelligent line breaking** at word boundaries (no mid-word breaks)
- **Proper indentation** maintained throughout
- **Natural reading flow** preserved
- **80-character line limit** for optimal readability

### LaTeX Cleanup Transformations
- `\(\)` → removed (inline math delimiters)
- `\[\]` → proper line breaks (display math)
- `\displaystyle` → removed
- `\frac{a}{b}` → `(a)/(b)`
- `\;` → proper spacing
- `\qquad` → readable spacing

---

## 💰 Cost Integration Enhancements

### Database Integration
- **Automatic cost lookup** from `prompts/costs.db`
- **Semantic name resolution** for relationship tracking
- **Total cost calculation** across conversation sessions
- **Token usage statistics** (input/output breakdown)

### Relationship Tracking
- **Links conversations to original prompt files**
- **Inherits semantic names** from `.prompt` statements
- **Tracks conversation continuations** properly
- **Maintains cost continuity** across sessions

---

## 🔧 Technical Improvements

### AiModel Serialization Enhancement
**Problem Solved:** Database entries showed useless `<AiModel object>` representations.

**Before:**
```json
{
  "model": "<AiModel object>",
  "filename": "<PosixPath object>"
}
```

**After:**
```json
{
  "model": "AiModel(name='gpt-4o-mini', provider='OpenAI', company='OpenAI', input=6e-07, output=2.4e-06, context=128000)",
  "filename": "prompts/simple_test.prompt"
}
```

### Conversation Continuation Improvements
- **Metadata inheritance** from original prompts
- **Semantic name preservation** across conversation sessions
- **Professional cost tracking** for conversation continuations
- **Enhanced debugging** with proper object serialization

---

## 📊 Use Cases & Benefits

### Educational Content
- **Math tutoring conversations** now perfectly readable
- **LaTeX equations** displayed in clear, understandable format
- **Educational analytics** with cost tracking per conversation
- **Learning progress tracking** through conversation history

### Development & Debugging
- **Conversation analysis** for AI interaction patterns
- **Cost optimization** by identifying expensive conversation flows
- **Model comparison** across different conversations
- **Professional debugging** with complete variable state visibility

### Production Monitoring
- **Real-time cost tracking** for conversation-based applications
- **Usage pattern analysis** for business intelligence
- **Performance metrics** with token usage and response quality
- **Relationship analysis** linking conversations to business processes

---

## 🏗️ Architecture & Implementation

### New Components
- **`list_conversations()`**: Scans conversation directory and integrates cost data
- **`view_conversation()`**: Detailed conversation display with formatting
- **LaTeX cleanup engine**: Text processing for mathematical content
- **Smart text wrapper**: Intelligent line breaking at word boundaries
- **Cost query system**: SQLite integration for cost analysis

### File Structure
```
conversations/
├── conversation-name.conversation  # JSON conversation files
└── ...

prompts/
├── costs.db                       # Enhanced cost tracking database
└── ...

ks/
├── conversation-management.md      # New technical documentation
└── ...
```

### Enhanced Conversation Format
```json
{
  "vm_state": {
    "model_name": "gpt-4o-mini",
    "interaction_no": 3,
    "created": "2025-09-17 09:31:36"
  },
  "messages": [
    {
      "role": "user|assistant|system|tool",
      "content": [{"type": "text", "text": "content"}]
    }
  ],
  "variables": {
    "model": "AiModel(name='gpt-4o-mini', provider='OpenAI', ...)",
    "filename": "prompts/original.prompt"
  }
}
```

---

## 📚 Documentation Updates

### Updated Files
- **README.md**: Added comprehensive conversation viewing section
- **docs/QUICK_REFERENCE.md**: Updated with new commands and features
- **ks/conversation-management.md**: New technical documentation
- **ks/**: Enhanced context documentation for AI development

### New Command Reference
| Command | Description | Example |
|---------|-------------|---------|
| `keprompt --list-conversations` | List all conversations with costs | `keprompt --list-conversations` |
| `keprompt --view-conversation <name>` | View detailed conversation history | `keprompt --view-conversation my_session` |

---

## 🔄 Migration & Compatibility

### Backward Compatibility
- **Existing conversations** remain fully functional
- **Legacy cost data** preserved and accessible
- **No breaking changes** to existing workflows
- **Gradual migration** to improved serialization

### Database Migration
- **Automatic schema updates** for cost tracking
- **Improved object serialization** for new entries
- **Legacy data remains accessible**
- **Clean migration path** for existing installations

---

## 🎯 Future Roadmap

### Planned Enhancements
- **Conversation search and filtering**
- **Export capabilities** (PDF, HTML)
- **Conversation templates and patterns**
- **Advanced cost analytics and reporting**
- **Conversation merging and splitting tools**

### Integration Opportunities
- **Business intelligence dashboards**
- **Educational management systems**
- **Customer support analytics**
- **AI training and fine-tuning workflows**

---

## 🚀 Getting Started with v1.4.0

### Upgrade Instructions
```bash
# Update KePrompt
pip install --upgrade keprompt

# Verify new version
keprompt --version
```

### Try the New Features
```bash
# List your conversations
keprompt --list-conversations

# View a specific conversation
keprompt --view-conversation your_conversation_name

# Start a new conversation and see the improved tracking
keprompt -e your_prompt --conversation test_v140 --debug
```

---

## 🎉 Summary

**KePrompt v1.4.0** represents a significant leap forward in conversation management and user experience:

- **Professional conversation viewing** with comprehensive cost integration
- **Enhanced readability** making mathematical and complex content easy to read
- **Improved cost tracking** with relationship analysis across conversation sessions
- **Better debugging experience** with proper object serialization
- **Comprehensive documentation** for professional deployment

This release transforms KePrompt from a simple prompt execution tool into a **professional conversation management platform** suitable for educational, development, and production environments.

**Perfect for:**
- **Educational institutions** using AI for math tutoring and learning
- **Development teams** building conversational AI applications
- **Businesses** requiring professional AI conversation management
- **Researchers** analyzing AI interaction patterns and costs

---

## 🙏 Acknowledgments

This release addresses real user feedback about conversation readability and management. Special thanks to users who reported issues with mathematical content display and requested better conversation tracking capabilities.

---

**Download KePrompt v1.4.0 today and experience professional-grade AI conversation management!**

```bash
pip install --upgrade keprompt
```

For support and questions, visit our [GitHub repository](https://github.com/JerryWestrick/keprompt).

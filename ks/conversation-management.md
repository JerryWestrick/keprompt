# KePrompt Conversation Management (v1.4.0)

## Professional Conversation Viewing System

### Overview
KePrompt v1.4.0 introduces comprehensive conversation management capabilities with professional-grade viewing, cost tracking integration, and enhanced readability features.

## New Commands

### List All Conversations
```bash
keprompt --list-conversations
```

**Features:**
- Tabular overview of all conversations
- Model information and message counts
- Last updated timestamps
- **Integrated cost tracking** with total costs per conversation
- Semantic name resolution for cost analysis

**Example Output:**
```
                                 Available Conversations                                 
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Name         ┃ Model                    ┃ Messages ┃ Last Updated        ┃ Total Cost ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ test-fix     │ gpt-4o-mini              │       12 │ 2025-09-17 09:31:36 │  $0.000458 │
│ MathTutor-3  │ openai/gpt-oss-120b      │       12 │ 2025-09-17 09:14:53 │        N/A │
└──────────────┴──────────────────────────┴──────────┴─────────────────────┴────────────┘
```

### View Detailed Conversation
```bash
keprompt --view-conversation <conversation-name>
```

**Features:**
- **Complete conversation summary** with model, cost, and metadata
- **Enhanced readability** with LaTeX cleanup and smart text wrapping
- **Cost integration** showing total calls, costs, and token usage
- **Relationship tracking** linking to original prompt files
- **Professional formatting** with role-based color coding

## Enhanced Readability Features

### LaTeX Math Formatting
**Before (Hard to Read):**
```
\(\displaystyle \frac{2x + 3}{6}\) as a sum (or difference) of simpler fractions.
```

**After (Easy to Read):**
```
(2x + 3)/(6) as a sum (or difference) of simpler fractions.
```

### Smart Text Wrapping
- Lines longer than 80 characters automatically wrap
- Word boundaries respected (no mid-word breaks)
- Proper indentation maintained
- Natural reading flow preserved

### LaTeX Cleanup Transformations
- `\(\)` → removed (inline math delimiters)
- `\[\]` → proper line breaks (display math)
- `\displaystyle` → removed
- `\frac{a}{b}` → `(a)/(b)`
- `\;` → proper spacing
- `\qquad` → readable spacing

## Cost Integration

### Database Integration
- Automatic cost lookup from `prompts/costs.db`
- Semantic name resolution for relationship tracking
- Total cost calculation across conversation sessions
- Token usage statistics (input/output)

### Relationship Tracking
- Links conversations to original prompt files
- Inherits semantic names from `.prompt` statements
- Tracks conversation continuations properly
- Maintains cost continuity across sessions

## Technical Implementation

### Architecture Components
- **list_conversations()**: Scans conversation directory and integrates cost data
- **view_conversation()**: Detailed conversation display with formatting
- **LaTeX cleanup**: Text processing for mathematical content
- **Smart wrapping**: Intelligent line breaking at word boundaries
- **Cost queries**: SQLite integration for cost analysis

### File Structure
```
conversations/
├── conversation-name.conversation  # JSON conversation files
└── ...

prompts/
├── costs.db                       # Cost tracking database
└── ...
```

### Conversation File Format
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
    "model": "AiModel(name='gpt-4o-mini', ...)",
    "filename": "prompts/original.prompt"
  }
}
```

## Integration with Existing Features

### Cost Tracking System
- Seamless integration with existing cost database
- Automatic cost aggregation by semantic name
- Backward compatibility with existing cost entries
- Enhanced cost analysis capabilities

### Prompt Versioning System
- Inherits semantic names from original prompts
- Version tracking across conversation sessions
- Metadata preservation in conversation continuations
- Professional prompt management integration

### AiModel Serialization
- Consistent object representation across all features
- Improved debugging and analysis capabilities
- Professional data quality in conversation variables
- Enhanced development experience

## Use Cases

### Development and Debugging
- **Conversation Analysis**: Review AI interaction patterns
- **Cost Optimization**: Identify expensive conversation flows
- **Model Comparison**: Compare performance across different models
- **Debugging**: Examine conversation state and variables

### Production Monitoring
- **Cost Tracking**: Monitor conversation costs in real-time
- **Usage Analysis**: Understand conversation patterns and frequency
- **Performance Metrics**: Track token usage and response quality
- **Relationship Analysis**: Link conversations to business processes

### Educational and Training
- **Math Tutoring**: Enhanced readability for mathematical content
- **Conversation Review**: Easy-to-read conversation histories
- **Learning Analytics**: Track educational conversation effectiveness
- **Content Analysis**: Review and improve conversational AI content

## Future Enhancements

### Planned Features
- Conversation search and filtering
- Export capabilities (PDF, HTML)
- Conversation templates and patterns
- Advanced cost analytics and reporting
- Conversation merging and splitting tools

### Integration Opportunities
- Business intelligence dashboards
- Educational management systems
- Customer support analytics
- AI training and fine-tuning workflows

## Migration and Compatibility

### Backward Compatibility
- Existing conversations remain fully functional
- Legacy cost data preserved and accessible
- Gradual migration to improved serialization
- No breaking changes to existing workflows

### Database Migration
- Automatic schema updates for cost tracking
- Improved object serialization for new entries
- Legacy data remains accessible
- Clean migration path for existing installations

This conversation management system represents a significant enhancement to KePrompt's professional capabilities, providing comprehensive tools for conversation analysis, cost tracking, and user experience optimization.

# KePrompt Documentation

Welcome to the comprehensive documentation for KePrompt - a powerful command-line tool for prompt engineering and AI interaction.

## 📚 Documentation Structure

### [Quick Start (Main README)](../README_NEW.md)
**Start here!** Get up and running with KePrompt in 5 minutes.
- Installation and setup
- Your first prompt
- Core concepts overview
- Essential commands

### [Complete Tutorial](TUTORIAL.md)
**Learn by doing.** Step-by-step guide from beginner to power user.
- Detailed explanations of all features
- Hands-on examples with real code
- Best practices and tips
- Advanced workflows

### [Quick Reference](QUICK_REFERENCE.md)
**Handy cheat sheet.** All commands, syntax, and patterns in one place.
- Command reference table
- Prompt language syntax
- Function reference
- Troubleshooting guide

### [Examples Collection](EXAMPLES.md)
**Real-world use cases.** Copy-paste ready examples for common tasks.
- Content creation workflows
- Code analysis and review
- Research and data processing
- Business automation

## 🎯 Choose Your Path

### New to KePrompt?
1. **Start with the [Main README](../README_NEW.md)** - Get the basics
2. **Try the [Tutorial](TUTORIAL.md)** - Learn step by step
3. **Bookmark the [Quick Reference](QUICK_REFERENCE.md)** - For daily use

### Looking for Specific Examples?
- **Content Creation**: Blog posts, documentation, social media
- **Code Analysis**: Reviews, security scans, repository analysis
- **Research**: Market analysis, academic research, data processing
- **Business**: Meeting minutes, proposals, reports
- **Education**: Tutorials, explanations, study guides

### Need Quick Help?
- **Commands**: Check the [Quick Reference](QUICK_REFERENCE.md#essential-commands)
- **Syntax**: See the [Prompt Language Cheat Sheet](QUICK_REFERENCE.md#prompt-language-cheat-sheet)
- **Troubleshooting**: Common issues and solutions in [Quick Reference](QUICK_REFERENCE.md#troubleshooting)

## 🔧 Key Features Overview

### Multi-Provider AI Support
Work with OpenAI, Anthropic, Google, MistralAI, XAI, DeepSeek, and more through a single interface.

### Simple Prompt Language
Write prompts using an intuitive syntax with 15+ statement types:
```
.llm {"model": "gpt-4o-mini"}
.system You are a helpful assistant
.user Hello world
.exec
```

### Powerful Function System
- **Built-in functions**: File operations, web requests, user interaction
- **Custom functions**: Write in any language (Python, Bash, etc.)
- **Function chaining**: Combine multiple operations

### Conversation Management
- Save and resume multi-turn conversations
- Cross-session persistence
- Conversation branching and continuation

### Cost Management
- Token usage tracking
- Cost estimation across providers
- Model comparison and selection

### Production Ready
- Comprehensive logging (production/debug modes)
- Error handling and recovery
- Integration with CI/CD and automation

## 📖 Documentation Quick Links

| Topic | Quick Reference | Detailed Guide | Examples |
|-------|----------------|----------------|----------|
| **Getting Started** | [Commands](QUICK_REFERENCE.md#essential-commands) | [Installation](TUTORIAL.md#getting-started) | [Hello World](../README_NEW.md#quick-start) |
| **Prompt Language** | [Syntax](QUICK_REFERENCE.md#prompt-language-cheat-sheet) | [Language Guide](TUTORIAL.md#understanding-the-prompt-language) | [All Statements](EXAMPLES.md) |
| **Variables** | [Variable Syntax](QUICK_REFERENCE.md#variables) | [Working with Variables](TUTORIAL.md#working-with-variables) | [Parameterized Prompts](EXAMPLES.md) |
| **Functions** | [Function List](QUICK_REFERENCE.md#built-in-functions) | [Using Functions](TUTORIAL.md#using-functions) | [Function Examples](EXAMPLES.md) |
| **Custom Functions** | [Templates](QUICK_REFERENCE.md#custom-functions) | [Creating Functions](TUTORIAL.md#creating-custom-functions) | [Real Functions](EXAMPLES.md) |
| **Conversations** | [Commands](QUICK_REFERENCE.md#conversation-management) | [Managing Conversations](TUTORIAL.md#managing-conversations) | [Multi-turn Examples](EXAMPLES.md) |
| **Models** | [Model Commands](QUICK_REFERENCE.md#model-management) | [Working with Models](../README_NEW.md#working-with-models) | [Model Selection](EXAMPLES.md) |
| **Troubleshooting** | [Common Issues](QUICK_REFERENCE.md#troubleshooting) | [Debug Guide](TUTORIAL.md#production-tips) | [Error Handling](EXAMPLES.md) |

## 🚀 Common Use Cases

### For Developers
- **Code Review**: Automated code analysis and improvement suggestions
- **Documentation**: Generate API docs, README files, tutorials
- **Testing**: Create test cases, analyze logs, debug issues
- **Release Management**: Generate release notes, changelogs

### For Content Creators
- **Blog Writing**: SEO-optimized posts with social media promotion
- **Technical Writing**: Documentation, tutorials, guides
- **Social Media**: Content calendars, post generation, engagement

### For Researchers
- **Market Analysis**: Competitive research, trend analysis
- **Academic Research**: Literature reviews, methodology design
- **Data Analysis**: CSV processing, statistical insights

### For Business Users
- **Meeting Management**: Minutes, action items, follow-ups
- **Proposal Writing**: Client proposals, project scoping
- **Report Generation**: Executive summaries, status reports

## 🛠️ Integration Examples

### Shell Scripts
```bash
#!/bin/bash
result=$(keprompt -e analyze --param file "$1")
echo "Analysis: $result"
```

### CI/CD Pipelines
```yaml
- name: Generate Release Notes
  run: keprompt -e release_notes --param version "${{ github.ref }}"
```

### Cron Jobs
```bash
# Daily reports
0 9 * * * keprompt -e daily_report --log "daily_$(date +%Y%m%d)"
```

## 💡 Tips for Success

1. **Start Simple**: Begin with basic prompts, add complexity gradually
2. **Use Debug Mode**: Always use `--debug` when developing prompts
3. **Organize Your Work**: Create directories for different prompt types
4. **Version Control**: Keep your prompts in git repositories
5. **Monitor Costs**: Use cheaper models for development, premium for production
6. **Test Functions**: Verify custom functions work independently
7. **Document Everything**: Use comments in your prompt files

## 🆘 Getting Help

### Built-in Help
```bash
keprompt --help          # Full command reference
keprompt -s              # List statement types
keprompt -f              # List available functions
keprompt -m              # List available models
```

### Community & Support
- **GitHub Repository**: [keprompt](https://github.com/JerryWestrick/keprompt)
- **Issues & Bug Reports**: Use GitHub issues
- **Feature Requests**: Submit via GitHub
- **Discussions**: Community discussions on GitHub

### Documentation Feedback
Found an error or want to suggest improvements? Please:
1. Open an issue on GitHub
2. Submit a pull request with corrections
3. Share your use cases and examples

## 📋 Documentation Checklist

When working with KePrompt, use this checklist to find what you need:

- [ ] **New user?** → Start with [Main README](../README_NEW.md)
- [ ] **Learning the basics?** → Follow the [Tutorial](TUTORIAL.md)
- [ ] **Need quick syntax help?** → Check [Quick Reference](QUICK_REFERENCE.md)
- [ ] **Looking for examples?** → Browse [Examples Collection](EXAMPLES.md)
- [ ] **Building custom functions?** → See [Function Templates](QUICK_REFERENCE.md#custom-functions)
- [ ] **Troubleshooting issues?** → Check [Troubleshooting Guide](QUICK_REFERENCE.md#troubleshooting)
- [ ] **Optimizing costs?** → Review [Cost Management](QUICK_REFERENCE.md#cost-management)
- [ ] **Integrating with tools?** → See [Integration Examples](QUICK_REFERENCE.md#integration-examples)

---

**Happy prompting!** 🎉

*KePrompt: Making AI interaction simple, powerful, and cost-effective.*

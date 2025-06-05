# Tinker - Phase 3.2

Let's add anthropic APIs. I've already have ANTHROPIC_API_KEY in .env file. However, I haven't updated any code around it.

Can you add it and make it the default agent?

## Task List

### 🔧 Core Implementation
1. **Add Anthropic dependency** - Update `pyproject.toml` with `anthropic` package
2. **Create AnthropicToolsManager** - Convert existing OpenAI tools to Anthropic format
3. **Update main.py** - Add Anthropic client initialization and make it default
4. **Create process_task_with_anthropic_tools()** - Handle Claude's conversation flow

### 🔄 Integration
5. **Agent selection logic** - Prioritize Anthropic, fallback to OpenAI
6. **Update task analysis** - Make `analyze_task_with_ai()` work with both agents
7. **Test all tools** - Verify shell commands, file ops, and email work with Claude

### 📚 Final Steps
8. **Update documentation** - Add Anthropic setup instructions
9. **End-to-end testing** - Ensure Phase 3.1 functionality still works
10. **Clean up imports** - Organize code for maintainability


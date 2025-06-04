# Tinker - Phase 3.1

Today was mostly sidetracked with kid annual physical and TechEx expo. So got 1 hour to iterate on Tinker.

I want tinker to use Claude Sonnet 4 since that one has been the best coding agent so far. 

And in yesterday's tests, GPT 4.1 sometimes deletes certain section of the code.

## Task

- [x] Use Claude Sonnet 4
- [ ] Hand Validate

## Implementation Details

### Phase 3.1 Changes:
1. **Claude Sonnet Integration**: Added Anthropic client as primary AI provider
2. **Dual AI Support**: Fallback to OpenAI if Anthropic API key is not available  
3. **Enhanced Model**: Using `claude-3-5-sonnet-20241022` for improved coding capabilities
4. **Backwards Compatibility**: Maintains existing OpenAI support for seamless transition

### Client Priority:
1. **Claude (Anthropic)** - Primary choice for enhanced coding performance
2. **OpenAI GPT-4** - Fallback option for existing users

### Environment Variables:
- `ANTHROPIC_API_KEY` - For Claude Sonnet (preferred)
- `OPENAI_API_KEY` - For GPT-4 (fallback)

The system automatically detects available API keys and uses Claude if available, falling back to OpenAI if needed.
- [ ] Update the shell execution to use "tools" field instead.
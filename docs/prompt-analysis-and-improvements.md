# Tinker Prompt Analysis and Improvements

## Current Prompts Review

### 1. Main System Prompt (langgraph_nodes.py, lines 43-88)

**Issues:**
- Too focused on "Pixel" project (hardcoded context)
- Very long and complex
- Mixes identity, capabilities, and guidelines
- Power management instructions are overly specific
- GitHub repository is hardcoded

**Improvements:**
- Make it more generic and adaptable
- Simplify and structure better
- Remove hardcoded project references
- Focus on core capabilities

### 2. Tool Decision Prompt (langgraph_nodes.py, lines 110-123)

**Issues:**
- Good structure but could be clearer
- Examples are helpful but limited
- Could better explain the decision logic

**Improvements:**
- Add more diverse examples
- Clarify decision criteria
- Better guidance for edge cases

### 3. Tool Result Analysis Prompt (langgraph_nodes.py, lines 307-312)

**Issues:**
- Very simple and functional
- Could provide better guidance on analysis depth
- Doesn't specify output format preferences

**Improvements:**
- Add guidance for different types of outputs
- Specify analysis depth and focus areas
- Better instruction on relevance filtering

### 4. Continuous Agent Thinking Prompt (continuous_agent_nodes.py, lines 32-52)

**Issues:**
- Good structure but could be more focused
- Questions are good but could be more specific
- Missing guidance on iteration efficiency

**Improvements:**
- Add time/iteration awareness
- Better guidance on goal decomposition
- Clearer success criteria

### 5. Action Decision Prompt (continuous_agent_nodes.py, lines 103-106)

**Issues:**
- Very minimal
- Lacks safety considerations
- Could provide better command formatting guidance

**Improvements:**
- Add safety guidelines
- Better command format examples
- Error handling guidance

## Recommended Improvements

### Enhanced System Prompt
- Generic, adaptable identity
- Clearer capability definitions
- Better structured guidelines
- Safety-first approach

### Improved Tool Decision Logic
- More sophisticated decision criteria
- Better examples across domains
- Clearer output format

### Enhanced Result Analysis
- Depth guidance based on context
- Format preferences
- Relevance filtering

### Better Continuous Reasoning
- Iteration efficiency focus
- Goal decomposition guidance
- Success criteria clarity

### Safer Action Decisions
- Built-in safety checks
- Command validation
- Error recovery guidance
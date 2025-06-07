# Tinker - Phase 5.0: LangGraph Evaluation

Write a design doc.

## Overview

Add LangGraph to enable persistent memory, context summarization, and resumable workflows. Transform Tinker from stateless task processor to autonomous agent with cross-session continuity.

## Current Limitations
1. **No persistent memory** - Each task starts fresh
2. **No context summarization** - Token limits in long conversations  
3. **No resumption** - Interrupted tasks cannot continue
4. **No cross-session learning** - Previous attempts lost
5. **Linear execution only** - No complex workflow orchestration

## Implementation Plan

### Phase 5.1: Foundation (Week 1-2)
```toml
# pyproject.toml
langgraph = "^0.4.8"
langchain = "^0.3.25" 
langchain-openai = "^0.3.21"
langchain-anthropic = "^0.3.15"
```

- Wrap existing `AnthropicToolsManager` in LangGraph nodes
- Parallel implementation alongside current system
- Basic SQLite checkpointing

### Phase 5.2: Memory System (Week 3-4)
- Replace `state.md` with structured memory database
- Auto-summarization at 75% token limit
- Cross-session context persistence

### Phase 5.3: Workflow Enhancement (Week 5-6)
- Multi-step task orchestration
- Conditional workflow routing
- Error recovery workflows

## Core Components

### State Management
```python
class TinkerState(TypedDict):
    task_content: str
    conversation_history: List[BaseMessage]
    tool_results: List[Dict]
    current_directory: str
    resumption_point: Optional[str]
```

### Memory Manager
```python
class TinkerMemoryManager:
    def __init__(self):
        self.checkpointer = SqliteSaver.from_conn_string(".tinker/memory.db")
    
    def save_conversation_state(self, thread_id, state): pass
    def summarize_long_context(self, messages): pass
    def resume_from_checkpoint(self, thread_id): pass
```

### Workflow Design
```python
class TinkerWorkflow(StateGraph):
    def __init__(self):
        super().__init__(TinkerState)
        self.add_node("task_analyzer", self.analyze_task)
        self.add_node("tool_executor", self.execute_tools)
        self.add_node("memory_manager", self.manage_memory)
        # Conditional edges for workflow control
```

## Migration Strategy

**Backward Compatibility**: Maintain existing CLI interface and Docker integration. Wrap current tools in LangGraph nodes.

**Implementation Approach**: 
1. Add `--langgraph` flag for testing new system
2. Run both systems in parallel during development
3. Gradual feature migration once stable
4. Complete transition after validation

## Success Criteria

- Context preservation across sessions
- Task resumption after interruption  
- Automatic context summarization
- Performance parity with current system
- 90%+ resumption success rate
# Tinker - Phase 5.2: Advanced Memory System

## Overview

Build upon Phase 5.1's foundation to implement intelligent memory management, context summarization, and cross-session persistence. Transform the basic checkpointing into a sophisticated memory system that can handle long conversations and learn from previous sessions.

## Goals

1. **Intelligent Memory Management** - Replace simple state storage with smart memory system
2. **Context Summarization** - Auto-summarize at token limits to maintain context
3. **Cross-session Persistence** - Implement real SQLite persistence for durability
4. **Memory Retrieval** - Smart context loading based on relevance
5. **Performance Optimization** - Efficient memory operations and storage

## Current Phase 5.1 Foundation

✅ **What We Have:**
- LangGraph workflow with MemorySaver checkpointing
- Basic SQLite tables for session metadata
- State management with conversation history
- Working CLI integration with `--langgraph` flag
- Complete test coverage

🎯 **What We Need:**
- Replace MemorySaver with SQLiteSaver
- Implement context summarization at 75% token limit
- Add memory search and retrieval capabilities
- Cross-session context loading
- Enhanced error recovery

## Implementation Tasks

### Task 5.2.1: SQLite Checkpointing Migration

**Objective**: Replace MemorySaver with proper SQLite persistence

**Current Issue**: Phase 5.1 uses MemorySaver due to import issues with `langgraph.checkpoint.sqlite`

**Investigation Needed**: 
- Determine correct import path for SQLite checkpointer
- Alternative: Implement custom SQLite checkpointer
- Ensure data persistence across application restarts

**Success Criteria**:
- Checkpoints survive application restarts
- Performance comparable to MemorySaver
- No data corruption or loss

### Task 5.2.2: Context Summarization Engine

**Objective**: Implement automatic context summarization when approaching token limits

**File**: `src/tinker/memory_manager.py`

**Implementation Approach**:
```python
class TinkerMemoryManager:
    def __init__(self, anthropic_client, max_tokens=100000):
        self.max_tokens = max_tokens
        self.summarization_threshold = int(max_tokens * 0.75)  # 75%
        self.anthropic_client = anthropic_client
    
    def check_and_summarize(self, conversation_history):
        """Check if summarization is needed and perform it"""
        current_tokens = self._estimate_tokens(conversation_history)
        
        if current_tokens > self.summarization_threshold:
            return self._summarize_conversation(conversation_history)
        
        return conversation_history
    
    def _summarize_conversation(self, messages):
        """Use Claude to summarize conversation maintaining key context"""
        # Implementation with Anthropic API
        pass
```

**Success Criteria**:
- Automatic summarization at 75% token limit
- Key context preserved in summaries
- Smooth conversation flow after summarization

### Task 5.2.3: Enhanced State Management

**Objective**: Extend TinkerState with memory and context features

**File**: `src/tinker/langgraph_state.py`

**New Fields**:
```python
class TinkerState(TypedDict):
    # ...existing fields...
    memory_summary: Optional[str]
    context_window_start: Optional[str]  # Timestamp of context window start
    previous_sessions: List[str]  # Related session IDs
    token_count: int
    summarization_needed: bool
    memory_retrieval_context: Optional[Dict[str, Any]]
```

### Task 5.2.4: Cross-Session Context Loading

**Objective**: Load relevant context from previous sessions

**Implementation**:
```python
class SessionContextLoader:
    def find_related_sessions(self, current_task: str) -> List[str]:
        """Find sessions with similar tasks using embedding similarity"""
        pass
    
    def load_relevant_context(self, session_ids: List[str]) -> Dict[str, Any]:
        """Load summarized context from related sessions"""
        pass
    
    def merge_context(self, current_state: TinkerState, 
                     previous_context: Dict[str, Any]) -> TinkerState:
        """Intelligently merge previous context with current session"""
        pass
```

### Task 5.2.5: Memory Search and Retrieval

**Objective**: Implement smart memory search for context retrieval

**Features**:
- Semantic search across previous conversations
- Task similarity matching
- Tool usage pattern recognition
- Error pattern learning

### Task 5.2.6: Enhanced Error Recovery

**Objective**: Learn from previous errors and provide better recovery

**Implementation**:
- Store error patterns and resolutions
- Suggest fixes based on previous similar errors
- Automatic retry with learned solutions

## Technical Architecture

### Memory Stack
```
TinkerMemoryManager
    ├── ContextSummarizer (Anthropic-powered)
    ├── SessionContextLoader (Cross-session)
    ├── MemorySearchEngine (Semantic search)
    └── SQLiteCheckpointManager (Persistent storage)
```

### Data Flow
```
Task Input → Memory Context Loading → Workflow Execution → Memory Updates
     ↑                                                            ↓
Previous Sessions ← Context Summarization ← Token Limit Check ←───┘
```

### Database Schema Evolution
```sql
-- Enhanced tables for Phase 5.2
CREATE TABLE memory_summaries (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    summary_text TEXT,
    token_count INTEGER,
    created_at TIMESTAMP,
    context_window_start TIMESTAMP,
    context_window_end TIMESTAMP
);

CREATE TABLE session_relationships (
    id INTEGER PRIMARY KEY,
    session_a TEXT,
    session_b TEXT,
    similarity_score REAL,
    relationship_type TEXT, -- 'similar_task', 'error_resolution', 'continuation'
    created_at TIMESTAMP
);

CREATE TABLE error_patterns (
    id INTEGER PRIMARY KEY,
    error_signature TEXT,
    resolution_steps TEXT,
    success_rate REAL,
    last_used TIMESTAMP
);
```

## Migration Strategy

### Phase 5.1 → 5.2 Transition
1. **Gradual Enhancement**: Add new features alongside existing MemorySaver
2. **Data Migration**: Convert existing checkpoint data to new schema
3. **Feature Flags**: Enable advanced features incrementally
4. **Backward Compatibility**: Maintain `--langgraph` flag behavior

### Testing Strategy
- Unit tests for each memory component
- Integration tests for cross-session loading
- Performance tests for large conversation histories
- Memory leak detection for long-running sessions

## Success Metrics

### Functionality
- Cross-session context loading works reliably
- Summarization preserves key information
- Memory search returns relevant results
- Error recovery improves over time

### Performance
- Summarization completes within 5 seconds
- Context loading adds < 2 seconds to startup
- Memory operations don't degrade workflow performance
- SQLite operations are atomic and reliable

### User Experience
- Seamless conversation flow across sessions
- Relevant context appears automatically
- Better error messages and suggestions
- No manual memory management required

## Implementation Timeline

**Week 3**: SQLite migration + context summarization
**Week 4**: Cross-session loading + memory search
**Integration**: Testing, optimization, and documentation

## Next Steps

After Phase 5.2, we'll have a sophisticated memory system ready for Phase 5.3's advanced workflow orchestration, including:
- Multi-step task planning
- Conditional workflow routing
- Parallel task execution
- Complex error recovery workflows

This memory foundation will enable Tinker to become a truly autonomous agent with learning capabilities and long-term context awareness.

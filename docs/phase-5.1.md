# Tinker - Phase 5.1: LangGraph Foundation

## Overview

Establish the foundation for LangGraph integration by wrapping existing `AnthropicToolsManager` in LangGraph nodes, implementing basic SQLite checkpointing, and creating parallel system operation. This phase focuses on minimal viable integration while maintaining backward compatibility.

## Goals

1. **Dependency Integration** - Add LangGraph and LangChain dependencies
2. **Node Wrapping** - Convert existing tools to LangGraph nodes
3. **Basic Checkpointing** - Implement SQLite-based state persistence
4. **Parallel Operation** - Run LangGraph system alongside existing implementation
5. **CLI Flag Support** - Add `--langgraph` flag for testing new system

## Implementation Tasks

### Task 5.1.1: Dependency Management

**Objective**: Add LangGraph dependencies to project

**Dependencies to Add**:
```toml
langgraph = "^0.4.8"
langchain = "^0.3.25" 
langchain-openai = "^0.3.21"
langchain-anthropic = "^0.3.15"
sqlite3 = "*"  # For checkpointing
```

**File Changes**:
- Update `pyproject.toml` with new dependencies
- Run `poetry install` to update lock file

**Success Criteria**:
- All dependencies install without conflicts
- Existing functionality remains unaffected

### Task 5.1.2: Core State Definition

**Objective**: Define TinkerState structure for LangGraph workflows

**File**: `src/tinker/langgraph_state.py`

**Implementation**:
```python
from typing import Dict, List, Any, Optional, TypedDict
from langchain_core.messages import BaseMessage

class TinkerState(TypedDict):
    """Core state structure for Tinker LangGraph workflows"""
    task_content: str
    conversation_history: List[BaseMessage]
    tool_results: List[Dict[str, Any]]
    current_directory: str
    resumption_point: Optional[str]
    thread_id: Optional[str]
    checkpoint_id: Optional[str]
    execution_status: str  # "running", "completed", "failed", "paused"
```

**Success Criteria**:
- State structure supports all current functionality
- Extensible for future memory and workflow features

### Task 5.1.3: LangGraph Tool Node Wrapper

**Objective**: Wrap existing AnthropicToolsManager in LangGraph nodes

**File**: `src/tinker/langgraph_nodes.py`

**Implementation**:
```python
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph
from .anthropic_tools_manager import AnthropicToolsManager
from .langgraph_state import TinkerState

class TinkerLangGraphNodes:
    """LangGraph node implementations wrapping existing tools"""
    
    def __init__(self):
        self.tools_manager = AnthropicToolsManager()
    
    def task_analyzer_node(self, state: TinkerState) -> TinkerState:
        """Analyze incoming task and prepare for execution"""
        # Extract task requirements
        # Set execution context
        # Update state with analysis results
        pass
    
    def tool_executor_node(self, state: TinkerState) -> TinkerState:
        """Execute tools using existing AnthropicToolsManager"""
        # Route to existing tool execution
        # Capture results in state
        # Handle errors and retries
        pass
    
    def checkpoint_manager_node(self, state: TinkerState) -> TinkerState:
        """Manage state checkpointing"""
        # Save current state to SQLite
        # Update checkpoint metadata
        # Handle resumption logic
        pass
```

**Success Criteria**:
- Existing tool functionality accessible through nodes
- State properly maintained across node transitions
- Error handling preserves debugging capabilities

### Task 5.1.4: Basic SQLite Checkpointing

**Objective**: Implement simple checkpoint system using SQLite

**File**: `src/tinker/checkpoint_manager.py`

**Implementation**:
```python
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from langchain_core.runnables import ConfigurableFieldSpec
from langgraph.checkpoint.sqlite import SqliteSaver
from .langgraph_state import TinkerState

class TinkerCheckpointManager:
    """Manages state persistence using SQLite"""
    
    def __init__(self, db_path: str = ".tinker/memory.db"):
        self.db_path = db_path
        self._ensure_directory()
        self.checkpointer = SqliteSaver.from_conn_string(db_path)
    
    def _ensure_directory(self):
        """Ensure .tinker directory exists"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def save_checkpoint(self, thread_id: str, state: TinkerState) -> str:
        """Save state checkpoint and return checkpoint ID"""
        checkpoint_id = str(uuid.uuid4())
        # Use LangGraph's native checkpointing
        # Add custom metadata for Tinker-specific needs
        pass
    
    def load_checkpoint(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[TinkerState]:
        """Load state from checkpoint"""
        # Retrieve from SQLite using LangGraph checkpointer
        # Handle missing checkpoints gracefully
        pass
    
    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        """List available checkpoints for a thread"""
        pass
```

**Database Schema**:
```sql
-- Managed by LangGraph SqliteSaver, but custom tables for metadata
CREATE TABLE IF NOT EXISTS tinker_sessions (
    thread_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    task_summary TEXT,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS tinker_checkpoints_meta (
    checkpoint_id TEXT PRIMARY KEY,
    thread_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resumption_point TEXT,
    execution_status TEXT,
    FOREIGN KEY (thread_id) REFERENCES tinker_sessions(thread_id)
);
```

**Success Criteria**:
- States persist across application restarts
- Checkpoint loading restores exact execution context
- Database operations are atomic and reliable

### Task 5.1.5: LangGraph Workflow Definition

**Objective**: Create basic workflow graph connecting nodes

**File**: `src/tinker/langgraph_workflow.py`

**Implementation**:
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from .langgraph_state import TinkerState
from .langgraph_nodes import TinkerLangGraphNodes
from .checkpoint_manager import TinkerCheckpointManager

class TinkerWorkflow:
    """Main LangGraph workflow for Tinker task execution"""
    
    def __init__(self, checkpoint_manager: TinkerCheckpointManager):
        self.nodes = TinkerLangGraphNodes()
        self.checkpoint_manager = checkpoint_manager
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the execution graph"""
        workflow = StateGraph(TinkerState)
        
        # Add nodes
        workflow.add_node("task_analyzer", self.nodes.task_analyzer_node)
        workflow.add_node("tool_executor", self.nodes.tool_executor_node)
        workflow.add_node("checkpoint_manager", self.nodes.checkpoint_manager_node)
        
        # Define edges
        workflow.set_entry_point("task_analyzer")
        workflow.add_edge("task_analyzer", "tool_executor")
        workflow.add_edge("tool_executor", "checkpoint_manager")
        workflow.add_edge("checkpoint_manager", END)
        
        # Compile with checkpointing
        return workflow.compile(
            checkpointer=self.checkpoint_manager.checkpointer,
            interrupt_before=["tool_executor"]  # Allow interruption before tool execution
        )
    
    def execute_task(self, task_content: str, thread_id: Optional[str] = None) -> TinkerState:
        """Execute a task using the LangGraph workflow"""
        if not thread_id:
            import uuid
            thread_id = str(uuid.uuid4())
        
        initial_state = TinkerState(
            task_content=task_content,
            conversation_history=[],
            tool_results=[],
            current_directory="/workspace",
            resumption_point=None,
            thread_id=thread_id,
            checkpoint_id=None,
            execution_status="running"
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(initial_state, config=config)
        return result
    
    def resume_task(self, thread_id: str, checkpoint_id: Optional[str] = None) -> TinkerState:
        """Resume a task from a checkpoint"""
        config = {"configurable": {"thread_id": thread_id}}
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id
        
        # Resume from last checkpoint
        result = self.graph.invoke(None, config=config)
        return result
```

**Success Criteria**:
- Graph executes tasks using existing tool infrastructure
- Checkpoints created at appropriate intervals
- Resumption works from any checkpoint

### Task 5.1.6: CLI Integration

**Objective**: Add `--langgraph` flag to enable new system

**File**: `src/tinker/main.py` (modifications)

**Implementation**:
```python
# Add to argument parser
parser.add_argument(
    "--langgraph", 
    action="store_true",
    help="Use LangGraph-based execution (experimental)"
)

# Add conditional execution logic
if args.langgraph:
    from .langgraph_workflow import TinkerWorkflow
    from .checkpoint_manager import TinkerCheckpointManager
    
    checkpoint_manager = TinkerCheckpointManager()
    workflow = TinkerWorkflow(checkpoint_manager)
    result = workflow.execute_task(task_content)
else:
    # Existing execution path
    pass
```

**Success Criteria**:
- `--langgraph` flag switches to new system
- Default behavior unchanged (backward compatibility)
- Both systems produce equivalent results for basic tasks

### Task 5.1.7: Testing and Validation

**Objective**: Ensure new system works correctly and maintains compatibility

**Files**: 
- `tests/test_langgraph_basic.py`
- `tests/test_checkpoint_manager.py`
- `tests/test_backward_compatibility.py`

**Test Cases**:
1. **Basic Execution Test**
   - Simple task execution with `--langgraph` flag
   - Verify same results as existing system

2. **Checkpoint Creation Test**
   - Task creates checkpoints at expected points
   - Checkpoint data is valid and retrievable

3. **Resume Test**
   - Interrupt task mid-execution
   - Resume from checkpoint successfully

4. **Backward Compatibility Test**
   - All existing functionality works without `--langgraph`
   - No performance regression in default mode

**Success Criteria**:
- All tests pass
- Performance within 10% of existing system
- No regression in existing functionality

## File Structure Changes

```
src/tinker/
├── __init__.py
├── anthropic_tools_manager.py          # Existing
├── docker_manager.py                   # Existing
├── email_manager.py                    # Existing
├── github_manager.py                   # Existing
├── main.py                            # Modified for --langgraph flag
├── tools_manager.py                   # Existing
├── langgraph_state.py                 # New
├── langgraph_nodes.py                 # New
├── langgraph_workflow.py              # New
└── checkpoint_manager.py              # New

tests/
├── test_langgraph_basic.py            # New
├── test_checkpoint_manager.py         # New
└── test_backward_compatibility.py     # New

.tinker/                               # New directory
└── memory.db                          # SQLite database
```

## Migration Considerations

### Backward Compatibility
- All existing commands work unchanged
- Docker integration preserved
- Tool definitions remain the same
- Performance characteristics maintained

### Risk Mitigation
- Parallel implementation reduces integration risk
- Existing system remains default until validation complete
- Rollback possible by removing `--langgraph` flag usage
- Incremental feature migration in subsequent phases

### Performance Expectations
- Slight overhead from LangGraph abstraction (~5-10%)
- Checkpoint operations add minimal latency
- Memory usage increase due to state persistence
- Disk usage for SQLite database storage

## Success Metrics

1. **Functional Parity**
   - All existing tasks execute correctly with `--langgraph`
   - Results match existing system output

2. **Checkpointing Reliability**
   - 100% checkpoint creation success rate
   - 95%+ successful resumption rate
   - No data corruption in SQLite database

3. **Performance**
   - Execution time within 110% of existing system
   - Memory usage increase < 50MB for typical tasks
   - Startup time increase < 2 seconds

4. **Code Quality**
   - All new code covered by tests (>90% coverage)
   - No static analysis warnings
   - Documentation for all public APIs

## Next Steps (Phase 5.2 Preview)

After Phase 5.1 completion:
- Replace simple state persistence with intelligent memory management
- Implement context summarization for long conversations
- Add cross-session learning capabilities
- Enhanced error recovery and retry logic

This foundation will enable the advanced memory and workflow features planned for subsequent phases while maintaining system stability and user experience.

# Phase 6.2: Remove Unused TinkerWorkflow and TinkerState Classes

## Objective
Remove the unused TinkerWorkflow and TinkerState classes along with their associated nodes to simplify the codebase.

## Background
From the Phase 6.1 analysis, we identified that:
- TinkerWorkflow creates nodes (task_analyzer, tool_executor, completion) but is never invoked
- The actual work is delegated to ContinuousAgentWorkflow
- TinkerState is part of this unused system
- TinkerLangGraphNodes contains the node implementations for this unused workflow

## Files to Modify

### 1. Remove TinkerWorkflow (`src/tinker/langgraph_workflow.py`)
- [ ] Delete the entire TinkerWorkflow class
- [ ] Remove any imports that are only used by TinkerWorkflow

### 2. Remove TinkerState (`src/tinker/langgraph_state.py`)
- [ ] Delete the TinkerState TypedDict class
- [ ] Check if this file becomes empty and can be deleted entirely

### 3. Remove TinkerLangGraphNodes (`src/tinker/langgraph_nodes.py`)
- [ ] Delete the entire TinkerLangGraphNodes class
- [ ] This includes removing:
  - `task_analyzer_node`
  - `tool_executor_node`  
  - `completion_node`
- [ ] Check if this file becomes empty and can be deleted entirely

### 4. Update main.py
- [ ] Remove any imports of TinkerWorkflow
- [ ] Remove any instantiation of TinkerWorkflow
- [ ] Verify that only ContinuousAgentWorkflow is being used

### 5. Clean up imports
- [ ] Search for any remaining imports of:
  - `TinkerWorkflow`
  - `TinkerState`
  - `TinkerLangGraphNodes`
- [ ] Remove these imports from all files

## Verification Steps
1. [ ] Ensure the application still runs in interactive mode
2. [ ] Ensure the application still runs with a task argument
3. [ ] Run any existing tests to ensure nothing breaks
4. [ ] Check that ContinuousAgentWorkflow still functions correctly

## Expected Benefits
- Reduced code complexity
- Eliminated confusion between two workflow systems
- Cleaner codebase focused on the actually used ContinuousAgentWorkflow
- Easier maintenance going forward

## Notes
- Keep a careful eye on TinkerCheckpointManager - it should still work with ContinuousAgentWorkflow
- The removal should not affect the continuous reasoning loop functionality
- This is a pure cleanup task - no functionality should change
"""
Tinker LangGraph Workflow - Phase 5.1
Main LangGraph workflow for Tinker task execution
"""

import uuid
from typing import Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .langgraph_state import TinkerState
from .langgraph_nodes import TinkerLangGraphNodes
from .checkpoint_manager import TinkerCheckpointManager


class TinkerWorkflow:
    """Main LangGraph workflow for Tinker task execution"""
    
    def __init__(self, checkpoint_manager: TinkerCheckpointManager):
        self.nodes = TinkerLangGraphNodes()
        self.checkpoint_manager = checkpoint_manager
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the execution graph"""
        workflow = StateGraph(TinkerState)
        
        # Add nodes
        workflow.add_node("task_analyzer", self.nodes.task_analyzer_node)
        workflow.add_node("tool_executor", self.nodes.tool_executor_node)
        workflow.add_node("completion", self.nodes.completion_node)
        
        # Define edges with conditional logic
        workflow.set_entry_point("task_analyzer")
        
        # Conditional edge: only go to tool_executor if tools are planned
        def should_execute_tools(state: TinkerState) -> str:
            """Decide whether to execute tools or skip to completion"""
            planned_tools = state.get("planned_tools", [])
            if planned_tools and len(planned_tools) > 0:
                return "tool_executor"
            else:
                return "completion"
        
        workflow.add_conditional_edges(
            "task_analyzer",
            should_execute_tools,
            {
                "tool_executor": "tool_executor",
                "completion": "completion"
            }
        )
        workflow.add_edge("tool_executor", "completion")
        workflow.add_edge("completion", END)
        
        # Compile with checkpointing
        return workflow.compile(
            checkpointer=self.checkpoint_manager.get_checkpointer()
            # Remove interrupt_before for Phase 5.1 testing
        )
    
    def execute_task(self, task_content: str, thread_id: Optional[str] = None, use_persistent_memory: bool = True) -> TinkerState:
        """Execute a task using the LangGraph workflow"""
        if not thread_id:
            if use_persistent_memory:
                thread_id = self.checkpoint_manager.get_main_thread_id()
            else:
                thread_id = str(uuid.uuid4())
        
        # Create session record
        self.checkpoint_manager.create_session(thread_id, task_content[:100])
        
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}
        
        # Check if this is continuing an existing conversation
        has_existing = self.checkpoint_manager.has_existing_conversation(thread_id)
        
        if has_existing:
            try:
                # Continue from existing conversation
                from langchain_core.messages import HumanMessage
                new_message = HumanMessage(content=task_content)
                
                # Get current state and add new message
                state_snapshot = self.checkpoint_manager.checkpointer.get(config)
                if state_snapshot and state_snapshot.values:
                    current_state = state_snapshot.values.copy()
                    conversation_history = current_state.get("conversation_history", [])
                    conversation_history.append(new_message)
                    current_state["conversation_history"] = conversation_history
                    current_state["task_content"] = task_content
                    current_state["execution_status"] = "running"
                    current_state["tool_results"] = []
                    current_state["planned_tools"] = []
                    
                    result = self.graph.invoke(current_state, config=config)
                else:
                    # Fallback to new conversation
                    result = self._execute_new_conversation(task_content, thread_id, config)
            except Exception as e:
                # Fallback to new conversation on error
                result = self._execute_new_conversation(task_content, thread_id, config)
        else:
            # Start new conversation
            result = self._execute_new_conversation(task_content, thread_id, config)
        
        try:
            self.checkpoint_manager.update_session_access(thread_id)
            return result
        except Exception as e:
            # Handle execution errors
            error_state = TinkerState(
                task_content=task_content,
                conversation_history=[],
                tool_results=[],
                planned_tools=[],
                pending_ai_response=None,
                remaining_output=None,
                current_directory="/workspace",
                resumption_point=f"error: {str(e)}",
                thread_id=thread_id,
                tinker_checkpoint_id=None,
                execution_status="failed"
            )
            return error_state
    
    def _execute_new_conversation(self, task_content: str, thread_id: str, config: dict) -> TinkerState:
        """Execute a new conversation"""
        initial_state = TinkerState(
            task_content=task_content,
            conversation_history=[],
            tool_results=[],
            planned_tools=[],
            pending_ai_response=None,
            remaining_output=None,
            current_directory="/workspace",
            resumption_point=None,
            thread_id=thread_id,
            tinker_checkpoint_id=None,
            execution_status="running"
        )
        
        return self.graph.invoke(initial_state, config=config)
    
    def resume_task(self, thread_id: str, checkpoint_id: Optional[str] = None) -> TinkerState:
        """Resume a task from a checkpoint"""
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id
        
        try:
            # Resume from last checkpoint
            result = self.graph.invoke(None, config=config)
            self.checkpoint_manager.update_session_access(thread_id)
            return result
        except Exception as e:
            # Handle resumption errors
            error_state = TinkerState(
                task_content="",
                conversation_history=[],
                tool_results=[],
                planned_tools=[],
                current_directory="/workspace",
                resumption_point=f"resume_error: {str(e)}",
                thread_id=thread_id,
                tinker_checkpoint_id=checkpoint_id,
                execution_status="failed"
            )
            return error_state
    
    def get_checkpoints(self, thread_id: str):
        """Get available checkpoints for a thread"""
        return self.checkpoint_manager.list_checkpoints_for_thread(thread_id)
    
    def list_sessions(self):
        """List all sessions"""
        return self.checkpoint_manager.list_sessions()

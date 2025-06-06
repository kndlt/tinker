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
    
    def _build_graph(self) -> StateGraph:
        """Build the execution graph"""
        workflow = StateGraph(TinkerState)
        
        # Add nodes
        workflow.add_node("task_analyzer", self.nodes.task_analyzer_node)
        workflow.add_node("tool_executor", self.nodes.tool_executor_node)
        workflow.add_node("completion", self.nodes.completion_node)
        
        # Define edges
        workflow.set_entry_point("task_analyzer")
        workflow.add_edge("task_analyzer", "tool_executor")
        workflow.add_edge("tool_executor", "completion")
        workflow.add_edge("completion", END)
        
        # Compile with checkpointing
        return workflow.compile(
            checkpointer=self.checkpoint_manager.get_checkpointer()
            # Remove interrupt_before for Phase 5.1 testing
        )
    
    def execute_task(self, task_content: str, thread_id: Optional[str] = None) -> TinkerState:
        """Execute a task using the LangGraph workflow"""
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        # Create session record
        self.checkpoint_manager.create_session(thread_id, task_content[:100])
        
        initial_state = TinkerState(
            task_content=task_content,
            conversation_history=[],
            tool_results=[],
            planned_tools=[],
            current_directory="/workspace",
            resumption_point=None,
            thread_id=thread_id,
            tinker_checkpoint_id=None,
            execution_status="running"
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = self.graph.invoke(initial_state, config=config)
            self.checkpoint_manager.update_session_access(thread_id)
            return result
        except Exception as e:
            # Handle execution errors
            error_state = initial_state.copy()
            error_state["execution_status"] = "failed"
            error_state["resumption_point"] = f"error: {str(e)}"
            return error_state
    
    def resume_task(self, thread_id: str, checkpoint_id: Optional[str] = None) -> TinkerState:
        """Resume a task from a checkpoint"""
        config = {"configurable": {"thread_id": thread_id}}
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

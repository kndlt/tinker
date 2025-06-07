"""
Tests for LangGraph Basic Integration - Phase 5.1
"""

import pytest
import uuid
from tinker.langgraph_state import TinkerState
from tinker.langgraph_nodes import TinkerLangGraphNodes
from tinker.checkpoint_manager import TinkerCheckpointManager
from tinker.langgraph_workflow import TinkerWorkflow


class TestLangGraphBasic:
    """Test basic LangGraph functionality"""
    
    def test_tinker_state_creation(self):
        """Test TinkerState can be created with required fields"""
        state = TinkerState(
            task_content="test task",
            conversation_history=[],
            tool_results=[],
            current_directory="/workspace",
            resumption_point=None,
            thread_id=str(uuid.uuid4()),
            tinker_checkpoint_id=None,
            execution_status="running"
        )
        
        assert state["task_content"] == "test task"
        assert state["execution_status"] == "running"
        assert state["current_directory"] == "/workspace"
    
    def test_nodes_initialization(self):
        """Test that LangGraph nodes can be initialized"""
        nodes = TinkerLangGraphNodes()
        assert nodes.tools_manager is not None
    
    def test_task_analyzer_node(self):
        """Test task analyzer node functionality"""
        nodes = TinkerLangGraphNodes()
        
        initial_state = TinkerState(
            task_content="echo 'test'",
            conversation_history=[],
            tool_results=[],
            current_directory="/workspace",
            resumption_point=None,
            thread_id=str(uuid.uuid4()),
            tinker_checkpoint_id=None,
            execution_status="running"
        )
        
        result = nodes.task_analyzer_node(initial_state)
        
        assert result["execution_status"] == "analyzing"
        assert result["resumption_point"] == "task_analyzed"
        assert len(result["conversation_history"]) == 1
        assert result["tinker_checkpoint_id"] is not None
    
    def test_tool_executor_node(self):
        """Test tool executor node functionality"""
        nodes = TinkerLangGraphNodes()
        
        initial_state = TinkerState(
            task_content="echo 'test'",
            conversation_history=[],
            tool_results=[],
            current_directory="/workspace",
            resumption_point="task_analyzed",
            thread_id=str(uuid.uuid4()),
            tinker_checkpoint_id=str(uuid.uuid4()),
            execution_status="analyzing"
        )
        
        result = nodes.tool_executor_node(initial_state)
        
        assert result["execution_status"] == "executing"
        assert result["resumption_point"] == "tools_executed"
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["tool_name"] == "execute_shell_command"
    
    def test_completion_node(self):
        """Test completion node functionality"""
        nodes = TinkerLangGraphNodes()
        
        initial_state = TinkerState(
            task_content="echo 'test'",
            conversation_history=[],
            tool_results=[{"tool_name": "test", "result": {"success": True}}],
            current_directory="/workspace",
            resumption_point="tools_executed",
            thread_id=str(uuid.uuid4()),
            tinker_checkpoint_id=str(uuid.uuid4()),
            execution_status="executing"
        )
        
        result = nodes.completion_node(initial_state)
        
        assert result["execution_status"] == "completed"
        assert result["resumption_point"] == "completed"
        assert len(result["conversation_history"]) == 1
    
    def test_checkpoint_manager_initialization(self):
        """Test that checkpoint manager can be initialized"""
        manager = TinkerCheckpointManager()
        assert manager.checkpointer is not None
        assert manager.db_path.endswith("memory.db")
    
    def test_workflow_creation(self):
        """Test that workflow can be created and compiled"""
        checkpoint_manager = TinkerCheckpointManager()
        workflow = TinkerWorkflow(checkpoint_manager)
        assert workflow.graph is not None
        assert workflow.nodes is not None


class TestLangGraphIntegration:
    """Test LangGraph workflow integration"""
    
    def test_execute_simple_task(self):
        """Test executing a simple task through the workflow"""
        checkpoint_manager = TinkerCheckpointManager()
        workflow = TinkerWorkflow(checkpoint_manager)
        
        result = workflow.execute_task("echo 'Hello from test'")
        
        assert result["execution_status"] == "completed"
        assert result["thread_id"] is not None
        assert len(result["tool_results"]) == 1
        assert len(result["conversation_history"]) >= 2  # At least human + AI messages
    
    def test_session_management(self):
        """Test session creation and tracking"""
        checkpoint_manager = TinkerCheckpointManager()
        workflow = TinkerWorkflow(checkpoint_manager)
        
        thread_id = str(uuid.uuid4())
        result = workflow.execute_task("test task", thread_id=thread_id)
        
        assert result["thread_id"] == thread_id
        
        # Check that session was created
        sessions = workflow.list_sessions()
        session_ids = [s["thread_id"] for s in sessions]
        assert thread_id in session_ids


if __name__ == "__main__":
    pytest.main([__file__])

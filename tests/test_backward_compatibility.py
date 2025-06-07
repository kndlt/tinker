"""
Tests for Backward Compatibility - Phase 5.1
"""

import pytest
import tempfile
from unittest.mock import patch, MagicMock
from tinker.main import process_task_langgraph


class TestBackwardCompatibility:
    """Test that existing functionality is preserved"""
    
    @patch('tinker.main.docker_manager')
    @patch('tinker.main.anthropic.Anthropic')
    def test_existing_cli_still_works(self, mock_anthropic, mock_docker):
        """Test that CLI without --langgraph flag still works"""
        # This is a basic test that the main imports don't break
        # Full CLI testing would require more complex mocking
        
        from tinker.main import main
        
        # Should be able to import without errors
        assert main is not None
        assert hasattr(main, '__call__')
    
    def test_langgraph_function_exists(self):
        """Test that the LangGraph processing function exists"""
        assert process_task_langgraph is not None
        assert callable(process_task_langgraph)
    
    def test_langgraph_handles_errors_gracefully(self):
        """Test that LangGraph integration handles errors gracefully"""
        # Test with invalid task content
        try:
            process_task_langgraph("")
        except Exception as e:
            # Should not raise unhandled exceptions
            pytest.fail(f"LangGraph should handle errors gracefully, but raised: {e}")
    
    def test_langgraph_import_error_handling(self):
        """Test graceful handling of import errors"""
        # Test with a more realistic scenario - calling the function directly
        # and ensuring it handles missing dependencies gracefully
        
        # This should not crash even if something goes wrong
        try:
            result = process_task_langgraph("test task")
            # Function should complete without throwing unhandled exceptions
        except Exception as e:
            # Only ImportErrors should be caught and handled gracefully
            if "LangGraph dependencies not available" not in str(e):
                pytest.fail(f"Unexpected exception type: {e}")
    
    def test_existing_managers_still_importable(self):
        """Test that existing managers can still be imported"""
        from tinker.anthropic_tools_manager import AnthropicToolsManager
        from tinker.docker_manager import start_container
        from tinker.email_manager import send_email_from_task
        from tinker.github_manager import check_github_cli_status
        
        # Should all be importable
        assert AnthropicToolsManager is not None
        assert start_container is not None
        assert send_email_from_task is not None
        assert check_github_cli_status is not None
    
    def test_new_langgraph_modules_importable(self):
        """Test that new LangGraph modules can be imported"""
        from tinker.langgraph_state import TinkerState
        from tinker.langgraph_nodes import TinkerLangGraphNodes
        from tinker.langgraph_workflow import TinkerWorkflow
        from tinker.checkpoint_manager import TinkerCheckpointManager
        
        # Should all be importable
        assert TinkerState is not None
        assert TinkerLangGraphNodes is not None
        assert TinkerWorkflow is not None
        assert TinkerCheckpointManager is not None


if __name__ == "__main__":
    pytest.main([__file__])

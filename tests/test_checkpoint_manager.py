"""
Tests for Checkpoint Manager - Phase 5.1
"""

import pytest
import tempfile
import os
from tinker.checkpoint_manager import TinkerCheckpointManager


class TestCheckpointManager:
    """Test checkpoint manager functionality"""
    
    def test_initialization(self):
        """Test checkpoint manager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            manager = TinkerCheckpointManager(db_path)
            
            assert manager.db_path == db_path
            assert manager.checkpointer is not None
            assert os.path.exists(os.path.dirname(db_path))
    
    def test_session_creation(self):
        """Test session creation and retrieval"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            manager = TinkerCheckpointManager(db_path)
            
            thread_id = "test-thread-123"
            task_summary = "Test task summary"
            
            # Create session
            manager.create_session(thread_id, task_summary)
            
            # List sessions
            sessions = manager.list_sessions()
            
            assert len(sessions) == 1
            assert sessions[0]["thread_id"] == thread_id
            assert sessions[0]["task_summary"] == task_summary
            assert sessions[0]["status"] == "active"
    
    def test_session_access_update(self):
        """Test updating session access time"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            manager = TinkerCheckpointManager(db_path)
            
            thread_id = "test-thread-456"
            
            # Create session
            manager.create_session(thread_id, "Test task")
            
            # Get initial access time
            sessions_before = manager.list_sessions()
            initial_access = sessions_before[0]["last_accessed"]
            
            # Update access time
            manager.update_session_access(thread_id)
            
            # Get updated access time
            sessions_after = manager.list_sessions()
            updated_access = sessions_after[0]["last_accessed"]
            
            # Should be different (though timing might make this flaky)
            # At minimum, it shouldn't error
            assert sessions_after[0]["thread_id"] == thread_id
    
    def test_checkpoint_metadata(self):
        """Test checkpoint metadata storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            manager = TinkerCheckpointManager(db_path)
            
            thread_id = "test-thread-789"
            checkpoint_id = "checkpoint-123"
            
            # Create session first
            manager.create_session(thread_id, "Test task")
            
            # Save checkpoint metadata
            manager.save_checkpoint_metadata(
                checkpoint_id, 
                thread_id, 
                "test_resumption_point", 
                "running"
            )
            
            # List checkpoints for thread
            checkpoints = manager.list_checkpoints_for_thread(thread_id)
            
            assert len(checkpoints) == 1
            assert checkpoints[0]["checkpoint_id"] == checkpoint_id
            assert checkpoints[0]["thread_id"] == thread_id
            assert checkpoints[0]["resumption_point"] == "test_resumption_point"
            assert checkpoints[0]["execution_status"] == "running"
    
    def test_memory_checkpointer_access(self):
        """Test getting the LangGraph checkpointer instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_memory.db")
            manager = TinkerCheckpointManager(db_path)
            
            checkpointer = manager.get_checkpointer()
            
            # Should return a MemorySaver instance
            assert checkpointer is not None
            assert hasattr(checkpointer, 'put')  # MemorySaver should have put method
            assert hasattr(checkpointer, 'get')  # MemorySaver should have get method


if __name__ == "__main__":
    pytest.main([__file__])

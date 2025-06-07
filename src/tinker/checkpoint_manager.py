"""
Tinker Checkpoint Manager - Phase 5.1
Manages state persistence using SQLite with LangGraph checkpointing
"""

import os
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from langgraph.checkpoint.sqlite import SqliteSaver
from .langgraph_state import TinkerState


class TinkerCheckpointManager:
    """Manages state persistence using SQLite with LangGraph checkpointing"""
    
    def __init__(self, db_path: str = ".tinker/memory.db"):
        self.db_path = db_path
        self._ensure_directory()
        # Use SQLiteSaver for Phase 5.2 - proper persistence!
        # Use direct connection for better compatibility
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(conn)
        self._init_custom_tables()
    
    def _ensure_directory(self):
        """Ensure .tinker directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_custom_tables(self):
        """Initialize custom tables for Tinker-specific metadata"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Create sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tinker_sessions (
                    thread_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    task_summary TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Create checkpoint metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tinker_checkpoints_meta (
                    checkpoint_id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resumption_point TEXT,
                    execution_status TEXT,
                    FOREIGN KEY (thread_id) REFERENCES tinker_sessions(thread_id)
                )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def create_session(self, thread_id: str, task_summary: str = "") -> None:
        """Create a new session record"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tinker_sessions (thread_id, task_summary) VALUES (?, ?)",
                (thread_id, task_summary)
            )
            conn.commit()
        finally:
            conn.close()
    
    def update_session_access(self, thread_id: str) -> None:
        """Update last accessed time for a session"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE tinker_sessions SET last_accessed = CURRENT_TIMESTAMP WHERE thread_id = ?",
                (thread_id,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def save_checkpoint_metadata(self, checkpoint_id: str, thread_id: str, 
                                resumption_point: Optional[str] = None,
                                execution_status: str = "running") -> None:
        """Save checkpoint metadata"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO tinker_checkpoints_meta 
                   (checkpoint_id, thread_id, resumption_point, execution_status) 
                   VALUES (?, ?, ?, ?)""",
                (checkpoint_id, thread_id, resumption_point, execution_status)
            )
            conn.commit()
        finally:
            conn.close()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM tinker_sessions ORDER BY last_accessed DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def list_checkpoints_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """List available checkpoints for a thread"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM tinker_checkpoints_meta WHERE thread_id = ? ORDER BY created_at DESC",
                (thread_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_checkpointer(self) -> SqliteSaver:
        """Get the LangGraph checkpointer instance"""
        return self.checkpointer
    
    def get_main_thread_id(self) -> str:
        """Get or create the main conversation thread ID"""
        return "tinker_main_conversation"
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history from checkpoints"""
        try:
            # Get the latest state from checkpointer
            config = {"configurable": {"thread_id": thread_id}}
            state_snapshot = self.checkpointer.get(config)
            
            if state_snapshot and state_snapshot.values:
                conversation_history = state_snapshot.values.get("conversation_history", [])
                # Convert LangChain messages to dictionaries for easier handling
                history_data = []
                for msg in conversation_history:
                    if hasattr(msg, 'content') and hasattr(msg, '__class__'):
                        history_data.append({
                            'type': msg.__class__.__name__,
                            'content': str(msg.content)
                        })
                return history_data
            return []
        except Exception:
            return []
    
    def has_existing_conversation(self, thread_id: str) -> bool:
        """Check if there's an existing conversation for this thread"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state_snapshot = self.checkpointer.get(config)
            return state_snapshot is not None and state_snapshot.values is not None
        except Exception:
            return False
    
    def clear_memory(self, thread_id: Optional[str] = None) -> bool:
        """Clear conversation memory for a specific thread or all threads"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                if thread_id:
                    # Clear specific thread
                    conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                    conn.execute("DELETE FROM tinker_sessions WHERE thread_id = ?", (thread_id,))
                    conn.execute("DELETE FROM tinker_checkpoints_meta WHERE thread_id = ?", (thread_id,))
                    print(f"🧹 Cleared memory for thread: {thread_id}")
                else:
                    # Clear all memory
                    conn.execute("DELETE FROM checkpoints")
                    conn.execute("DELETE FROM tinker_sessions") 
                    conn.execute("DELETE FROM tinker_checkpoints_meta")
                    print("🧹 Cleared all conversation memory")
                
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            print(f"❌ Failed to clear memory: {e}")
            return False

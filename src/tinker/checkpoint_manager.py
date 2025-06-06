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
from langgraph.checkpoint.memory import MemorySaver
from .langgraph_state import TinkerState


class TinkerCheckpointManager:
    """Manages state persistence using in-memory checkpointing (Phase 5.1)"""
    
    def __init__(self, db_path: str = ".tinker/memory.db"):
        self.db_path = db_path
        self._ensure_directory()
        # Use MemorySaver for Phase 5.1, will upgrade to SQLite in Phase 5.2
        self.checkpointer = MemorySaver()
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
    
    def get_checkpointer(self) -> MemorySaver:
        """Get the LangGraph checkpointer instance"""
        return self.checkpointer

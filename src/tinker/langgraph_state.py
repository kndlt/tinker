"""
Tinker LangGraph State Definition - Phase 5.1
Core state structure for LangGraph workflows
"""

from typing import Dict, List, Any, Optional, TypedDict
from langchain_core.messages import BaseMessage


class TinkerState(TypedDict):
    """Core state structure for Tinker LangGraph workflows"""
    task_content: str
    conversation_history: List[BaseMessage]
    tool_results: List[Dict[str, Any]]
    planned_tools: List[Dict[str, Any]]  # Tools planned by AI for execution
    pending_ai_response: Optional[str]  # AI response to add after tools complete
    current_directory: str
    resumption_point: Optional[str]
    thread_id: Optional[str]
    tinker_checkpoint_id: Optional[str]  # Renamed to avoid LangGraph reserved name
    execution_status: str  # "running", "completed", "failed", "paused"

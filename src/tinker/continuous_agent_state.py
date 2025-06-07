"""
Continuous Agent State for Tinker
Defines the state structure for continuous reasoning loops
"""

from typing import Dict, List, Any, Optional, TypedDict, Literal
from langchain_core.messages import BaseMessage


class ContinuousAgentState(TypedDict):
    """State for continuous agent reasoning loop"""
    # Core conversation
    messages: List[BaseMessage]
    
    # Current reasoning context
    current_goal: str
    iteration_count: int
    max_iterations: int
    
    # Agent's internal state
    working_memory: Dict[str, Any]  # Current understanding
    observations: List[str]  # What has been learned
    planned_actions: List[str]  # Queue of things to try
    
    # Execution state
    last_action: Optional[str]
    last_result: Optional[Dict[str, Any]]
    
    # Loop control
    should_continue: bool
    exit_reason: Optional[str]
    
    # Reasoning phase
    current_phase: Literal["think", "act", "observe", "decide"]
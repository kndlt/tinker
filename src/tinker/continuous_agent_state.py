"""
Extended State Schema for Memory Summarization
Supports LangMem SummarizationNode requirements
"""

from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Dict, Any


class ContinuousAgentState(AgentState):
    """Extended state schema for memory summarization support
    
    Inherits from AgentState which provides the 'messages' field
    and adds context tracking required by SummarizationNode
    """
    context: Dict[str, Any]  # Required for SummarizationNode bookkeeping
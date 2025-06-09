"""
Continuous Agent Workflow for Tinker
Simplified implementation using LangGraph's create_react_agent
"""

from typing import Dict, Any
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately
from .langchain_tools import AVAILABLE_TOOLS
from .constants import ANTHROPIC_MODEL
from .continuous_agent_state import ContinuousAgentState


class ContinuousAgentWorkflow:
    """Simplified workflow using LangGraph's create_react_agent"""
    
    def __init__(self, enable_memory: bool = True):
        # Define available tools
        self.tools = AVAILABLE_TOOLS
        
        # Setup memory components
        if enable_memory:
            # Configure SQLite checkpointer for persistence
            # Use context manager approach for proper resource management
            import sqlite3
            from langgraph.checkpoint.sqlite import SqliteSaver
            
            # Create SQLite connection and checkpointer
            conn = sqlite3.connect("conversations.db", check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            
            # Configure summarization model with optimized settings
            summarization_model = ChatAnthropic(
                model=ANTHROPIC_MODEL,
                max_tokens=256,  # Constrained for efficiency
                temperature=0.1   # Lower temperature for consistent summaries
            )
            
            # Create summarization node with researched optimal parameters
            self.summarization_node = SummarizationNode(
                model=summarization_model,
                max_tokens=512,                    # Final context size limit
                max_tokens_before_summary=768,     # Trigger threshold (1.5x target)
                max_summary_tokens=256,            # Budget for summary content
                token_counter=count_tokens_approximately,
                initial_summary_prompt="Summarize the key points and context from this conversation, focusing on task progress, decisions made, and important context for future interactions.",
                existing_summary_prompt="Update the existing summary with new information, preserving important context while removing redundant details."
            )
        else:
            checkpointer = None
            self.summarization_node = None
        
        # Create the agent using LangGraph prebuilt with memory support
        self.agent = create_react_agent(
            model=f"anthropic:{ANTHROPIC_MODEL}",
            tools=self.tools,
            checkpointer=checkpointer,
            pre_model_hook=self.summarization_node if enable_memory else None,
            state_schema=ContinuousAgentState,
            prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for fluid reasoning"""
        return """You are an AI assistant that can reason through problems and execute commands fluidly.

When solving tasks:
- Think through the problem step by step
- Execute commands during your reasoning as needed  
- Observe results and adapt your approach immediately
- Continue until the task is complete or you determine it cannot be done

Key capabilities:
- Execute shell commands in a persistent Docker environment
- Send email notifications
- Work with files, git, package managers, and development tools
- Handle errors gracefully and try alternative approaches

Guidelines:
- Be efficient but thorough
- Explain your reasoning clearly
- Execute multiple commands in sequence when logical
- Always validate results before proceeding
- Ask for clarification if the task is unclear"""
    
    def run_continuous_task(self, goal: str, thread_id: str = "main", **kwargs) -> Dict[str, Any]:
        """Run a task with fluid reasoning and tool execution
        
        Args:
            goal: The task/goal to accomplish
            thread_id: Thread ID for conversation memory
            **kwargs: Additional arguments for compatibility (e.g., max_iterations)
        
        Returns:
            Dictionary with messages and results
        """
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100
        }
        
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": goal}]},
            config=config
        )
        
        return result
    
    def run_task(self, goal: str, thread_id: str = "main") -> Dict[str, Any]:
        """Alternative method name for compatibility"""
        return self.run_continuous_task(goal, thread_id=thread_id)
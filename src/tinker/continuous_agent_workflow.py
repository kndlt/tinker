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
            
            # Create .tinker directory for app data
            import os
            tinker_dir = os.path.expanduser("~/.tinker")
            os.makedirs(tinker_dir, exist_ok=True)
            
            # Create SQLite connection and checkpointer in .tinker directory
            db_path = os.path.join(tinker_dir, "conversations.db")
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            
            # Configure summarization model with optimized settings
            summarization_model = ChatAnthropic(
                model=ANTHROPIC_MODEL,
                temperature=0.1,   # Lower temperature for consistent summaries
                max_tokens=16384   # 8x original: 2048 * 8
            )
            
            # Create summarization node with researched optimal parameters
            # 8x the recommended values for balanced context handling
            self.summarization_node = SummarizationNode(
                model=summarization_model,
                max_tokens=16384,                   # 8x: 2048 * 8
                max_tokens_before_summary=24576,    # 8x: 3072 * 8  
                max_summary_tokens=4096,            # 8x: 512 * 8
                token_counter=count_tokens_approximately
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
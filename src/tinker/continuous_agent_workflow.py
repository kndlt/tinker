"""
Continuous Agent Workflow for Tinker
Simplified implementation using LangGraph's create_react_agent
"""

from typing import Dict, Any
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .langchain_tools import AVAILABLE_TOOLS
from .constants import ANTHROPIC_MODEL


class ContinuousAgentWorkflow:
    """Simplified workflow using LangGraph's create_react_agent"""
    
    def __init__(self, enable_memory: bool = True):
        # Define available tools
        self.tools = AVAILABLE_TOOLS
        
        # Setup memory if enabled
        checkpointer = MemorySaver() if enable_memory else None
        
        # Create the agent using LangGraph prebuilt
        self.agent = create_react_agent(
            model=f"anthropic:{ANTHROPIC_MODEL}",
            tools=self.tools,
            checkpointer=checkpointer,
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
        config = {"configurable": {"thread_id": thread_id}}
        
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": goal}]},
            config=config
        )
        
        return result
    
    def run_task(self, goal: str, thread_id: str = "main") -> Dict[str, Any]:
        """Alternative method name for compatibility"""
        return self.run_continuous_task(goal, thread_id=thread_id)
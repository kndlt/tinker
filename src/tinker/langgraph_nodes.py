"""
Tinker LangGraph Nodes - Phase 5.1
LangGraph node implementations wrapping existing tools
"""

import uuid
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from .anthropic_tools_manager import AnthropicToolsManager
from .langgraph_state import TinkerState


class TinkerLangGraphNodes:
    """LangGraph node implementations wrapping existing tools"""
    
    def __init__(self):
        self.tools_manager = AnthropicToolsManager()
    
    def task_analyzer_node(self, state: TinkerState) -> TinkerState:
        """Analyze incoming task and prepare for execution"""
        # Add human message to conversation history
        task_message = HumanMessage(content=state["task_content"])
        
        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append(task_message)
        
        # Set execution context
        updated_state = state.copy()
        updated_state["conversation_history"] = conversation_history
        updated_state["execution_status"] = "analyzing"
        updated_state["resumption_point"] = "task_analyzed"
        
        # Generate checkpoint ID if not present
        if not updated_state.get("tinker_checkpoint_id"):
            updated_state["tinker_checkpoint_id"] = str(uuid.uuid4())
        
        return updated_state
    
    def tool_executor_node(self, state: TinkerState) -> TinkerState:
        """Execute tools using existing AnthropicToolsManager"""
        # Extract the command from the task content for simple commands
        task_content = state["task_content"]
        
        # For simple echo commands, extract the command directly
        if task_content.startswith("echo "):
            command = task_content
            reason = "Direct command execution via LangGraph"
        else:
            # For more complex tasks, we'll need to analyze them
            # For now, default to echoing the task content
            command = f"echo 'LangGraph executed: {task_content}'"
            reason = "LangGraph task execution"
        
        # Actually execute the command using the tools manager
        try:
            result = self.tools_manager.execute_tool(
                "execute_shell_command", 
                {"command": command, "reason": reason}
            )
            
            tool_result = {
                "tool_name": "execute_shell_command",
                "input": {
                    "command": command,
                    "reason": reason
                },
                "result": result,
                "timestamp": str(uuid.uuid4())
            }
            
            # Update state with actual tool results
            updated_state = state.copy()
            tool_results = updated_state.get("tool_results", [])
            tool_results.append(tool_result)
            updated_state["tool_results"] = tool_results
            updated_state["execution_status"] = "executing"
            updated_state["resumption_point"] = "tools_executed"
            
            # Add AI response to conversation
            ai_message = AIMessage(content=f"Command executed successfully: {command}")
            conversation_history = updated_state.get("conversation_history", [])
            conversation_history.append(ai_message)
            updated_state["conversation_history"] = conversation_history
            
        except Exception as e:
            # Handle execution errors
            tool_result = {
                "tool_name": "execute_shell_command",
                "input": {
                    "command": command,
                    "reason": reason
                },
                "result": {
                    "success": False,
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e)
                },
                "timestamp": str(uuid.uuid4())
            }
            
            updated_state = state.copy()
            tool_results = updated_state.get("tool_results", [])
            tool_results.append(tool_result)
            updated_state["tool_results"] = tool_results
            updated_state["execution_status"] = "error"
            updated_state["resumption_point"] = f"error_in_execution: {str(e)}"
            
            # Add error message to conversation
            ai_message = AIMessage(content=f"Command execution failed: {str(e)}")
            conversation_history = updated_state.get("conversation_history", [])
            conversation_history.append(ai_message)
            updated_state["conversation_history"] = conversation_history
        
        return updated_state
    
    def completion_node(self, state: TinkerState) -> TinkerState:
        """Mark task as completed and finalize state"""
        updated_state = state.copy()
        updated_state["execution_status"] = "completed"
        updated_state["resumption_point"] = "completed"
        
        # Add completion message
        completion_message = AIMessage(content="Task completed successfully via LangGraph workflow.")
        conversation_history = updated_state.get("conversation_history", [])
        conversation_history.append(completion_message)
        updated_state["conversation_history"] = conversation_history
        
        return updated_state

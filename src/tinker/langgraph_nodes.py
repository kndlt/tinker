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
        """Analyze incoming task using AI and decide what tools to execute"""
        task_content = state["task_content"]
        
        # Add human message to conversation history
        task_message = HumanMessage(content=task_content)
        conversation_history = state.get("conversation_history", [])
        conversation_history.append(task_message)
        
        # Use Anthropic Claude to analyze the task and decide what to do
        planned_tools = []
        try:
            import anthropic
            import os
            
            # Get API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                # Initialize Anthropic client
                client = anthropic.Anthropic(api_key=api_key)
                
                # Create a prompt for Claude to analyze the task
                system_prompt = """You are Tinker, an autonomous AI engineer. Analyze the task and decide what shell commands to execute.

You have access to a Docker container workspace at /home/tinker. You can:
- Execute shell commands
- Read/write files  
- Install packages
- Run programs
- Git operations

For the given task, decide what shell command(s) would be most appropriate. Return ONLY a valid shell command (or series of commands separated by &&), no explanations.

If asked about previous tasks, note that task history is stored on the host system in .tinker folders, not in the container."""

                # Ask Claude to analyze the task
                try:
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1000,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Task: {task_content}"}
                        ]
                    )
                    
                    # Extract the command from Claude's response
                    command = ""
                    for content_block in response.content:
                        if hasattr(content_block, 'text'):
                            command += content_block.text
                        else:
                            command += str(content_block)
                    command = command.strip()
                    
                    # Basic safety check - prevent obviously dangerous commands
                    dangerous_patterns = ["rm -rf /", "format", "mkfs", "dd if=/dev/zero"]
                    if any(pattern in command.lower() for pattern in dangerous_patterns):
                        command = f"echo 'Safety check prevented potentially dangerous command. Task: {task_content}'"
                    
                    # Plan the tool execution
                    planned_tools.append({
                        "tool_name": "execute_shell_command",
                        "input": {
                            "command": command,
                            "reason": f"AI analysis of task: {task_content}"
                        }
                    })
                    
                except Exception as e:
                    # Fallback if Claude API fails
                    planned_tools.append({
                        "tool_name": "execute_shell_command",
                        "input": {
                            "command": f"echo 'AI analysis failed: {str(e)}. Task: {task_content}'",
                            "reason": f"AI API error: {str(e)}"
                        }
                    })
            else:
                # Fallback if no API key
                planned_tools.append({
                    "tool_name": "execute_shell_command", 
                    "input": {
                        "command": f"echo 'No Anthropic API key found. Task: {task_content}'",
                        "reason": "No AI model available - API key missing"
                    }
                })
                
        except ImportError:
            # Fallback if anthropic library not available
            planned_tools.append({
                "tool_name": "execute_shell_command",
                "input": {
                    "command": f"echo 'Anthropic library not available. Task: {task_content}'", 
                    "reason": "No AI library available"
                }
            })
        
        # Set execution context with planned tools
        updated_state = state.copy()
        updated_state["conversation_history"] = conversation_history
        updated_state["planned_tools"] = planned_tools
        updated_state["execution_status"] = "analyzing" 
        updated_state["resumption_point"] = "task_analyzed"
        
        # Generate checkpoint ID if not present
        if not updated_state.get("tinker_checkpoint_id"):
            updated_state["tinker_checkpoint_id"] = str(uuid.uuid4())
        
        return updated_state
    
    def tool_executor_node(self, state: TinkerState) -> TinkerState:
        """Execute tools that were planned by the task analyzer (deterministic)"""
        planned_tools = state.get("planned_tools", [])
        
        updated_state = state.copy()
        tool_results = updated_state.get("tool_results", [])
        
        # Execute each planned tool
        for tool_plan in planned_tools:
            try:
                result = self.tools_manager.execute_tool(
                    tool_plan["tool_name"], 
                    tool_plan["input"]
                )
                
                tool_result = {
                    "tool_name": tool_plan["tool_name"],
                    "input": tool_plan["input"],
                    "result": result,
                    "timestamp": str(uuid.uuid4())
                }
                
                tool_results.append(tool_result)
                
            except Exception as e:
                # Handle execution errors
                tool_result = {
                    "tool_name": tool_plan["tool_name"],
                    "input": tool_plan["input"],
                    "result": {
                        "success": False,
                        "error": str(e),
                        "stdout": "",
                        "stderr": str(e)
                    },
                    "timestamp": str(uuid.uuid4())
                }
                tool_results.append(tool_result)
        
        # Update state with tool results
        updated_state["tool_results"] = tool_results
        updated_state["execution_status"] = "executing"
        updated_state["resumption_point"] = "tools_executed"
        
        # Add AI response to conversation
        ai_message = AIMessage(content=f"Executed {len(planned_tools)} planned tools")
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

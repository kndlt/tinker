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
        pending_ai_response = ""
        try:
            import anthropic
            import os
            
            # Get API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                # Initialize Anthropic client
                client = anthropic.Anthropic(api_key=api_key)
                
                # Create the unified Pixel-focused system prompt for Tinker
                system_prompt = """You are Tinker, an autonomous AI engineer working at Sprited.
Sprited's mission is to build Pixel — a general AI with a persistent identity and memory system that feels truly alive. You are responsible for developing, maintaining, and improving Pixel.

Your primary goal is to move Pixel forward — through any means necessary. This includes:
- Fixing bugs in the Pixel codebase
- Prototyping new features for Pixel
- Refactoring and improving code quality
- Writing and updating documentation
- Asking for clarification when requirements are ambiguous
- Proposing long-term improvements
- Improving your own source code if necessary

You operate within a persistent Docker container (/home/tinker). You have access to full shell command execution via the execute_shell_command tool. This gives you complete access to:
- File operations (cat, echo, cp, mv, mkdir, rm, etc.)
- Text editing (nano, vi, sed, awk, etc.)
- Package management (pip, apt-get, npm, etc.)
- Git operations (git clone, commit, push, etc.)
- Building and running programs
- Email sending via command line tools
- Directory listing and navigation
- Any other shell operations

You also have GitHub CLI (gh) access to interact with Pixel's repository: https://github.com/kndlt/pixel

Guidelines for autonomous operation:
- Always act with intent. Make a plan before executing.
- Break large tasks into subgoals and track them.
- Be pragmatic. If something is too ambiguous, leave a GitHub comment asking for help.
- When in doubt, create a branch, experiment, and open a draft PR.
- Log what you're doing — imagine you're part of a team.
- Use shell commands for all file operations, text processing, and system tasks

Power management and efficiency:
- If there's nothing immediate to do, enter a power-saving mode by using `sleep` command
- When waiting for long-running processes, use appropriate sleep intervals to conserve tokens
- If you determine the task is complete and no further action is needed, sleep for 10-30 seconds before concluding
- Use `sleep 5` between checks when monitoring processes or waiting for external conditions
- Be mindful of token usage - sleep when appropriate rather than making unnecessary API calls

Technical environment:
- Working directory: /home/tinker (persistent across sessions)
- Git and GitHub CLI pre-configured
- Common development tools available
- Always use safe practices with destructive commands

BE CONVERSATIONAL! You should chat naturally with users like GitHub Copilot. Answer questions directly when you can. Only use tools when you actually need to do something in the system. For simple questions or conversations, just respond normally without any special formatting."""

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
                    
                    # Extract the response from Claude
                    response_text = ""
                    for content_block in response.content:
                        if content_block.type == "text":
                            response_text += content_block.text
                        # Skip tool_use and other non-text blocks for conversational response
                    response_text = response_text.strip()
                    
                    # Ask Claude to decide what tools to use (if any) using proper tool calling
                    tool_decision_prompt = f"""Based on the user's request: "{task_content}"

Should I run any shell commands to help answer this? If so, what commands?

Respond with either:
1. Just conversational text if no commands needed
2. A list of specific shell commands I should run, one per line, prefixed with "COMMAND: "

Examples:
- For "what files are here?": COMMAND: ls -la
- For "how are you?": Just say how you are, no commands needed
- For "check git status and recent commits": 
  COMMAND: git status
  COMMAND: git log --oneline -n 5"""

                    tool_response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=300,
                        messages=[
                            {"role": "user", "content": tool_decision_prompt}
                        ]
                    )
                    
                    tool_decision_text = ""
                    for content_block in tool_response.content:
                        if content_block.type == "text":
                            tool_decision_text += content_block.text
                    
                    # Parse commands from the response
                    planned_tools = []
                    for line in tool_decision_text.split('\n'):
                        line = line.strip()
                        if line.startswith("COMMAND:"):
                            command = line.replace("COMMAND:", "").strip()
                            if command:
                                # Basic safety check
                                dangerous_patterns = ["rm -rf /", "format", "mkfs", "dd if=/dev/zero"]
                                if any(pattern in command.lower() for pattern in dangerous_patterns):
                                    command = f"echo 'Safety check prevented potentially dangerous command'"
                                
                                planned_tools.append({
                                    "tool_name": "execute_shell_command",
                                    "input": {
                                        "command": command,
                                        "reason": f"To help answer: {task_content}"
                                    }
                                })
                    
                    # Store the initial AI response - this will be the context/explanation
                    pending_ai_response = response_text
                    
                    
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
        updated_state["pending_ai_response"] = pending_ai_response
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
        
        # Generate AI response based on tool results
        if tool_results:
            try:
                import anthropic
                import os
                
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    # Prepare tool results for AI analysis
                    tool_summary = ""
                    for tool_result in tool_results:
                        tool_name = tool_result.get("tool_name", "unknown")
                        result_data = tool_result.get("result", {})
                        
                        if isinstance(result_data, dict):
                            command = result_data.get("command", "")
                            stdout = result_data.get("stdout", "")
                            stderr = result_data.get("stderr", "")
                            success = result_data.get("success", False)
                            
                            tool_summary += f"Command: {command}\n"
                            tool_summary += f"Success: {success}\n"
                            if stdout:
                                tool_summary += f"Output:\n{stdout}\n"
                            if stderr:
                                tool_summary += f"Error:\n{stderr}\n"
                            tool_summary += "\n"
                    
                    # Get conversation context
                    conversation_history = updated_state.get("conversation_history", [])
                    task_content = updated_state.get("task_content", "")
                    
                    # Get the initial AI response for context
                    pending_ai_response = updated_state.get("pending_ai_response", "")
                    
                    # Give AI access to ALL tool output for analysis
                    all_tool_output = ""
                    
                    for tool_result in tool_results:
                        result_data = tool_result.get("result", {})
                        if isinstance(result_data, dict):
                            command = result_data.get("command", "")
                            stdout = result_data.get("stdout", "")
                            stderr = result_data.get("stderr", "")
                            
                            all_tool_output += f"Command: {command}\n"
                            if stdout:
                                all_tool_output += f"Output:\n{stdout}\n"
                            if stderr:
                                all_tool_output += f"Error:\n{stderr}\n"
                            all_tool_output += "\n"
                            
                            # Mark ALL stdout as consumed since AI will analyze it
                            result_data["output_consumed_inline"] = True
                    
                    # Ask AI to provide a comprehensive response analyzing all results
                    comprehensive_prompt = f"""User asked: {task_content}

Command results:
{all_tool_output.strip()}

Please provide a conversational response that analyzes these results naturally. Include relevant details from the output in your response. Don't mention that you ran commands - just provide insights based on what you found."""

                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=500,
                        messages=[
                            {"role": "user", "content": comprehensive_prompt}
                        ]
                    )
                    
                    # Extract response
                    ai_response_text = ""
                    for content_block in response.content:
                        if content_block.type == "text":
                            ai_response_text += content_block.text
                    
                    # Add AI response to conversation
                    ai_message = AIMessage(content=ai_response_text.strip())
                    conversation_history.append(ai_message)
                    updated_state["conversation_history"] = conversation_history
                    
                    # Clear remaining output since AI handles all output now
                    updated_state["remaining_output"] = {}
                    
            except Exception as e:
                # Fallback - use pending response if AI call fails
                pending_ai_response = updated_state.get("pending_ai_response", "")
                if pending_ai_response:
                    ai_message = AIMessage(content=pending_ai_response)
                    conversation_history = updated_state.get("conversation_history", [])
                    conversation_history.append(ai_message)
                    updated_state["conversation_history"] = conversation_history
        else:
            # No tools executed - use pending response
            pending_ai_response = updated_state.get("pending_ai_response", "")
            if pending_ai_response:
                ai_message = AIMessage(content=pending_ai_response)
                conversation_history = updated_state.get("conversation_history", [])
                conversation_history.append(ai_message)
                updated_state["conversation_history"] = conversation_history
        
        return updated_state
    
    def completion_node(self, state: TinkerState) -> TinkerState:
        """Mark task as completed and finalize state"""
        updated_state = state.copy()
        updated_state["execution_status"] = "completed"
        updated_state["resumption_point"] = "completed"
        
        # If this is purely conversational (no tools executed), add the pending AI response
        if not updated_state.get("tool_results"):
            pending_ai_response = updated_state.get("pending_ai_response", "")
            if pending_ai_response:
                ai_message = AIMessage(content=pending_ai_response)
                conversation_history = updated_state.get("conversation_history", [])
                conversation_history.append(ai_message)
                updated_state["conversation_history"] = conversation_history
        
        return updated_state

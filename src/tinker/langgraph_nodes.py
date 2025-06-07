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
                    
                    # Check if this is purely conversational or if Claude is suggesting actions
                    # Be very conservative - only detect clear action patterns
                    needs_shell_execution = any([
                        "let me check" in response_text.lower(),
                        "i'll check" in response_text.lower(), 
                        "let me run" in response_text.lower(),
                        "i'll run" in response_text.lower(),
                        "let me look" in response_text.lower(),
                        "i'll look" in response_text.lower(),
                        "let me find" in response_text.lower(),
                        "i'll find" in response_text.lower(),
                        "let me search" in response_text.lower(),
                        "i'll search" in response_text.lower(),
                        "let me use" in response_text.lower() and "command" in response_text.lower(),
                        "i'll use" in response_text.lower() and "command" in response_text.lower()
                    ])
                    
                    if needs_shell_execution:
                        # Ask Claude to provide the specific command with clearer context
                        command_prompt = f"""Your previous response suggested you want to perform an action: "{response_text}"

What specific shell command should I execute to accomplish this? Examples:
- To check for a README file: "ls README*" or "find . -name 'README*'"
- To list directory contents: "ls -la"
- To check git status: "git status"

Please provide only the shell command, or respond "NO_COMMAND" if no command is actually needed."""
                        
                        cmd_response = client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=200,
                            messages=[
                                {"role": "user", "content": command_prompt}
                            ]
                        )
                        
                        command = ""
                        for content_block in cmd_response.content:
                            if content_block.type == "text":
                                command += content_block.text
                            # Skip tool_use and other non-text blocks for command extraction
                        command = command.strip()
                        
                        # Check if Claude said no command is needed
                        if "NO_COMMAND" in command.upper() or "no command" in command.lower():
                            planned_tools = []
                        else:
                            # Basic safety check - prevent obviously dangerous commands
                            dangerous_patterns = ["rm -rf /", "format", "mkfs", "dd if=/dev/zero"]
                            if any(pattern in command.lower() for pattern in dangerous_patterns):
                                command = f"echo 'Safety check prevented potentially dangerous command. Task: {task_content}'"
                            
                            # Plan the tool execution
                            planned_tools.append({
                                "tool_name": "execute_shell_command",
                                "input": {
                                    "command": command,
                                    "reason": f"Following up on conversational response about: {task_content}"
                                }
                            })
                    else:
                        # This is purely conversational, no tools needed
                        planned_tools = []
                    
                    # Store the AI response to add AFTER tools complete (if any)
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
                    
                    # Ask AI to respond based on tool results
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=500,
                        messages=[
                            {"role": "user", "content": f"User asked: {task_content}\n\nI executed these commands:\n{tool_summary}\n\nPlease provide a helpful response based on these results. Be conversational and natural."}
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

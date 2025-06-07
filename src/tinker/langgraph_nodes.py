"""
Tinker LangGraph Nodes - Phase 5.1
LangGraph node implementations wrapping existing tools
"""

import uuid
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from .anthropic_tools_manager import AnthropicToolsManager
from .langgraph_state import TinkerState
from .constants import ANTHROPIC_MODEL


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
                
                # Enhanced system prompt for Tinker
                system_prompt = """You are Tinker, an autonomous AI engineering assistant designed to help with software development tasks. You work collaboratively with users to build, maintain, and improve software projects.

Your core capabilities include:
- Code development and bug fixing
- System architecture and design
- Testing and quality assurance
- Documentation and technical writing
- DevOps and deployment tasks
- Code review and optimization

You operate within a persistent Docker container environment with full shell access via the execute_shell_command tool, providing you with:
- Complete file system operations (create, read, edit, delete files)
- Package management and dependency installation
- Git version control operations
- Build and deployment tools
- Email and notification capabilities
- GitHub CLI for repository management

Guidelines for effective operation:
- Always understand the task before acting - ask clarifying questions when needed
- Break complex tasks into manageable steps and track progress
- Use appropriate tools for each task - don't over-engineer simple solutions
- Be safety-conscious with destructive operations
- Maintain clean, readable code following project conventions
- Document your work and reasoning clearly

Communication style:
- Be conversational and helpful like a skilled pair programming partner
- Answer simple questions directly without unnecessary tool usage
- Explain your reasoning when making technical decisions
- Ask for feedback and clarification when requirements are unclear

Technical environment:
- Working directory: /home/tinker (persistent across sessions)
- Pre-configured development tools and CLI utilities
- GitHub CLI available for repository operations
- Standard package managers and build tools installed"""

                # Ask Claude to analyze the task
                try:
                    response = client.messages.create(
                        model=ANTHROPIC_MODEL,
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

Determine if you need to use tools or can respond directly.

Use tools when you need to:
- Read, create, edit, or analyze files
- Execute commands or run programs
- Check system status or gather information
- Perform git operations or interact with repositories
- Send emails or notifications

Respond directly (no tools) for:
- Answering conceptual or theoretical questions
- Providing explanations of existing code you can see
- Discussing best practices or design patterns
- General conversation or clarification requests

Examples:
- "What does this function do?" → Direct response (if code is visible)
- "Create a new Python file" → COMMAND: touch new_file.py
- "How do I implement OAuth?" → Direct response with explanation
- "Run the tests" → COMMAND: python -m pytest
- "What's the difference between REST and GraphQL?" → Direct response
- "Check if the server is running" → COMMAND: ps aux | grep server

Choose the most efficient approach - prefer direct responses when possible, use tools when necessary.

Respond with either:
1. Just conversational text if no commands needed
2. A list of specific shell commands I should run, one per line, prefixed with "COMMAND: """

                    tool_response = client.messages.create(
                        model=ANTHROPIC_MODEL,
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

Analyze the tool execution results and provide a clear, contextual response to the user.

Focus areas for analysis:
- Success/failure status and any error conditions
- Key information that addresses the user's request
- Unexpected results that need explanation
- Next steps or follow-up actions needed

Response guidelines:
- Summarize the most relevant findings first
- Include specific details when they're important for understanding
- Explain any errors in user-friendly terms
- Filter out routine/expected output unless specifically relevant
- Suggest concrete next steps when appropriate

For different result types:
- File operations: Confirm success and highlight important content
- Command execution: Focus on meaningful output and any errors
- Code execution: Explain results and any issues encountered
- System queries: Present information in organized, useful format

Keep responses concise but informative - users need actionable insights, not raw data dumps."""

                    response = client.messages.create(
                        model=ANTHROPIC_MODEL,
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

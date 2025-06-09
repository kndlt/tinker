"""
LangChain Tool Definitions for Tinker
Converts existing tools to LangChain format for use with create_react_agent
"""

from langchain_core.tools import tool
from typing import Dict, Any
from .anthropic_tools_manager import AnthropicToolsManager
from .email_manager import send_email_from_task


@tool
def execute_shell_command(command: str, reason: str = "") -> Dict[str, Any]:
    """Execute a shell command in the Docker environment.
    
    Args:
        command: The shell command to execute (e.g., 'ls -la', 'git status')
        reason: Brief explanation of why this command is needed
    
    Returns:
        Dictionary with command result, stdout, stderr, and success status
    """
    tools_manager = AnthropicToolsManager()
    return tools_manager.execute_tool("execute_shell_command", {
        "command": command,
        "reason": reason
    })


@tool 
def send_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an email notification.
    
    Args:
        to_email: Email recipient address
        subject: Email subject line
        body: Email body content
    
    Returns:
        Dictionary with send result and status
    """
    try:
        result = send_email_from_task(to_email, subject, body)
        return {
            "success": True,
            "message": "Email sent successfully",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send email: {e}"
        }


# List of all available tools
AVAILABLE_TOOLS = [
    execute_shell_command,
    send_email
]
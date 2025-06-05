"""
Tinker Anthropic Tools Manager - Phase 3.2
Implements Anthropic Claude tool calling for container command execution
"""

import json
import os
from typing import Dict, List, Any, Optional
from . import docker_manager
from .email_manager import send_email_from_task


class AnthropicToolsManager:
    """Manages tool definitions and execution for Anthropic Claude tool calling"""
    
    def __init__(self):
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for Anthropic Claude tool calling"""
        return [
            {
                "name": "execute_shell_command",
                "description": "Execute a shell command inside the Docker container. Use this for file operations, running programs, installing packages, git operations, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute (e.g., 'ls -la', 'mkdir project', 'git clone https://github.com/user/repo.git')"
                        },
                        "reason": {
                            "type": "string", 
                            "description": "Brief explanation of why this command is needed for the task"
                        }
                    },
                    "required": ["command", "reason"]
                }
            }
        ]
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools definition for Anthropic API"""
        return self.tools
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function call and return the result"""
        try:
            # Route to appropriate function
            if tool_name == "execute_shell_command":
                return self._execute_shell_command(tool_input)
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {tool_name}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}"
            }
    
    def _execute_shell_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command in the container"""
        command = args.get("command")
        reason = args.get("reason", "No reason provided")
        
        if not command:
            return {"success": False, "error": "command is required"}
        
        try:
            print(f"🔧 Executing: {command}")
            print(f"   Reason: {reason}")
            
            result = docker_manager.exec_in_container(["bash", "-c", command])
            
            return {
                "success": result.returncode == 0,
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "reason": reason
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

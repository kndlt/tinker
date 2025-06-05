"""
Tinker Tools Manager - Phase 3.1
Implements OpenAI Function Calling tools for container command execution
"""

import json
import os
from typing import Dict, List, Any, Optional
from . import docker_manager


class ToolsManager:
    """Manages tool definitions and execution for OpenAI function calling"""
    
    def __init__(self):
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for OpenAI function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "execute_shell_command",
                    "description": "Execute a shell command with full user shell access. Use this for all operations including file operations, running programs, installing packages, git operations, directory listing, file reading/writing, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute (e.g., 'ls -la', 'mkdir project', 'cat file.txt', 'echo content > file.txt', 'git clone https://github.com/user/repo.git')"
                            },
                            "reason": {
                                "type": "string", 
                                "description": "Brief explanation of why this command is needed for the task"
                            }
                        },
                        "required": ["command", "reason"]
                    }
                }
            }
        ]
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the tools definition for OpenAI API"""
        return self.tools
    
    def execute_tool(self, tool_call) -> Dict[str, Any]:
        """Execute a tool function call and return the result"""
        function_name = tool_call.function.name
        
        try:
            # Parse arguments
            if tool_call.function.arguments:
                arguments = json.loads(tool_call.function.arguments)
            else:
                arguments = {}
            
            # Route to appropriate function
            if function_name == "execute_shell_command":
                return self._execute_shell_command(arguments)
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON arguments: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution error: {str(e)}"
            }
    
    def _execute_shell_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a shell command with full user shell access"""
        command = args.get("command")
        reason = args.get("reason", "No reason provided")
        
        if not command:
            return {"success": False, "error": "Command is required"}
        
        print(f"🤖 AI executing command: {command}")
        print(f"💭 Reason: {reason}")
        
        try:
            # Execute command using existing docker manager
            result = docker_manager.exec_in_container(["bash", "-c", command])
            
            # Display output with formatting
            if result.stdout:
                print("\033[90mOutput:\033[0m")
                for line in result.stdout.splitlines():
                    print(f"\033[90m  {line}\033[0m")
            
            if result.stderr and result.returncode != 0:
                print("\033[91mError output:\033[0m")
                for line in result.stderr.splitlines():
                    print(f"\033[91m  {line}\033[0m")
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "command": command
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

"""
Tinker Tools Manager - Phase 3.1
Implements OpenAI Function Calling tools for container command execution
"""

import json
import os
from typing import Dict, List, Any, Optional
from . import docker_manager
from .email_manager import send_email_from_task


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
                    "description": "Execute a shell command inside the Docker container. Use this for file operations, running programs, installing packages, git operations, etc.",
                    "parameters": {
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
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file from the container filesystem",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read (relative to /home/tinker or absolute)"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file in the container filesystem",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to write (relative to /home/tinker or absolute)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            },
                            "mode": {
                                "type": "string",
                                "description": "Write mode: 'w' to overwrite, 'a' to append",
                                "default": "w"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List contents of a directory in the container",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory_path": {
                                "type": "string",
                                "description": "Path to the directory to list (relative to /home/tinker or absolute)",
                                "default": "."
                            },
                            "show_hidden": {
                                "type": "boolean",
                                "description": "Whether to show hidden files (starting with .)",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send an email using the configured SMTP settings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to_email": {
                                "type": "string",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body content"
                            }
                        },
                        "required": ["to_email", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_directory",
                    "description": "Get the current working directory in the container",
                    "parameters": {
                        "type": "object",
                        "properties": {}
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
            elif function_name == "read_file":
                return self._read_file(arguments)
            elif function_name == "write_file":
                return self._write_file(arguments)
            elif function_name == "list_directory":
                return self._list_directory(arguments)
            elif function_name == "send_email":
                return self._send_email(arguments)
            elif function_name == "get_current_directory":
                return self._get_current_directory(arguments)
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
        """Execute a shell command in the container"""
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
    
    def _read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file from the container"""
        file_path = args.get("file_path")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            result = docker_manager.exec_in_container(["cat", file_path])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "content": result.stdout,
                    "file_path": file_path
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to read file",
                    "file_path": file_path
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def _write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file in the container"""
        file_path = args.get("file_path")
        content = args.get("content")
        mode = args.get("mode", "w")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        if content is None:
            return {"success": False, "error": "content is required"}
        
        try:
            # Escape content for shell
            escaped_content = content.replace("'", "'\"'\"'")
            
            if mode == "a":
                command = f"echo '{escaped_content}' >> '{file_path}'"
            else:
                command = f"echo '{escaped_content}' > '{file_path}'"
            
            result = docker_manager.exec_in_container(["bash", "-c", command])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": file_path,
                    "bytes_written": len(content),
                    "mode": mode
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to write file",
                    "file_path": file_path
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def _list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents in the container"""
        directory_path = args.get("directory_path", ".")
        show_hidden = args.get("show_hidden", False)
        
        try:
            if show_hidden:
                command = ["ls", "-la", directory_path]
            else:
                command = ["ls", "-l", directory_path]
            
            result = docker_manager.exec_in_container(command)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "listing": result.stdout,
                    "directory_path": directory_path
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to list directory",
                    "directory_path": directory_path
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "directory_path": directory_path
            }
    
    def _send_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email using the email manager"""
        to_email = args.get("to_email")
        subject = args.get("subject")
        body = args.get("body")
        
        if not to_email:
            return {"success": False, "error": "to_email is required"}
        if not subject:
            return {"success": False, "error": "subject is required"}
        if not body:
            return {"success": False, "error": "body is required"}
        
        try:
            # Create a task-like content for the email manager
            task_content = f"""Send email to {to_email}

Subject: {subject}

{body}"""
            
            result = send_email_from_task(task_content)
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "to_email": to_email
            }
    
    def _get_current_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current working directory in the container"""
        try:
            result = docker_manager.exec_in_container(["pwd"])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "current_directory": result.stdout.strip()
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to get current directory"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

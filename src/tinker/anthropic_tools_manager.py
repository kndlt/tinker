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
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file from the container filesystem",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read (relative to /home/tinker or absolute)"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file in the container filesystem",
                "input_schema": {
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
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory in the container",
                "input_schema": {
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
            },
            {
                "name": "send_email",
                "description": "Send an email using the configured SMTP settings",
                "input_schema": {
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
            },
            {
                "name": "get_current_directory",
                "description": "Get the current working directory in the container",
                "input_schema": {
                    "type": "object",
                    "properties": {}
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
            elif tool_name == "read_file":
                return self._read_file(tool_input)
            elif tool_name == "write_file":
                return self._write_file(tool_input)
            elif tool_name == "list_directory":
                return self._list_directory(tool_input)
            elif tool_name == "send_email":
                return self._send_email(tool_input)
            elif tool_name == "get_current_directory":
                return self._get_current_directory(tool_input)
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
    
    def _read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file from the container"""
        file_path = args.get("file_path")
        
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        
        try:
            # Use absolute path if it starts with /, otherwise make relative to /home/tinker
            if not file_path.startswith('/'):
                file_path = f"/home/tinker/{file_path}"
            
            result = docker_manager.exec_in_container(["cat", file_path])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": file_path,
                    "content": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to read file: {result.stderr}",
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
        if not content:
            return {"success": False, "error": "content is required"}
        
        try:
            # Use absolute path if it starts with /, otherwise make relative to /home/tinker
            if not file_path.startswith('/'):
                file_path = f"/home/tinker/{file_path}"
            
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(file_path)
            if dir_path != "/home/tinker":
                docker_manager.exec_in_container(["mkdir", "-p", dir_path])
            
            # Write content using shell redirection
            operator = ">>" if mode == "a" else ">"
            escaped_content = content.replace("'", "'\"'\"'")  # Escape single quotes
            
            result = docker_manager.exec_in_container([
                "bash", "-c", f"printf '%s' '{escaped_content}' {operator} '{file_path}'"
            ])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": file_path,
                    "mode": mode,
                    "bytes_written": len(content.encode('utf-8'))
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to write file: {result.stderr}",
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
            # Use absolute path if it starts with /, otherwise make relative to /home/tinker
            if not directory_path.startswith('/'):
                directory_path = f"/home/tinker/{directory_path}"
            
            # Build ls command
            ls_flags = "-la" if show_hidden else "-l"
            result = docker_manager.exec_in_container(["ls", ls_flags, directory_path])
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "directory_path": directory_path,
                    "contents": result.stdout,
                    "show_hidden": show_hidden
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to list directory: {result.stderr}",
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
                    "error": f"Failed to get current directory: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

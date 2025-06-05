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
            # Create a horizontal gradient animation that sweeps through the command text
            import time
            import sys
            
            # ASCII spinner characters for CLI-style animation
            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            
            # Beautiful gradient colors from deep blue to bright cyan
            gradient_colors = [
                "\033[38;5;17m",   # Very deep blue
                "\033[38;5;18m",   # Deep blue
                "\033[38;5;19m",   # Blue
                "\033[38;5;20m",   # Bright blue
                "\033[38;5;21m",   # Cyan blue
                "\033[38;5;27m",   # Blue cyan
                "\033[38;5;33m",   # Bright cyan blue
                "\033[38;5;39m",   # Cyan
                "\033[38;5;45m",   # Bright cyan
                "\033[38;5;51m",   # Light cyan
                "\033[38;5;87m",   # Very light cyan
                "\033[38;5;123m",  # Light blue cyan
            ]
            
            def create_horizontal_gradient(text, offset, gradient_width=8):
                """Create a horizontal gradient effect that moves through the text"""
                colored_text = ""
                text_len = len(text)
                
                for i, char in enumerate(text):
                    # Calculate position in the gradient wave
                    wave_pos = (i - offset) % (text_len + gradient_width)
                    
                    # Determine color based on position in gradient
                    if wave_pos < gradient_width:
                        color_index = int((wave_pos / gradient_width) * (len(gradient_colors) - 1))
                        color_index = max(0, min(color_index, len(gradient_colors) - 1))
                        color = gradient_colors[color_index]
                    else:
                        # Use a dim color for characters outside the gradient wave
                        color = "\033[38;5;240m"  # Dim gray
                    
                    colored_text += f"{color}{char}"
                
                return colored_text + "\033[0m"  # Reset color at the end
            
            # Show horizontal gradient animation
            cycles = 20  # Number of animation cycles
            for i in range(cycles):
                spinner = spinner_chars[i % len(spinner_chars)]
                
                # Create the horizontal gradient effect
                gradient_text = create_horizontal_gradient(command, i * 2)
                
                sys.stdout.write(f"\r{spinner}  {gradient_text}")
                sys.stdout.flush()
                time.sleep(0.08)  # Smooth animation timing
            
            # Final display with bright cyan and completion checkmark
            print(f"\r✓  \033[38;5;51m{command}\033[0m")
            
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

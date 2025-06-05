import os
import time
import random
import shutil
import signal
import atexit
import subprocess
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import anthropic
from dotenv import load_dotenv
from . import docker_manager
from .email_manager import send_email_from_task
from . import github_manager
from .tools_manager import ToolsManager
from .anthropic_tools_manager import AnthropicToolsManager

def is_process_running(pid):
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def acquire_lock(tinker_folder):
    """Acquire a lock file to prevent multiple instances."""
    lock_file = tinker_folder / "tinker.lock"
    current_pid = os.getpid()
    
    if lock_file.exists():
        try:
            # Read existing PID
            existing_pid = int(lock_file.read_text().strip())
            
            # Check if the process is still running
            if is_process_running(existing_pid):
                print(f"⚠️  Another Tinker process is already running (PID: {existing_pid})")
                print("   Do you want to stop the existing process and start a new one?")
                
                while True:
                    response = input("   [y/N]: ").strip().lower()
                    if response in ['y', 'yes']:
                        print(f"🛑 Stopping existing Tinker process (PID: {existing_pid})")
                        try:
                            os.kill(existing_pid, signal.SIGTERM)
                            time.sleep(1)  # Give it a moment to stop gracefully
                            
                            # Check if it's still running
                            if is_process_running(existing_pid):
                                print(f"🔨 Force killing process (PID: {existing_pid})")
                                os.kill(existing_pid, signal.SIGKILL)
                                time.sleep(0.5)
                            
                            print(f"✅ Successfully stopped existing process")
                            # Remove the old lock file if it still exists
                            if lock_file.exists():
                                lock_file.unlink()
                            break
                        except (OSError, ProcessLookupError):
                            print(f"🧹 Process {existing_pid} was already stopped")
                            # Remove the stale lock file if it still exists
                            if lock_file.exists():
                                lock_file.unlink()
                            break
                    elif response in ['n', 'no', '']:
                        print("❌ Exiting - existing Tinker process will continue running")
                        return False
                    else:
                        print("   Please enter 'y' for yes or 'n' for no")
            else:
                print(f"🧹 Cleaning up stale lock file (PID {existing_pid} no longer running)")
                if lock_file.exists():
                    lock_file.unlink()
        except (ValueError, FileNotFoundError):
            # Invalid or corrupted lock file
            print("🧹 Cleaning up corrupted lock file")
            if lock_file.exists():
                lock_file.unlink()
    
    # Create new lock file with current PID
    lock_file.write_text(str(current_pid))
    print(f"🔒 Acquired lock (PID: {current_pid})")
    
    # Register cleanup function
    def cleanup_lock():
        if lock_file.exists():
            lock_file.unlink()
            print("🔓 Released lock file")
    
    atexit.register(cleanup_lock)
    
    # Handle interruption signals
    def signal_handler(signum, frame):
        cleanup_lock()
        print(f"\n🛑 Tinker stopped by signal {signum}")
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    return True

def create_tinker_folder():
    """Create .tinker folder structure in current directory if it doesn't exist."""
    tinker_folder = Path.cwd() / ".tinker"
    tinker_folder.mkdir(exist_ok=True)
    
    # Create subdirectories for Phase 2
    (tinker_folder / "tasks").mkdir(exist_ok=True)
    (tinker_folder / "ongoing").mkdir(exist_ok=True)
    (tinker_folder / "done").mkdir(exist_ok=True)
    
    # Create state.md if it doesn't exist
    state_file = tinker_folder / "state.md"
    if not state_file.exists():
        state_file.write_text("# Tinker State\n\n*Waiting for tasks...*\n")
    
    print(f"Created/verified .tinker folder structure at: {tinker_folder}")
    return tinker_folder

def generate_gibberish():
    """Generate random gibberish text."""
    words = ["beep", "boop", "whirr", "click", "buzz", "hum", "zap", "ping", "tick", "whiz"]
    symbols = ["!", "@", "#", "$", "%", "^", "&", "*", "~", "+"]
    
    gibberish = []
    for _ in range(random.randint(3, 8)):
        if random.choice([True, False]):
            gibberish.append(random.choice(words))
        else:
            gibberish.append(random.choice(symbols))
    
    return " ".join(gibberish)

def update_state(tinker_folder, message):
    """Update the state.md file with current activity."""
    state_file = tinker_folder / "state.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Read current state
    current_state = state_file.read_text() if state_file.exists() else "# Tinker State\n\n"
    
    # Add new entry
    new_entry = f"\n**[{timestamp}]** {message}\n"
    updated_state = current_state + new_entry
    
    # Write back to file
    state_file.write_text(updated_state)

def scan_for_tasks(tinker_folder):
    """Scan for new tasks in the tasks folder."""
    tasks_folder = tinker_folder / "tasks"
    task_files = list(tasks_folder.glob("*.md"))
    return task_files

def process_task(task_file, tinker_folder, client=None, is_single_task=False):
    """Process a single task file through the workflow."""
    task_name = task_file.name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Read task content
        task_content = task_file.read_text()
        
        # Update state
        update_state(tinker_folder, f"🔄 Processing task: {task_name}")
        
        # Move to ongoing folder (only if not processing a single task from external location)
        if not is_single_task:
            ongoing_folder = tinker_folder / "ongoing"
            ongoing_folder.mkdir(exist_ok=True)
            ongoing_file = ongoing_folder / task_name
            shutil.move(str(task_file), str(ongoing_file))
        else:
            # For single tasks, use the original file path
            ongoing_file = task_file
        
        print(f"📋 Processing task: {task_name}")
        print(f"📄 Task content preview:")
        # Show first few lines of the task
        lines = task_content.strip().split('\n')[:5]
        for line in lines:
            if line.strip():  # Only show non-empty lines
                print(f"   {line}")
        if len(task_content.strip().split('\n')) > 5:
            print("   ...")
        
        # Initialize ai_analysis to None
        ai_analysis = None
        tools_result = None
        
        # Phase 3.2: Try Anthropic tools first, then fallback to OpenAI tools
        if client:
            # Check if this is an Anthropic client
            if hasattr(client, 'messages'):
                print(f"\n🚀 Phase 3.2: Processing with Anthropic Claude tools...")
                update_state(tinker_folder, f"🤖 Processing task with Claude: {task_name}")
                
                anthropic_tools_manager = AnthropicToolsManager()
                tools_result = process_task_with_anthropic_tools(task_content, client, anthropic_tools_manager)
            else:
                print(f"\n🚀 Phase 3.1: Processing with OpenAI tools...")
                update_state(tinker_folder, f"🛠️  Processing task with OpenAI tools: {task_name}")
                
                tools_manager = ToolsManager()
                tools_result = process_task_with_tools(task_content, client, tools_manager)
            
            if tools_result and tools_result.get("success"):
                agent_name = tools_result.get("agent", "AI")
                task_result = {
                    "completed": True,
                    "tools_used": tools_result.get("tools_used", 0),
                    "tool_results": tools_result.get("tool_results", []),
                    "ai_response": tools_result.get("final_response", ""),
                    "errors": [],
                    "commands_executed": [],
                    "emails_sent": [],
                    "agent": agent_name
                }
                print(f"✅ Task completed using {task_result['tools_used']} tool calls with {agent_name}")
            else:
                print(f"⚠️  Tools processing failed, falling back to legacy mode...")
                task_result = {"completed": False, "commands_executed": [], "errors": [], "emails_sent": []}
                if tools_result:
                    task_result["errors"].append(tools_result.get("error", "Tools processing failed"))
                # Fall back to Phase 2.x approach
                ai_analysis = analyze_task_with_ai(task_content, client)
        else:
            # No AI client, fall back to Phase 2.x approach
            print(f"\n🤖 No AI client available, using legacy analysis...")
            ai_analysis = analyze_task_with_ai(task_content, client)
            task_result = {"completed": False, "commands_executed": [], "errors": [], "emails_sent": []}
        
        # Legacy Phase 2.x processing (only if tools failed or no AI client)
        if not client or not tools_result or not tools_result.get("success"):
            # Check if this is an email task
            if ai_analysis and ai_analysis.get("is_email", False):
                print(f"\n📧 AI Analysis: This is an email task")
                print(f"💭 Reasoning: {ai_analysis.get('reasoning', 'No reasoning provided')}")
                
                update_state(tinker_folder, f"📧 Processing email task: {task_name}")
                
                # Ask user for approval before sending email
                print(f"\n📧 Tinker wants to send an email:")
                print(f"📋 Task: {task_name}")
                print(f"📄 Email content preview:")
                
                # Show email content preview
                lines = task_content.strip().split('\n')
                for line in lines[:10]:  # Show more lines for email preview
                    if line.strip():
                        print(f"   {line}")
                if len(lines) > 10:
                    print("   ...")
                
                print(f"\n⚠️  This will send a real email.")
                
                while True:
                    response = input("Do you approve sending this email? [y/N]: ").strip().lower()
                    
                    if response in ['y', 'yes']:
                        print("📧 Sending email...")
                        email_result = send_email_from_task(task_content)
                        
                        task_result["emails_sent"].append(email_result)
                        
                        if email_result["success"]:
                            print(f"✅ Email sent successfully to {email_result.get('to', 'recipient')}")
                            update_state(tinker_folder, f"📧 ✅ Email sent to {email_result.get('to', 'recipient')}")
                            task_result["completed"] = True
                        else:
                            print(f"❌ Email failed: {email_result.get('error', 'Unknown error')}")
                            update_state(tinker_folder, f"📧 ❌ Email failed: {email_result.get('error', 'Unknown error')}")
                            task_result["errors"].append(email_result.get('error', 'Email sending failed'))
                            task_result["completed"] = False
                        break
                    elif response in ['n', 'no', '']:
                        print("❌ Email sending rejected by user")
                        task_result["errors"].append("Email sending rejected by user")
                        task_result["completed"] = False
                        break
                    else:
                        print("Please enter 'y' for yes or 'n' for no")
        
        elif ai_analysis and ai_analysis.get("needs_shell", False):
            print(f"\n🤖 AI Analysis: This task requires shell commands")
            print(f"💭 Reasoning: {ai_analysis.get('reasoning', 'No reasoning provided')}")
            
            suggested_commands = ai_analysis.get("suggested_commands", [])
            context = ai_analysis.get("context", "Task execution")
            
            if suggested_commands:
                print(f"\n📋 Suggested commands ({len(suggested_commands)} total):")
                for i, cmd in enumerate(suggested_commands, 1):
                    print(f"   {i}. {cmd}")
                
                update_state(tinker_folder, f"🛠️  Task requires {len(suggested_commands)} shell commands")
                
                # Execute each command with user approval
                for i, command in enumerate(suggested_commands, 1):
                    print(f"\n--- Command {i}/{len(suggested_commands)} ---")
                    
                    approved, final_command = get_user_approval_for_command(
                        command, 
                        f"Step {i} of task '{task_name}': {context}"
                    )
                    
                    if approved:
                        update_state(tinker_folder, f"⚡ Executing: {final_command}")
                        result = execute_shell_command(final_command)
                        
                        task_result["commands_executed"].append({
                            "command": final_command,
                            "success": result["success"],
                            "output": result["stdout"][:500],  # Limit output length
                            "error": result["stderr"][:500] if result["stderr"] else None
                        })
                        
                        if result["success"]:
                            print(f"✅ Command succeeded")
                        else:
                            print(f"❌ Command failed (exit code: {result.get('returncode', 'unknown')})")
                            task_result["errors"].append(result["stderr"])
                            
                            # Ask user if they want to continue or abort
                            continue_choice = input("Command failed. Continue with remaining commands? [y/N]: ").strip().lower()
                            if continue_choice not in ['y', 'yes']:
                                print("🛑 Task execution aborted by user")
                                break
                    else:
                        print(f"⏭️  Skipping command {i}")
                        task_result["errors"].append(f"Command {i} rejected by user")
                
                task_result["completed"] = len(task_result["errors"]) == 0
            else:
                print("🤖 AI suggests shell commands are needed but provided no specific commands")
                task_result["completed"] = True
        else:
            print(f"🤖 AI Analysis: This task doesn't require shell commands")
            if ai_analysis:
                print(f"💭 Reasoning: {ai_analysis.get('reasoning', 'No reasoning provided')}")
            task_result["completed"] = True
        
        # Create a detailed completion report
        agent_info = task_result.get("agent", "legacy")
        completion_report = f"""# Task Completion Report

**Task:** {task_name}
**Timestamp:** {timestamp}
**Status:** {'✅ Completed' if task_result['completed'] else '⚠️ Completed with errors'}
**Agent:** {agent_info}

## Original Task Content
{task_content}

## Execution Summary
- Commands executed: {len(task_result['commands_executed'])}
- Emails sent: {len(task_result['emails_sent'])}
- Errors encountered: {len(task_result['errors'])}
- Tools used: {task_result.get('tools_used', 0)}

"""
        
        if task_result["emails_sent"]:
            completion_report += "## Emails Sent\n"
            for i, email_result in enumerate(task_result["emails_sent"], 1):
                status = "✅" if email_result["success"] else "❌"
                to_email = email_result.get("to", "unknown")
                subject = email_result.get("subject", "unknown")
                completion_report += f"{i}. {status} Email to: {to_email}\n"
                completion_report += f"   Subject: {subject}\n"
                if email_result.get("error"):
                    completion_report += f"   Error: {email_result['error']}\n"
                completion_report += "\n"
        
        if task_result["commands_executed"]:
            completion_report += "## Commands Executed\n"
            for i, cmd_result in enumerate(task_result["commands_executed"], 1):
                status = "✅" if cmd_result["success"] else "❌"
                completion_report += f"{i}. {status} `{cmd_result['command']}`\n"
                if cmd_result["output"]:
                    completion_report += f"   Output: {cmd_result['output'][:200]}...\n"
                if cmd_result["error"]:
                    completion_report += f"   Error: {cmd_result['error'][:200]}...\n"
                completion_report += "\n"
        
        if task_result["errors"]:
            completion_report += "## Errors\n"
            for error in task_result["errors"]:
                completion_report += f"- {error}\n"
        
        # Write the completion report and handle file operations
        if not is_single_task:
            # For normal workflow: write to ongoing file and move to done folder
            ongoing_file.write_text(completion_report)
            
            # Move to done folder with timestamp
            done_folder = tinker_folder / "done"
            done_folder.mkdir(exist_ok=True)
            done_filename = f"{timestamp}_{task_name}"
            done_file = done_folder / done_filename
            shutil.move(str(ongoing_file), str(done_file))
            
            # Update state
            status_emoji = "✅" if task_result["completed"] else "⚠️"
            update_state(tinker_folder, f"{status_emoji} Completed task: {task_name} → {done_filename}")
            
            print(f"\n{status_emoji} Task completed: {task_name}")
            print(f"📁 Moved to: done/{done_filename}")
        else:
            # For single task processing: just display the completion report
            status_emoji = "✅" if task_result["completed"] else "⚠️"
            print(f"\n{status_emoji} Task completed: {task_name}")
            print("\n📊 Task Completion Report:")
            print(completion_report)
        
        return task_result["completed"]
        
    except Exception as e:
        update_state(tinker_folder, f"❌ Error processing {task_name}: {str(e)}")
        print(f"❌ Error processing {task_name}: {e}")
        return False

def execute_shell_command(command, timeout=30):
    """Execute a shell command inside the Docker container and return the result."""
    try:
        # Simple, clean command display
        print(f"\033[1;96m$ \033[1;37m{command}\033[0m")
        
        # Always run in bash for shell features (redirects, etc)
        result = docker_manager.exec_in_container(["bash", "-c", command])
        
        # Display output in simple greyed-out format
        if result.stdout:
            for line in result.stdout.splitlines():
                print(f"\033[90m  {line}\033[0m")
        
        if result.stderr:
            for line in result.stderr.splitlines():
                print(f"\033[91m  {line}\033[0m")  # Red for stderr
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def get_user_approval_for_command(command, context=""):
    """Ask user for approval before executing a shell command."""
    print(f"\n\033[93m⚠️  \033[1;37mTinker wants to run:\033[0m \033[1;33m{command}\033[0m")
    print(f"\033[90m   Context: {context}\033[0m")
    
    while True:
        response = input("Approve? [y/N/e(dit)]: ").strip().lower()
        
        if response in ['y', 'yes']:
            return True, command
        elif response in ['n', 'no', '']:
            print("❌ Command rejected by user")
            return False, command
        elif response in ['e', 'edit']:
            new_command = input(f"Enter modified command (original: {command}): ").strip()
            if new_command:
                return True, new_command
            else:
                print("❌ Empty command, rejecting")
                return False, command
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'e' to edit the command")

def analyze_task_with_ai(task_content, client=None):
    """Use OpenAI to analyze a task and suggest shell commands if needed."""
    if not client:
        return None
    
    try:
        prompt = f"""You are Tinker, an autonomous AI agent that helps with development tasks.

Analyze this task and determine what type of task it is:

Task content:
{task_content}

Respond with a JSON object containing:
- "task_type": string ("shell", "email", or "other")
- "needs_shell": boolean (true if shell commands are needed)
- "is_email": boolean (true if this is an email task)
- "suggested_commands": array of strings (shell commands to execute, in order) - only if needs_shell is true
- "reasoning": string (explanation of why these commands are needed or what type of task this is)
- "context": string (brief description of what needs to be done)

Task type detection:
- "email": Tasks that start with "Send email to" or are clearly about sending emails
- "shell": Tasks that require shell commands (creating files/directories, installing packages, running tests, building projects, git operations)
- "other": Planning, documentation, analysis tasks that don't require shell commands or emails

Examples of email tasks:
- "Send email to someone@example.com: Subject: Hello ..."
- "Email john@company.com about the project status"

Examples of shell tasks:
- Creating files/directories
- Installing packages
- Running tests
- Building projects
- Git operations

Examples of other tasks:
- Planning or documentation tasks
- Analysis or research tasks
- Simple text processing that can be done in Python
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that analyzes tasks and categorizes them. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"⚠️  AI analysis failed: {e}")
        return None

def process_task_with_tools(task_content, client, tools_manager):
    """Process a task using OpenAI function calling tools"""
    if not client or not tools_manager:
        return None
    
    try:
        # Create the system prompt for Tinker
        system_prompt = """You are Tinker, an autonomous AI agent that helps with development tasks.

You have access to tools that allow you to:
- Execute shell commands in a Docker container
- Read and write files
- List directory contents
- Send emails
- Get current working directory

When given a task, analyze what needs to be done and use the appropriate tools to complete it.
Be methodical and break down complex tasks into smaller steps.
Always explain what you're doing and why.

The container is a Linux environment with common development tools installed.
Your working directory is /home/tinker which is the user's workspace.

Safety notes:
- Be careful with destructive commands
- Always check if files/directories exist before operating on them
- Use relative paths when possible
- Provide clear explanations for your actions"""

        # Get tools definition
        tools = tools_manager.get_tools()
        
        # Make the initial API call
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please complete this task:\n\n{task_content}"}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=4000,
            temperature=0.3
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please complete this task:\n\n{task_content}"},
            {"role": "assistant", "content": response.choices[0].message.content, "tool_calls": response.choices[0].message.tool_calls}
        ]
        
        # Track results for reporting
        tool_results = []
        total_tools_used = 0
        
        # Process tool calls
        while response.choices[0].message.tool_calls:
            print(f"\n🔧 AI wants to use {len(response.choices[0].message.tool_calls)} tool(s):")
            
            for tool_call in response.choices[0].message.tool_calls:
                total_tools_used += 1
                print(f"  • {tool_call.function.name}")
                
                # Execute the tool
                result = tools_manager.execute_tool(tool_call)
                tool_results.append({
                    "tool_call": tool_call,
                    "result": result
                })
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            
            # Get next response from AI
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=4000,
                    temperature=0.3
                )
                
                # Add the AI's response to messages
                if response.choices[0].message.content:
                    print(f"\n🤖 AI: {response.choices[0].message.content}")
                
                if response.choices[0].message.tool_calls:
                    messages.append({
                        "role": "assistant", 
                        "content": response.choices[0].message.content,
                        "tool_calls": response.choices[0].message.tool_calls
                    })
                else:
                    messages.append({
                        "role": "assistant",
                        "content": response.choices[0].message.content
                    })
                    break
                    
            except Exception as e:
                print(f"⚠️  Error getting AI response: {e}")
                break
        
        # Final response from AI
        if response.choices[0].message.content:
            print(f"\n🎯 Task completed. AI summary:")
            print(f"   {response.choices[0].message.content}")
        
        return {
            "success": True,
            "tools_used": total_tools_used,
            "tool_results": tool_results,
            "final_response": response.choices[0].message.content,
            "messages": messages
        }
        
    except Exception as e:
        print(f"⚠️  Error processing task with tools: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools_used": 0,
            "tool_results": []
        }


def process_task_with_anthropic_tools(task_content, anthropic_client, anthropic_tools_manager):
    """Process a task using Anthropic Claude tool calling"""
    if not anthropic_client or not anthropic_tools_manager:
        return None
    
    try:
        # Create the system prompt for Tinker with Claude
        system_prompt = """You are Tinker, an autonomous AI agent that helps with development tasks.

You have access to tools that allow you to:
- Execute shell commands in a Docker container
- Read and write files
- List directory contents
- Send emails
- Get current working directory

When given a task, analyze what needs to be done and use the appropriate tools to complete it.
Be methodical and break down complex tasks into smaller steps.
Always explain what you're doing and why.

The container is a Linux environment with common development tools installed.
Your working directory is /home/tinker which is the user's workspace.

Safety notes:
- Be careful with destructive commands
- Always check if files/directories exist before operating on them
- Use relative paths when possible
- Provide clear explanations for your actions"""

        # Get tools definition
        tools = anthropic_tools_manager.get_tools()
        
        print(f"\n🤖 Claude analyzing task with {len(tools)} available tools...")
        
        # Make the initial API call
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            system=system_prompt,
            tools=tools,
            messages=[
                {"role": "user", "content": f"Please complete this task:\n\n{task_content}"}
            ]
        )
        
        messages = [
            {"role": "user", "content": f"Please complete this task:\n\n{task_content}"}
        ]
        
        # Track results for reporting
        tool_results = []
        total_tools_used = 0
        
        # Process the response and any tool calls
        while True:
            # Add Claude's response to messages
            if response.content:
                # Find text content
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        text_content = content_block.text
                        break
                
                if text_content:
                    print(f"\n🤖 Claude: {text_content}")
                    messages.append({
                        "role": "assistant", 
                        "content": response.content
                    })
            
            # Check for tool use
            tool_calls = []
            for content_block in response.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    tool_calls.append(content_block)
            
            if not tool_calls:
                break
            
            print(f"\n🔧 Claude wants to use {len(tool_calls)} tool(s):")
            
            # Execute tools and prepare tool results
            tool_results_for_api = []
            for tool_call in tool_calls:
                total_tools_used += 1
                print(f"  • {tool_call.name}")
                
                # Execute the tool
                result = anthropic_tools_manager.execute_tool(tool_call.name, tool_call.input)
                tool_results.append({
                    "tool_call": tool_call,
                    "result": result
                })
                
                # Add tool result in Anthropic format
                tool_results_for_api.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result) if result else ""
                })
            
            # Add tool results message with proper content structure for Anthropic
            # Anthropic expects content to be a list when using tool results
            tool_results_message = {
                "role": "user",
                "content": tool_results_for_api
            }
            messages.append(tool_results_message)  # type: ignore
            
            # Get next response from Claude
            try:
                response = anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    temperature=0.3,
                    system=system_prompt,
                    tools=tools,
                    messages=messages
                )
                    
            except Exception as e:
                print(f"⚠️  Error getting Claude response: {e}")
                break
        
        # Final response from Claude
        final_text = ""
        if response.content:
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    final_text = content_block.text
                    break
        
        if final_text:
            print(f"\n🎯 Task completed. Claude summary:")
            print(f"   {final_text}")
        
        return {
            "success": True,
            "tools_used": total_tools_used,
            "tool_results": tool_results,
            "final_response": final_text,
            "messages": messages,
            "agent": "anthropic"
        }
        
    except Exception as e:
        print(f"⚠️  Error processing task with Claude: {e}")
        return {
            "success": False,
            "error": str(e),
            "tools_used": 0,
            "tool_results": [],
            "agent": "anthropic"
        }

def main():
    """Main entry point for Tinker CLI"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tinker - AI Agent Task Runner")
    parser.add_argument("--single-task", help="Path to a single task file to process")
    parser.add_argument("--ssh-status", action="store_true", help="Check GitHub SSH status")
    parser.add_argument("--ssh-setup", action="store_true", help="Setup GitHub SSH authentication")  
    parser.add_argument("--ssh-reset", action="store_true", help="Reset GitHub SSH keys")
    parser.add_argument("--github-status", action="store_true", help="Check GitHub CLI authentication")
    parser.add_argument("--github-setup", action="store_true", help="Setup GitHub CLI authentication")
    parser.add_argument("--github-issues", help="List GitHub issues for repository (format: owner/repo)")
    parser.add_argument("--github-issue", help="Get specific GitHub issue (format: owner/repo:number)")
    parser.add_argument("--github-search", help="Search GitHub issues (format: owner/repo query)")
    parser.add_argument("--issue-state", default="open", choices=["open", "closed", "all"], help="Issue state filter")
    parser.add_argument("--issue-limit", type=int, default=10, help="Maximum number of issues to return")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Initialize AI clients with priority: Anthropic first, then OpenAI
    anthropic_client = None
    openai_client = None
    agent_type = None
    
    # Try Anthropic first
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        try:
            anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            agent_type = "anthropic"
            print("🤖 Phase 3.2: Using Anthropic Claude as primary AI agent")
        except Exception as e:
            print(f"⚠️  Failed to initialize Anthropic client: {e}")
    
    # Fallback to OpenAI
    if not anthropic_client:
        openai_api_key = os.getenv("OPENAI_API_KEY") 
        if openai_api_key:
            try:
                openai_client = OpenAI(api_key=openai_api_key)
                agent_type = "openai"
                print("🤖 Phase 3.1: Using OpenAI GPT as AI agent (Anthropic not available)")
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI client: {e}")
    
    if not anthropic_client and not openai_client:
        print("❌ No AI client available. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file")
        return
    
    # Handle SSH management commands
    if args.ssh_status:
        docker_manager.check_ssh_status()
        return
    elif args.ssh_setup:
        docker_manager.start_container()
        docker_manager.ensure_github_ssh()
        return
    elif args.ssh_reset:
        docker_manager.start_container()
        docker_manager.reset_ssh_setup()
        return
    
    # Handle GitHub CLI commands
    if args.github_status:
        github_manager.check_github_cli_status()
        return
    elif args.github_setup:
        docker_manager.start_container()
        github_manager.setup_github_cli_auth()
        return
    elif args.github_issues:
        issues = github_manager.list_github_issues(args.github_issues, args.issue_state, args.issue_limit)
        if issues:
            for issue in issues:
                print(f"#{issue['number']}: {issue['title']}")
                print(f"   State: {issue['state']} | Labels: {', '.join(issue.get('labels', []))}")
                print(f"   URL: {issue['url']}")
                print()
        return
    elif args.github_issue:
        repo, issue_num = args.github_issue.split(':')
        issue = github_manager.get_github_issue(repo, int(issue_num))
        if issue:
            print(f"#{issue['number']}: {issue['title']}")
            print(f"State: {issue['state']}")
            print(f"Author: {issue['author']}")
            print(f"Labels: {', '.join(issue.get('labels', []))}")
            print(f"Created: {issue['created_at']}")
            print(f"URL: {issue['url']}")
            print(f"\nBody:\n{issue['body']}")
        return
    elif args.github_search:
        parts = args.github_search.split(' ', 1)
        if len(parts) == 2:
            repo, query = parts
            issues = github_manager.search_github_issues(repo, query, args.issue_state, args.issue_limit)
            if issues:
                for issue in issues:
                    print(f"#{issue['number']}: {issue['title']}")
                    print(f"   State: {issue['state']} | Labels: {', '.join(issue.get('labels', []))}")
                    print(f"   URL: {issue['url']}")
                    print()
        return
    
    # Create tinker folder structure
    tinker_folder = create_tinker_folder()
    
    # Acquire lock to prevent multiple instances
    if not acquire_lock(tinker_folder):
        return
    
    # Start Docker container
    print("🐳 Starting Docker container...")
    docker_manager.start_container()
    
    # Single task mode
    if args.single_task:
        task_file = Path(args.single_task)
        if not task_file.exists():
            print(f"❌ Task file not found: {args.single_task}")
            return
        
        print(f"🎯 Processing single task: {task_file.name}")
        # Use the appropriate client
        client = anthropic_client if anthropic_client else openai_client
        process_task(task_file, tinker_folder, client, is_single_task=True)
        return
    
    # Main loop for continuous task processing
    print(f"🚀 Tinker Phase 3.2 started! Agent: {agent_type}")
    print("👀 Watching for tasks in .tinker/tasks folder...")
    update_state(tinker_folder, f"🚀 Tinker Phase 3.2 started with {agent_type} agent")
    
    try:
        while True:
            # Scan for new tasks
            task_files = scan_for_tasks(tinker_folder)
            
            if task_files:
                print(f"\n📋 Found {len(task_files)} task(s) to process")
                
                for task_file in task_files:
                    # Use the appropriate client
                    client = anthropic_client if anthropic_client else openai_client
                    process_task(task_file, tinker_folder, client)
                
                print(f"✅ Completed processing {len(task_files)} task(s)")
                update_state(tinker_folder, f"✅ Processed {len(task_files)} task(s)")
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Tinker stopped by user")
        update_state(tinker_folder, "🛑 Tinker stopped by user")


if __name__ == "__main__":
    main()

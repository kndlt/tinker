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
from anthropic import Anthropic
from dotenv import load_dotenv
from . import docker_manager
from .email_manager import send_email_from_task
from . import github_manager

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

def process_task(task_file, tinker_folder, client=None, client_type=None):
    """Process a single task file through the workflow."""
    task_name = task_file.name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Read task content
        task_content = task_file.read_text()
        
        # Update state
        update_state(tinker_folder, f"🔄 Processing task: {task_name}")
        
        # Move to ongoing folder
        ongoing_folder = tinker_folder / "ongoing"
        ongoing_file = ongoing_folder / task_name
        shutil.move(str(task_file), str(ongoing_file))
        
        print(f"📋 Processing task: {task_name}")
        print(f"📄 Task content preview:")
        # Show first few lines of the task
        lines = task_content.strip().split('\n')[:5]
        for line in lines:
            if line.strip():  # Only show non-empty lines
                print(f"   {line}")
        if len(task_content.strip().split('\n')) > 5:
            print("   ...")
        
        # Phase 1.3: Analyze task with AI to determine if shell commands are needed
        update_state(tinker_folder, f"🤖 Analyzing task with AI: {task_name}")
        
        ai_analysis = analyze_task_with_ai(task_content, client, client_type)
        
        task_result = {"completed": False, "commands_executed": [], "errors": [], "emails_sent": []}
        
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
                            
                            # Phase 2.7: Analyze the error and suggest fixes
                            print("🔍 Analyzing error...")
                            error_analysis = analyze_command_result(
                                final_command, 
                                result["stdout"], 
                                result["stderr"], 
                                result["returncode"], 
                                client,
                                client_type
                            )
                            
                            if error_analysis and error_analysis.get("is_recoverable", False):
                                print(f"\n🤖 AI Analysis: {error_analysis.get('explanation', 'Unknown error')}")
                                suggested_fix = error_analysis.get("suggested_fix")
                                confidence = error_analysis.get("confidence", 0.0)
                                
                                if suggested_fix and suggested_fix != "manual_intervention":
                                    print(f"💡 Suggested fix (confidence: {confidence:.1f}): {suggested_fix}")
                                    print("\nOptions:")
                                    print("  r) Retry with suggested fix")
                                    print("  s) Skip this command")
                                    print("  a) Abort task")
                                    
                                    while True:
                                        choice = input("Choose [r/s/a]: ").strip().lower()
                                        if choice == 'r':
                                            print(f"🔄 Retrying with: {suggested_fix}")
                                            retry_result = execute_shell_command(suggested_fix)
                                            if retry_result["success"]:
                                                print("✅ Fix succeeded!")
                                                task_result["commands_executed"].append({
                                                    "command": suggested_fix,
                                                    "success": True,
                                                    "output": retry_result["stdout"][:500],
                                                    "error": None
                                                })
                                                break
                                            else:
                                                print("❌ Fix also failed")
                                                print("Options: s) Skip this command, a) Abort task")
                                                choice = input("Choose [s/a]: ").strip().lower()
                                                if choice == 'a':
                                                    print("🛑 Task execution aborted by user")
                                                    break
                                                else:
                                                    print("⏭️ Skipping command")
                                                    break
                                        elif choice == 's':
                                            print("⏭️ Skipping command")
                                            break
                                        elif choice == 'a':
                                            print("🛑 Task execution aborted by user")
                                            break
                                        else:
                                            print("Please enter 'r', 's', or 'a'")
                                    
                                    if choice == 'a':
                                        break
                                else:
                                    print("🔧 Manual intervention needed")
                                    continue_choice = input("Continue with remaining commands? [y/N]: ").strip().lower()
                                    if continue_choice not in ['y', 'yes']:
                                        print("🛑 Task execution aborted by user")
                                        break
                            else:
                                # Fallback to original behavior
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
        completion_report = f"""# Task Completion Report

**Task:** {task_name}
**Timestamp:** {timestamp}
**Status:** {'✅ Completed' if task_result['completed'] else '⚠️ Completed with errors'}

## Original Task Content
{task_content}

## Execution Summary
- Commands executed: {len(task_result['commands_executed'])}
- Emails sent: {len(task_result['emails_sent'])}
- Errors encountered: {len(task_result['errors'])}

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
        
        # Write the completion report to the ongoing file
        ongoing_file.write_text(completion_report)
        
        # Move to done folder with timestamp
        done_folder = tinker_folder / "done"
        done_filename = f"{timestamp}_{task_name}"
        done_file = done_folder / done_filename
        shutil.move(str(ongoing_file), str(done_file))
        
        # Update state
        status_emoji = "✅" if task_result["completed"] else "⚠️"
        update_state(tinker_folder, f"{status_emoji} Completed task: {task_name} → {done_filename}")
        
        print(f"\n{status_emoji} Task completed: {task_name}")
        print(f"📁 Moved to: done/{done_filename}")
        
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

def analyze_task_with_ai(task_content, client=None, client_type=None):
    """Use AI to analyze a task and suggest shell commands if needed."""
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

        if client_type == "anthropic":
            # Use Anthropic Claude
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,
                system="You are a helpful AI assistant that analyzes tasks and categorizes them. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result = json.loads(response.content[0].text)
        else:
            # Use OpenAI GPT-4
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

def analyze_command_result(command, stdout, stderr, returncode, client=None, client_type=None):
    """Analyze a failed command result and suggest fixes."""
    if not client or returncode == 0:
        return None
    
    try:
        prompt = f"""You are Tinker, an AI assistant helping debug failed shell commands.

A command failed and I need your help to understand what went wrong and suggest a fix.

Command that failed: {command}
Exit code: {returncode}
STDOUT: {stdout}
STDERR: {stderr}

Please analyze this failure and respond with a JSON object containing:
- "error_type": string (category like "missing_package", "permission_error", "network_error", "file_not_found", "syntax_error", "unknown")
- "explanation": string (clear explanation of what went wrong)
- "suggested_fix": string (a specific command to fix the issue, or "manual_intervention" if human help is needed)
- "is_recoverable": boolean (true if this can likely be fixed automatically)
- "confidence": number (0.0-1.0, how confident you are in the diagnosis)

Common error patterns to look for:
- Missing packages/dependencies (pip install, apt install, npm install, etc.)
- Permission errors (chmod, sudo, file ownership)
- Network connectivity issues
- File/directory not found
- Syntax errors in commands
- Environment/PATH issues

Focus on practical, specific fixes when possible."""

        if client_type == "anthropic":
            # Use Anthropic Claude
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                temperature=0.3,
                system="You are a helpful AI assistant that analyzes command failures and suggests fixes. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result = json.loads(response.content[0].text)
        else:
            # Use OpenAI GPT-4
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that analyzes command failures and suggests fixes. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
        
        return result
        return result
        
    except Exception as e:
        print(f"⚠️  Error analysis failed: {e}")
        return None

def initialize_ai_client():
    """Initialize AI client with priority: Anthropic (Claude) -> OpenAI (GPT-4)."""
    client = None
    client_type = None
    
    # Try Anthropic first (Claude Sonnet 4)
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        try:
            client = Anthropic(api_key=anthropic_key)
            client_type = "anthropic"
            print("✅ Claude (Anthropic) client initialized - Phase 3.1 enhanced coding capabilities enabled")
            print("   Using claude-3-5-sonnet-20241022 for superior coding performance")
            return client, client_type
        except Exception as e:
            print(f"⚠️  Anthropic client initialization failed: {e}")
            print("   Falling back to OpenAI...")
    
    # Fallback to OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            client_type = "openai"
            print("✅ OpenAI client initialized - GPT-4 capabilities enabled")
            return client, client_type
        except Exception as e:
            print(f"⚠️  OpenAI client initialization failed: {e}")
    
    # No API keys available
    if not anthropic_key and not openai_key:
        print("⚠️  No AI API keys found in environment")
        print("   Add ANTHROPIC_API_KEY (preferred) or OPENAI_API_KEY to .env file")
        print("   AI-powered task analysis will be disabled")
    
    return None, None

def main():
    """Main Tinker CLI"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Tinker - Autonomous AI Agent')
    parser.add_argument('--ssh-status', action='store_true', 
                       help='Check GitHub SSH authentication status')
    parser.add_argument('--ssh-setup', action='store_true', 
                       help='Setup/reset GitHub SSH authentication')
    parser.add_argument('--ssh-reset', action='store_true', 
                       help='Reset and regenerate SSH keys')
    
    # GitHub CLI arguments
    parser.add_argument('--github-status', action='store_true', 
                       help='Check GitHub CLI authentication status')
    parser.add_argument('--github-setup', action='store_true', 
                       help='Setup GitHub CLI authentication')
    parser.add_argument('--github-issues', metavar='REPO', 
                       help='List GitHub issues for a repository (format: owner/repo)')
    parser.add_argument('--github-issue', nargs=2, metavar=('REPO', 'NUMBER'),
                       help='Get specific GitHub issue (format: owner/repo issue_number)')
    parser.add_argument('--github-search', nargs=2, metavar=('REPO', 'QUERY'),
                       help='Search GitHub issues (format: owner/repo "search query")')
    parser.add_argument('--issue-state', choices=['open', 'closed', 'all'], default='open',
                       help='Issue state to filter by (default: open)')
    parser.add_argument('--issue-limit', type=int, default=10,
                       help='Maximum number of issues to return (default: 10)')
    
    args = parser.parse_args()
    
    # Handle SSH-related commands
    if args.ssh_status:
        print("🔍 Checking GitHub SSH Status...")
        docker_manager.ssh_status()
        return
    
    if args.ssh_setup or args.ssh_reset:
        print("🔧 Setting up GitHub SSH Authentication...")
        try:
            docker_manager.start_container()
            if args.ssh_reset:
                docker_manager.ssh_reset()
            else:
                docker_manager.ensure_github_ssh()
        except Exception as e:
            print(f"❌ Failed to setup SSH: {e}")
        return
    
    # Handle GitHub CLI commands
    if args.github_status:
        print("🔍 Checking GitHub CLI Status...")
        docker_manager.start_container()
        github_manager.check_github_cli_status()
        return
    
    if args.github_setup:
        print("🔧 Setting up GitHub CLI Authentication...")
        try:
            docker_manager.start_container()
            github_manager.setup_github_cli_auth()
        except Exception as e:
            print(f"❌ Failed to setup GitHub CLI: {e}")
        return
    
    if args.github_issues:
        print(f"📋 Listing GitHub Issues for {args.github_issues}...")
        try:
            docker_manager.start_container()
            github_manager.list_github_issues(args.github_issues, args.issue_state, args.issue_limit)
        except Exception as e:
            print(f"❌ Failed to list issues: {e}")
        return
    
    if args.github_issue:
        repo, issue_number = args.github_issue
        print(f"📋 Getting GitHub Issue #{issue_number} from {repo}...")
        try:
            docker_manager.start_container()
            github_manager.get_github_issue(repo, issue_number)
        except Exception as e:
            print(f"❌ Failed to get issue: {e}")
        return
    
    if args.github_search:
        repo, query = args.github_search
        print(f"🔍 Searching GitHub Issues in {repo} for '{query}'...")
        try:
            docker_manager.start_container()
            github_manager.search_github_issues(repo, query, args.issue_state, args.issue_limit)
        except Exception as e:
            print(f"❌ Failed to search issues: {e}")
        return
    
    # Start or reuse the persistent Docker container
    try:
        docker_manager.start_container()
        print("[Tinker] Docker sandbox is ready.")
    except Exception as e:
        print(f"[Tinker] Failed to start Docker sandbox: {e}")
        print("[Tinker] Exiting for safety.")
        return
    
    """Main Tinker CLI that runs forever."""
    # Load environment variables from .env file
    load_dotenv()
    
    print("🔧 Tinker - Autonomous AI Agent Starting...")
    print("Building and maintaining Pixel...")
    
    # Create .tinker folder
    tinker_folder = create_tinker_folder()
    
    # Acquire process lock
    if not acquire_lock(tinker_folder):
        print("Exiting due to existing Tinker process.")
        return
    
    # Initialize AI client (Claude or OpenAI)
    client, client_type = initialize_ai_client()
    
    print("\n🚀 Tinker is now running with Phase 3.1 capabilities...")
    print("- 🤖 AI-powered task analysis (Claude Sonnet 4 or GPT-4)")
    print("- 💻 Shell command execution with user approval")
    print("- 📧 Email sending functionality")
    print("- 📋 Detailed task completion reports")
    print("\nScanning for tasks every 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    # Initial state update
    update_state(tinker_folder, "🚀 Tinker Phase 3.1 started - Enhanced AI capabilities with Claude Sonnet 4")
    
    try:
        while True:
            # Scan for new tasks
            tasks = scan_for_tasks(tinker_folder)
            
            if tasks:
                print(f"📋 Found {len(tasks)} task(s) to process:")
                for task_file in tasks:
                    print(f"   • {task_file.name}")
                
                # Process each task
                for task_file in tasks:
                    success = process_task(task_file, tinker_folder, client, client_type)
                    if success:
                        print("   ⏳ Task processing completed...")
                    else:
                        print("   ⚠️  Task completed with issues...")
                    time.sleep(2)  # Brief pause between tasks
                    
            else:
                # No tasks found, generate some activity
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] 🔍 Scanning for tasks... (none found)")
                update_state(tinker_folder, "🔍 Scanned for tasks - none found")
            
            # Wait 5 seconds before next scan
            time.sleep(5)
            
    except KeyboardInterrupt:
        update_state(tinker_folder, "🛑 Tinker stopped by user")
        print("\n\n🛑 Tinker stopped by user")
        print("Goodbye!")

if __name__ == "__main__":
    main()
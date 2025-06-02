import os
import time
import random
import shutil
import signal
import atexit
import subprocess
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from . import docker_manager

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

def process_task(task_file, tinker_folder, client=None):
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
        
        # Phase 3: Analyze task with AI to determine if shell commands are needed
        update_state(tinker_folder, f"🤖 Analyzing task with AI: {task_name}")
        
        ai_analysis = analyze_task_with_ai(task_content, client)
        
        task_result = {"completed": False, "commands_executed": [], "errors": []}
        
        if ai_analysis and ai_analysis.get("needs_shell", False):
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
                            if result["stdout"]:
                                print(f"📤 Output preview: {result['stdout'][:200]}...")
                        else:
                            print(f"❌ Command failed: {result['stderr']}")
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
        completion_report = f"""# Task Completion Report

**Task:** {task_name}
**Timestamp:** {timestamp}
**Status:** {'✅ Completed' if task_result['completed'] else '⚠️ Completed with errors'}

## Original Task Content
{task_content}

## Execution Summary
- Commands executed: {len(task_result['commands_executed'])}
- Errors encountered: {len(task_result['errors'])}

"""
        
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
    """Execute a shell command and return the result."""
    try:
        print(f"🔧 Executing: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'returncode': -1
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
    print(f"\n🤖 Tinker wants to execute a shell command:")
    print(f"📋 Context: {context}")
    print(f"💻 Command: {command}")
    print("\n⚠️  This command will be executed on your system.")
    
    while True:
        response = input("Do you approve this command? [y/N/e(dit)]: ").strip().lower()
        
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

Analyze this task and determine if it requires shell commands to complete:

Task content:
{task_content}

Respond with a JSON object containing:
- "needs_shell": boolean (true if shell commands are needed)
- "suggested_commands": array of strings (shell commands to execute, in order)
- "reasoning": string (explanation of why these commands are needed)
- "context": string (brief description of what each command does)

Only suggest commands that are safe and necessary for the task. Be conservative.

Examples of tasks that need shell commands:
- Creating files/directories
- Installing packages
- Running tests
- Building projects
- Git operations

Examples of tasks that don't need shell commands:
- Planning or documentation tasks
- Analysis or research tasks
- Simple text processing that can be done in Python
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that analyzes tasks and suggests shell commands when needed. Always respond with valid JSON."},
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

def main():
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
    
    # Initialize OpenAI client
    client = None
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found in environment")
            print("   Phase 3 shell command analysis will be disabled")
            print("   Add your OpenAI API key to .env file for full functionality")
        else:
            client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized - Phase 3 shell capabilities enabled")
    except Exception as e:
        print(f"⚠️  OpenAI client initialization failed: {e}")
        print("Continuing without AI analysis...")
    
    print("\n🚀 Tinker is now running with Phase 3 capabilities...")
    print("- 🤖 AI-powered task analysis")
    print("- 💻 Shell command execution with user approval")
    print("- 📋 Detailed task completion reports")
    print("\nScanning for tasks every 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    # Initial state update
    update_state(tinker_folder, "🚀 Tinker Phase 3 started - AI shell capabilities enabled")
    
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
                    success = process_task(task_file, tinker_folder, client)
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
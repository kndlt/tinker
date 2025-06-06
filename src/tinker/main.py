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
from dotenv import load_dotenv
from . import docker_manager
from .email_manager import send_email_from_task
from . import github_manager

def process_task(task_content: str):
    """Process a task using LangGraph workflow"""
    try:
        from .langgraph_workflow import TinkerWorkflow
        from .checkpoint_manager import TinkerCheckpointManager
        
        print("🔗 Using LangGraph execution (Phase 5.1)")
        
        # Initialize LangGraph components
        checkpoint_manager = TinkerCheckpointManager()
        workflow = TinkerWorkflow(checkpoint_manager)
        
        # Execute task
        result = workflow.execute_task(task_content)
        
        # Display results
        print(f"📊 Execution Status: {result['execution_status']}")
        print(f"🆔 Thread ID: {result['thread_id']}")
        print(f"📍 Resumption Point: {result.get('resumption_point', 'N/A')}")
        
        # Check if we have AI responses to display (for NO_TOOL_NEEDED cases)
        conversation_history = result.get('conversation_history', [])
        has_tool_results = bool(result.get('tool_results'))
        
        # Display AI responses for direct answers or reasoning
        ai_responses = []
        for msg in conversation_history:
            if hasattr(msg, 'content') and msg.content:
                # Skip system/user messages, focus on AI responses
                if hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                    # Ensure content is a string before checking
                    content = str(msg.content) if msg.content else ""
                    # Skip generic completion messages
                    if not content.startswith("Task completed successfully"):
                        ai_responses.append(content)
        
        if ai_responses and not has_tool_results:
            # Show direct AI response when no tools were executed
            print("\n💭 AI Response:")
            for response in ai_responses:
                # Format the response nicely
                for line in str(response).split('\n'):
                    if line.strip():
                        print(f"   {line}")
        
        if result.get('tool_results'):
            print("\n🔧 Tool Results:")
            for i, tool_result in enumerate(result['tool_results'], 1):
                print(f"  {i}. {tool_result.get('tool_name', 'Unknown')}:")
                if 'result' in tool_result:
                    tool_output = tool_result['result']
                    if isinstance(tool_output, dict):
                        # Handle structured tool output
                        if 'stdout' in tool_output and tool_output['stdout']:
                            print(f"     Output: {tool_output['stdout'][:200]}{'...' if len(tool_output['stdout']) > 200 else ''}")
                        elif 'output' in tool_output:
                            print(f"     Output: {tool_output['output'][:200]}{'...' if len(tool_output['output']) > 200 else ''}")
                        else:
                            print(f"     Success: {tool_output.get('success', 'Unknown')}")
                        
                        if 'stderr' in tool_output and tool_output['stderr']:
                            print(f"     Error: {tool_output['stderr'][:200]}{'...' if len(tool_output['stderr']) > 200 else ''}")
                    else:
                        print(f"     {str(tool_output)[:200]}{'...' if len(str(tool_output)) > 200 else ''}")
        
        print(f"✅ LangGraph task completed successfully")
        
    except ImportError as e:
        print(f"❌ LangGraph dependencies not available: {e}")
        print("   Please install required packages: poetry install")
    except Exception as e:
        print(f"❌ LangGraph execution failed: {e}")
        print("   Falling back to standard execution would require re-running without --langgraph flag")

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







def main():
    """Main entry point for Tinker CLI"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tinker - AI Agent Task Runner")
    parser.add_argument("--single-task", help="Path to a single task file to process")
    parser.add_argument("--task", help="Task content to process inline (no file required)")
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
        task_content = task_file.read_text()
        process_task(task_content)
        return
    
    # Inline task mode
    if args.task:
        task_content = args.task
        print(f"🎯 Processing inline task")
        process_task(task_content)
        return
    
    # Main loop for continuous task processing
    print(f"🚀 Tinker Phase 5.3 started! Using LangGraph-only execution")
    print("👀 Watching for tasks in .tinker/tasks folder...")
    update_state(tinker_folder, f"🚀 Tinker Phase 5.3 started with LangGraph-only execution")
    
    try:
        while True:
            # Scan for new tasks
            task_files = scan_for_tasks(tinker_folder)
            
            if task_files:
                print(f"\n📋 Found {len(task_files)} task(s) to process")
                
                for task_file in task_files:
                    task_content = task_file.read_text()
                    process_task(task_content)
                
                print(f"✅ Completed processing {len(task_files)} task(s)")
                update_state(tinker_folder, f"✅ Processed {len(task_files)} task(s)")
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Tinker stopped by user")
        update_state(tinker_folder, "🛑 Tinker stopped by user")


if __name__ == "__main__":
    main()

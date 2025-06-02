import os
import time
import random
import shutil
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

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

def process_task(task_file, tinker_folder):
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
        
        # Simulate some work
        update_state(tinker_folder, f"⚙️  Working on task: {task_name}")
        
        # Move to done folder with timestamp
        done_folder = tinker_folder / "done"
        done_filename = f"{timestamp}_{task_name}"
        done_file = done_folder / done_filename
        shutil.move(str(ongoing_file), str(done_file))
        
        # Update state
        update_state(tinker_folder, f"✅ Completed task: {task_name} → {done_filename}")
        
        print(f"✅ Task completed: {task_name}")
        print(f"📁 Moved to: done/{done_filename}")
        
        return True
        
    except Exception as e:
        update_state(tinker_folder, f"❌ Error processing {task_name}: {str(e)}")
        print(f"❌ Error processing {task_name}: {e}")
        return False

def main():
    """Main Tinker CLI that runs forever."""
    # Load environment variables from .env file
    load_dotenv()
    
    print("🔧 Tinker - Autonomous AI Agent Starting...")
    print("Building and maintaining Pixel...")
    
    # Create .tinker folder
    tinker_folder = create_tinker_folder()
    
    # Initialize OpenAI client (though we're not using it for gibberish yet)
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"⚠️  OpenAI client initialization failed: {e}")
        print("Continuing with gibberish generation...")
    
    print("\n🚀 Tinker is now running...")
    print("Scanning for tasks every 5 seconds...")
    print("Press Ctrl+C to stop\n")
    
    # Initial state update
    update_state(tinker_folder, "🚀 Tinker started - scanning for tasks")
    
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
                    success = process_task(task_file, tinker_folder)
                    if success:
                        print("   ⏳ Simulating work...")
                        time.sleep(2)  # Simulate some processing time
                    
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
import argparse
from dotenv import load_dotenv
from . import docker_manager
from .constants import ANTHROPIC_MODEL




def interactive_chat_mode():
    """Interactive chat mode similar to Claude Code"""
    from .langgraph_workflow import TinkerWorkflow
    from .checkpoint_manager import TinkerCheckpointManager
    
    print("🤖 Tinker Interactive Mode - Type 'exit' or 'quit' to stop")
    print("💬 Chat naturally or give tasks directly")
    print(f"🧠 Model: {ANTHROPIC_MODEL}")
    
    # Initialize LangGraph components
    checkpoint_manager = TinkerCheckpointManager()
    workflow = TinkerWorkflow(checkpoint_manager)
    
    # Check for existing conversation
    main_thread_id = checkpoint_manager.get_main_thread_id()
    if checkpoint_manager.has_existing_conversation(main_thread_id):
        print("🧠 Continuing previous conversation...")
    else:
        print("🆕 Starting new conversation...")
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("\n🧪 tinker> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                break
                
            if not user_input:
                continue
                
            # Handle exit commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("👋 Goodbye!")
                break
                
            # Handle memory clearing
            if user_input.lower() in ['clear memory', '/clear', '/memory clear']:
                main_thread_id = checkpoint_manager.get_main_thread_id()
                if checkpoint_manager.clear_memory(main_thread_id):
                    print("🆕 Memory cleared! Starting fresh conversation...")
                continue
                
            # Process all input as continuous reasoning (DEFAULT)
            try:
                print(f"\033[90m🔄 Starting continuous reasoning...\033[0m")
                from .continuous_agent_workflow import ContinuousAgentWorkflow
                continuous_workflow = ContinuousAgentWorkflow()
                result = continuous_workflow.run_continuous_task(user_input, max_iterations=10)
                
                # Display the reasoning process with better formatting
                for msg in result['messages']:
                    if hasattr(msg, 'content'):
                        content = str(msg.content)
                        if "[THINKING]" in content:
                            print(f"\n\033[95m💭 {content.replace('[THINKING] ', '')}\033[0m")
                        elif "[ACTION]" in content:
                            print(f"\033[94m⚡ {content.replace('[ACTION] ', '')}\033[0m")
                        elif "[OBSERVE]" in content:
                            print(f"\033[92m👁️  {content.replace('[OBSERVE] ', '')}\033[0m")
                        elif "[DECIDE]" in content:
                            print(f"\033[93m🎯 {content.replace('[DECIDE] ', '')}\033[0m")
                        elif "[ERROR]" in content:
                            print(f"\033[91m❌ {content.replace('[ERROR] ', '')}\033[0m")
                        elif not content.startswith("Starting continuous") and not content.startswith("Completed after"):
                            print(f"\033[90m{content}\033[0m")
                
                print(f"\n\033[92m✅ Reasoning completed: {result.get('exit_reason', 'Done')}\033[0m")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def single_task_mode(task_content):
    """Process a single task using continuous reasoning"""
    print(f"\033[90m🔄 Processing task with continuous reasoning...\033[0m")
    
    from .continuous_agent_workflow import ContinuousAgentWorkflow
    continuous_workflow = ContinuousAgentWorkflow()
    result = continuous_workflow.run_continuous_task(task_content, max_iterations=10)
    
    # Display the reasoning process
    for msg in result['messages']:
        if hasattr(msg, 'content'):
            content = str(msg.content)
            if "[THINKING]" in content:
                print(f"\n\033[95m💭 {content.replace('[THINKING] ', '')}\033[0m")
            elif "[ACTION]" in content:
                print(f"\033[94m⚡ {content.replace('[ACTION] ', '')}\033[0m")
            elif "[OBSERVE]" in content:
                print(f"\033[92m👁️  {content.replace('[OBSERVE] ', '')}\033[0m")
            elif "[DECIDE]" in content:
                print(f"\033[93m🎯 {content.replace('[DECIDE] ', '')}\033[0m")
            elif "[ERROR]" in content:
                print(f"\033[91m❌ {content.replace('[ERROR] ', '')}\033[0m")
            elif not content.startswith("Starting continuous") and not content.startswith("Completed after"):
                print(f"\033[90m{content}\033[0m")
    
    print(f"\n\033[92m✅ Task completed: {result.get('exit_reason', 'Done')}\033[0m")







def main():
    """Main entry point for Tinker CLI"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tinker - Interactive AI Agent")
    parser.add_argument("task", nargs="?", help="Optional task to process directly")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Start Docker container
    print("🐳 Starting Docker container...")
    docker_manager.start_container()
    
    # If task provided as argument, process it first then continue to chat
    if args.task:
        single_task_mode(args.task)
        print()  # Add some space before starting chat
    
    # Start interactive chat mode (always)
    interactive_chat_mode()


if __name__ == "__main__":
    main()

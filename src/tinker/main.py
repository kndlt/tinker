import argparse
from dotenv import load_dotenv
from . import docker_manager
from .constants import ANTHROPIC_MODEL


def interactive_chat_mode():
    """Interactive chat mode similar to Claude Code"""
    
    print("🤖 Tinker Interactive Mode - Type 'exit' or 'quit' to stop")
    print("💬 Chat naturally or give tasks directly")
    print(f"🧠 Model: {ANTHROPIC_MODEL}")
    
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
                # Since we don't have persistence yet, just acknowledge
                print("🆕 Memory cleared! (Note: No persistence implemented yet)")
                continue
                
            # Process all input as continuous reasoning (DEFAULT)
            try:
                print(f"\033[90m🔄 Starting continuous reasoning...\033[0m")
                from .continuous_agent_workflow import ContinuousAgentWorkflow
                continuous_workflow = ContinuousAgentWorkflow()
                result = continuous_workflow.run_continuous_task(user_input, max_iterations=10)
                
                # Display the conversation messages
                for msg in result.get('messages', []):
                    if hasattr(msg, 'content') and msg.content:
                        # Skip the initial user message (echo)
                        if hasattr(msg, 'type') and msg.type == 'human':
                            continue
                        print(f"\n{msg.content}")
                
                print(f"\n\033[92m✅ Task completed\033[0m")
                        
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
    
    # Display the conversation messages
    for msg in result.get('messages', []):
        if hasattr(msg, 'content') and msg.content:
            # Skip the initial user message (echo)
            if hasattr(msg, 'type') and msg.type == 'human':
                continue
            print(f"\n{msg.content}")
    
    print(f"\n\033[92m✅ Task completed\033[0m")


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

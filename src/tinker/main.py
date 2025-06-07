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
                
            # Handle continuous mode
            if user_input.lower().startswith('/continuous ') or user_input.lower().startswith('/loop '):
                goal = user_input.split(' ', 1)[1] if ' ' in user_input else ""
                if goal:
                    print(f"🔄 Starting continuous reasoning loop for: {goal}")
                    from .continuous_agent_workflow import ContinuousAgentWorkflow
                    continuous_workflow = ContinuousAgentWorkflow()
                    result = continuous_workflow.run_continuous_task(goal, max_iterations=10)
                    
                    # Display the reasoning process
                    for msg in result['messages']:
                        if hasattr(msg, 'content'):
                            content = str(msg.content)
                            if "[THINKING]" in content:
                                print(f"\n💭 {content.replace('[THINKING] ', '')}")
                            elif "[ACTION]" in content:
                                print(f"⚡ {content.replace('[ACTION] ', '')}")
                            elif "[OBSERVE]" in content:
                                print(f"👁️  {content.replace('[OBSERVE] ', '')}")
                            elif "[DECIDE]" in content:
                                print(f"🎯 {content.replace('[DECIDE] ', '')}")
                            elif "[ERROR]" in content:
                                print(f"❌ {content.replace('[ERROR] ', '')}")
                    
                    print(f"\n✅ Loop completed: {result.get('exit_reason', 'Done')}")
                else:
                    print("❌ Please provide a goal. Usage: /continuous <goal>")
                continue
                
            # Process the input as a conversation
            try:
                result = workflow.execute_task(user_input)
                
                # Display AI responses naturally in gray
                conversation_history = result.get('conversation_history', [])
                for msg in conversation_history:
                    if hasattr(msg, 'content') and msg.content:
                        if hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                            content = str(msg.content)
                            if not content.startswith("Task completed successfully") and not content.startswith("Executed"):
                                # Print in gray color
                                print(f"\033[90m{content}\033[0m")
                
                # Display remaining tool output (what wasn't included inline)
                remaining_output = result.get('remaining_output', {})
                if remaining_output:
                    for timestamp, output in remaining_output.items():
                        if output.strip():
                            print(output.strip())
                
                # Don't display tool stdout - it should be handled inline or in remaining_output
                # Only display stderr from tool results
                if result.get('tool_results'):
                    for tool_result in result['tool_results']:
                        tool_output = tool_result.get('result', {})
                        if isinstance(tool_output, dict):
                            # Only show stderr - all stdout should be handled inline or remaining
                            if 'stderr' in tool_output and tool_output['stderr'].strip():
                                print(f"Error: {tool_output['stderr'].strip()}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def single_task_mode(task_content):
    """Process a single task (for backward compatibility)"""
    from .langgraph_workflow import TinkerWorkflow
    from .checkpoint_manager import TinkerCheckpointManager
    
    # Initialize LangGraph components without announcing it
    checkpoint_manager = TinkerCheckpointManager()
    workflow = TinkerWorkflow(checkpoint_manager)
    
    # Execute task with persistent memory
    result = workflow.execute_task(task_content, use_persistent_memory=True)
    
    # Display AI responses naturally
    conversation_history = result.get('conversation_history', [])
    has_tool_results = bool(result.get('tool_results'))
    
    ai_responses = []
    for msg in conversation_history:
        if hasattr(msg, 'content') and msg.content:
            if hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                content = str(msg.content)
                if not content.startswith("Task completed successfully") and not content.startswith("Executed"):
                    ai_responses.append(content)
    
    # Show AI responses conversationally in gray
    for response in ai_responses:
        print(f"\033[90m{response}\033[0m")
    
    # Display remaining tool output (what wasn't included inline)
    remaining_output = result.get('remaining_output', {})
    if remaining_output:
        for output in remaining_output.values():
            if output.strip():
                print(output.strip())
    
    # Don't display tool stdout - it should be handled inline or in remaining_output
    # Only display stderr from tool results
    if result.get('tool_results'):
        for tool_result in result['tool_results']:
            if 'result' in tool_result:
                tool_output = tool_result['result']
                if isinstance(tool_output, dict):
                    # Only show stderr - all stdout should be handled inline or remaining
                    if 'stderr' in tool_output and tool_output['stderr'].strip():
                        print(f"Error: {tool_output['stderr'].strip()}")







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

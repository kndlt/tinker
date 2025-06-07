import argparse
from dotenv import load_dotenv
from . import docker_manager




def interactive_chat_mode():
    """Interactive chat mode similar to Claude Code"""
    from .langgraph_workflow import TinkerWorkflow
    from .checkpoint_manager import TinkerCheckpointManager
    
    print("🤖 Tinker Interactive Mode - Type 'exit' or 'quit' to stop")
    print("💬 Chat naturally or give tasks directly")
    
    # Initialize LangGraph components
    checkpoint_manager = TinkerCheckpointManager()
    workflow = TinkerWorkflow(checkpoint_manager)
    
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
                
            # Process the input as a conversation
            try:
                result = workflow.execute_task(user_input)
                
                # Display AI responses naturally
                conversation_history = result.get('conversation_history', [])
                for msg in conversation_history:
                    if hasattr(msg, 'content') and msg.content:
                        if hasattr(msg, '__class__') and 'AI' in msg.__class__.__name__:
                            content = str(msg.content)
                            if not content.startswith("Task completed successfully") and not content.startswith("Executed"):
                                print(content)
                
                # Display tool output naturally
                if result.get('tool_results'):
                    for tool_result in result['tool_results']:
                        tool_output = tool_result.get('result', {})
                        if isinstance(tool_output, dict):
                            if 'stdout' in tool_output and tool_output['stdout'].strip():
                                print(tool_output['stdout'].strip())
                            elif 'output' in tool_output and tool_output['output'].strip():
                                print(tool_output['output'].strip())
                            
                            if 'stderr' in tool_output and tool_output['stderr'].strip():
                                print(f"Error: {tool_output['stderr'].strip()}")
                        else:
                            output_str = str(tool_output).strip()
                            if output_str:
                                print(output_str)
                        
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
    
    # Execute task
    result = workflow.execute_task(task_content)
    
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
    
    # Show AI responses conversationally
    for response in ai_responses:
        print(response)
    
    # Show tool output naturally, without technical headers
    if result.get('tool_results'):
        for tool_result in result['tool_results']:
            if 'result' in tool_result:
                tool_output = tool_result['result']
                if isinstance(tool_output, dict):
                    if 'stdout' in tool_output and tool_output['stdout'].strip():
                        print(tool_output['stdout'].strip())
                    elif 'output' in tool_output and tool_output['output'].strip():
                        print(tool_output['output'].strip())
                    
                    if 'stderr' in tool_output and tool_output['stderr'].strip():
                        print(f"Error: {tool_output['stderr'].strip()}")
                else:
                    output_str = str(tool_output).strip()
                    if output_str:
                        print(output_str)







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

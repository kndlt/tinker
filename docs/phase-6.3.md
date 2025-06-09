# Phase 6.3: Replace 4-Node Loop with Fluid Reasoning Using LangGraph create_react_agent

## Objective
Replace the rigid 4-node continuous reasoning loop (think → act → observe → decide) with LangGraph's `create_react_agent` to enable fluid reasoning and tool execution in a single, intelligent node.

## Current Problems with 4-Node Approach

From Phase 6.1 analysis, the current system has several issues:

1. **Over-engineered**: 4 separate nodes for what could be one intelligent reasoning loop
2. **Rigid Constraints**: 200 token limit on act_node, mechanical observe_node
3. **Artificial Boundaries**: Forces separation between thinking and acting
4. **Multiple API Calls**: Each loop iteration requires 4 separate LLM calls
5. **Limited Flexibility**: Cannot adapt reasoning flow based on results

## Proposed Solution: LangGraph create_react_agent

### Why create_react_agent is Perfect for Our Use Case

1. **Built-in Fluid Reasoning**: Model naturally interweaves thinking with tool execution
2. **Minimal Code**: Replaces ~400 lines of custom graph logic with ~20 lines
3. **Multiple Tool Calls**: Can execute multiple commands in sequence naturally
4. **Error Handling**: Built-in tool error handling via ToolNode
5. **Memory Support**: Easy integration with checkpointers
6. **LangGraph Native**: Uses official prebuilt components

### Implementation Plan

#### 1. Convert Current Tools to LangChain Tool Format

```python
from langchain_core.tools import tool
from typing import Dict, Any

@tool
def execute_shell_command(command: str, reason: str = "") -> Dict[str, Any]:
    """Execute a shell command in the Docker environment.
    
    Args:
        command: The shell command to execute
        reason: Brief explanation of why this command is needed
    
    Returns:
        Dictionary with command result, stdout, stderr, and success status
    """
    # Use existing AnthropicToolsManager logic
    from .anthropic_tools_manager import AnthropicToolsManager
    tools_manager = AnthropicToolsManager()
    return tools_manager.execute_tool("execute_shell_command", {
        "command": command,
        "reason": reason
    })

@tool
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an email notification.
    
    Args:
        to: Email recipient
        subject: Email subject line
        body: Email body content
    """
    from .email_manager import EmailManager
    email_manager = EmailManager()
    return email_manager.send_email(to, subject, body)

# Add other tools as needed...
```

#### 2. Create Simplified Workflow Class

```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from typing import List, Dict, Any, Optional

class FluidReasoningWorkflow:
    """Simplified workflow using LangGraph's create_react_agent"""
    
    def __init__(self, enable_memory: bool = True):
        # Define available tools
        self.tools = [
            execute_shell_command,
            send_email,
            # Add other tools from current AnthropicToolsManager
        ]
        
        # Create model
        self.model = ChatAnthropic(
            model="claude-3-sonnet-20241022",
            temperature=0
        )
        
        # Setup memory if enabled
        checkpointer = MemorySaver() if enable_memory else None
        
        # Create the agent using LangGraph prebuilt
        self.agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=checkpointer,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for fluid reasoning"""
        return """You are an AI assistant that can reason through problems and execute commands fluidly.

When solving tasks:
- Think through the problem step by step
- Execute commands during your reasoning as needed  
- Observe results and adapt your approach immediately
- Continue until the task is complete or you determine it cannot be done

Key capabilities:
- Execute shell commands in a persistent Docker environment
- Send email notifications
- Work with files, git, package managers, and development tools
- Handle errors gracefully and try alternative approaches

Guidelines:
- Be efficient but thorough
- Explain your reasoning clearly
- Execute multiple commands in sequence when logical
- Always validate results before proceeding
- Ask for clarification if the task is unclear"""
    
    def run_task(self, goal: str, thread_id: str = "main") -> Dict[str, Any]:
        """Run a task with fluid reasoning and tool execution"""
        config = {"configurable": {"thread_id": thread_id}}
        
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": goal}]},
            config=config
        )
        
        return result
    
    def run_with_max_iterations(self, goal: str, max_iterations: int = 10, thread_id: str = "main") -> Dict[str, Any]:
        """Run task with iteration limit (for compatibility with current interface)"""
        # Note: create_react_agent handles this internally
        # We can add custom logic here if needed
        return self.run_task(goal, thread_id)
```

#### 3. Update main.py Integration

```python
def interactive_chat_mode():
    """Interactive chat mode with fluid reasoning"""
    
    print("🤖 Tinker Interactive Mode - Type 'exit' or 'quit' to stop")
    print("💬 Chat naturally or give tasks directly")
    print(f"🧠 Model: {ANTHROPIC_MODEL}")
    
    # Create fluid reasoning workflow
    workflow = FluidReasoningWorkflow(enable_memory=True)
    
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
                # Use new thread ID to start fresh
                import uuid
                thread_id = str(uuid.uuid4())
                print("🆕 Memory cleared! Starting fresh conversation...")
                continue
            
            # Process with fluid reasoning
            try:
                print(f"\033[90m🔄 Processing with fluid reasoning...\033[0m")
                result = workflow.run_task(user_input, thread_id="main")
                
                # Display result (create_react_agent returns standard message format)
                for message in result.get('messages', []):
                    if hasattr(message, 'content') and message.content:
                        print(f"\n{message.content}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def single_task_mode(task_content):
    """Process a single task using fluid reasoning"""
    print(f"\033[90m🔄 Processing task with fluid reasoning...\033[0m")
    
    workflow = FluidReasoningWorkflow(enable_memory=False)  # No memory for single tasks
    result = workflow.run_task(task_content, thread_id=f"task-{uuid.uuid4()}")
    
    # Display result
    for message in result.get('messages', []):
        if hasattr(message, 'content') and message.content:
            print(f"\n{message.content}")
    
    print(f"\n\033[92m✅ Task completed\033[0m")
```

## Benefits of This Approach

### 1. Massive Code Reduction
- **Current**: ~400 lines across workflow + nodes + state
- **New**: ~50 lines total
- **Maintenance**: Much simpler to understand and modify

### 2. Natural Fluid Execution
- No artificial boundaries between thinking and acting
- Can execute multiple commands in sequence naturally
- Adapts reasoning flow based on results

### 3. Better Error Handling
- Built-in tool error handling via LangGraph's ToolNode
- Natural error recovery through continued reasoning
- No need for custom error state management

### 4. Improved Performance
- Single LLM call per reasoning cycle instead of 4
- Reduced latency and API costs
- More efficient token usage

### 5. Enhanced Flexibility
- Can reason about complex multi-step problems
- Adapts strategy based on intermediate results
- No rigid iteration limits or phase constraints

## Migration Steps

1. [ ] Create tool definitions using @tool decorator
2. [ ] Implement FluidReasoningWorkflow class
3. [ ] Update main.py to use new workflow
4. [ ] Test basic functionality with simple tasks
5. [ ] Test complex multi-step tasks
6. [ ] Verify memory functionality works correctly
7. [ ] Remove old continuous_agent_* files
8. [ ] Update any remaining references

## Compatibility Notes

- **Interface**: `run_task(goal, thread_id)` maintains similar interface
- **Memory**: Built-in checkpointer replaces custom memory management
- **Tools**: Same underlying tool execution, just wrapped differently
- **Error Handling**: Improved error handling compared to current system

## Testing Plan

1. **Basic Tasks**: Simple commands like "list files", "check git status"
2. **Multi-step Tasks**: Complex workflows requiring multiple commands
3. **Error Scenarios**: Commands that fail and require recovery
4. **Memory Testing**: Conversation continuity across interactions
5. **Performance Testing**: Compare response times with current system

This approach represents a fundamental simplification while providing more powerful and flexible reasoning capabilities.
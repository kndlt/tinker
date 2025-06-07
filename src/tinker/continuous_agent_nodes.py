"""
Continuous Agent Nodes for Tinker
Implements Think-Act-Observe-Decide loop
"""

import os
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from .continuous_agent_state import ContinuousAgentState
from .anthropic_tools_manager import AnthropicToolsManager
from .constants import ANTHROPIC_MODEL


class ContinuousAgentNodes:
    """Nodes for continuous agent reasoning loop"""
    
    def __init__(self):
        self.tools_manager = AnthropicToolsManager()
    
    def think_node(self, state: ContinuousAgentState) -> ContinuousAgentState:
        """Think about the current goal and plan next steps"""
        try:
            import anthropic
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("No Anthropic API key found")
                
            client = anthropic.Anthropic(api_key=api_key)
            
            # Build context from state
            context = f"""Current Goal: {state['current_goal']}
Iteration: {state['iteration_count']}/{state['max_iterations']}

Working Memory:
{state.get('working_memory', {})}

Recent Observations:
{chr(10).join(state.get('observations', [])[-5:])}  # Last 5 observations

Planned Actions Queue:
{chr(10).join(state.get('planned_actions', []))}

Last Action: {state.get('last_action', 'None')}
Last Result: {state.get('last_result', 'None')}

Think about:
1. What progress have we made toward the goal?
2. What do we still need to learn or do?
3. What should be our next action?

Respond with your reasoning and what specific action to take next (or 'GOAL_ACHIEVED' if done)."""

            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": context}
                ]
            )
            
            reasoning = ""
            for content_block in response.content:
                if content_block.type == "text":
                    reasoning += content_block.text
            
            # Update state with reasoning
            state['messages'].append(AIMessage(content=f"[THINKING] {reasoning}"))
            
            # Check if goal achieved
            if "GOAL_ACHIEVED" in reasoning:
                state['should_continue'] = False
                state['exit_reason'] = "Goal achieved"
            else:
                state['current_phase'] = "act"
                
        except Exception as e:
            state['messages'].append(AIMessage(content=f"[ERROR] Think phase failed: {str(e)}"))
            state['should_continue'] = False
            state['exit_reason'] = f"Error in think phase: {str(e)}"
            
        return state
    
    def act_node(self, state: ContinuousAgentState) -> ContinuousAgentState:
        """Execute actions based on thinking"""
        try:
            import anthropic
            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("No Anthropic API key found")
                
            client = anthropic.Anthropic(api_key=api_key)
            
            # Get the last thinking message
            last_thoughts = ""
            for msg in reversed(state['messages']):
                if hasattr(msg, 'content') and "[THINKING]" in str(msg.content):
                    last_thoughts = str(msg.content)
                    break
            
            # Decide what tool to use
            action_prompt = f"""Based on this thinking: {last_thoughts}

What specific command should I run? Respond with ONLY the command, nothing else.
If no command is needed, respond with 'NO_ACTION'."""

            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=200,
                messages=[
                    {"role": "user", "content": action_prompt}
                ]
            )
            
            command = ""
            for content_block in response.content:
                if content_block.type == "text":
                    command += content_block.text
            command = command.strip()
            
            if command and command != "NO_ACTION":
                # Execute the command
                result = self.tools_manager.execute_tool(
                    "execute_shell_command",
                    {"command": command, "reason": "Part of continuous reasoning loop"}
                )
                
                state['last_action'] = command
                state['last_result'] = result
                state['messages'].append(AIMessage(content=f"[ACTION] Executed: {command}"))
            else:
                state['messages'].append(AIMessage(content="[ACTION] No action needed"))
                
            state['current_phase'] = "observe"
            
        except Exception as e:
            state['messages'].append(AIMessage(content=f"[ERROR] Act phase failed: {str(e)}"))
            state['current_phase'] = "observe"  # Continue to observe even on error
            
        return state
    
    def observe_node(self, state: ContinuousAgentState) -> ContinuousAgentState:
        """Observe and analyze results"""
        last_result = state.get('last_result')
        
        if last_result:
            # Extract key information from result
            stdout = last_result.get('stdout', '')
            stderr = last_result.get('stderr', '')
            success = last_result.get('success', False)
            
            observation = f"Command result - Success: {success}"
            if stdout:
                observation += f"\nOutput: {stdout[:500]}"  # First 500 chars
            if stderr:
                observation += f"\nError: {stderr[:500]}"
                
            # Add to observations
            state['observations'].append(observation)
            state['messages'].append(AIMessage(content=f"[OBSERVE] {observation}"))
            
            # Update working memory with key findings
            if 'working_memory' not in state:
                state['working_memory'] = {}
            state['working_memory']['last_command_success'] = success
            
        state['current_phase'] = "decide"
        return state
    
    def decide_node(self, state: ContinuousAgentState) -> ContinuousAgentState:
        """Decide whether to continue or stop"""
        # Check exit conditions
        if state['iteration_count'] >= state['max_iterations']:
            state['should_continue'] = False
            state['exit_reason'] = "Max iterations reached"
            state['messages'].append(AIMessage(content="[DECIDE] Stopping - max iterations reached"))
        elif state.get('exit_reason'):
            state['should_continue'] = False
            state['messages'].append(AIMessage(content=f"[DECIDE] Stopping - {state['exit_reason']}"))
        else:
            # Continue loop
            state['should_continue'] = True
            state['iteration_count'] += 1
            state['current_phase'] = "think"
            state['messages'].append(AIMessage(content=f"[DECIDE] Continuing to iteration {state['iteration_count']}"))
            
        return state
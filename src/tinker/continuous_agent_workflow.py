"""
Continuous Agent Workflow for Tinker
Implements the Think-Act-Observe-Decide loop
"""

from typing import Optional
from langgraph.graph import StateGraph, END
from .continuous_agent_state import ContinuousAgentState
from .continuous_agent_nodes import ContinuousAgentNodes
from langchain_core.messages import HumanMessage, AIMessage


class ContinuousAgentWorkflow:
    """Continuous reasoning loop workflow"""
    
    def __init__(self):
        self.nodes = ContinuousAgentNodes()
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the continuous loop graph"""
        workflow = StateGraph(ContinuousAgentState)
        
        # Add nodes
        workflow.add_node("think", self.nodes.think_node)
        workflow.add_node("act", self.nodes.act_node)
        workflow.add_node("observe", self.nodes.observe_node)
        workflow.add_node("decide", self.nodes.decide_node)
        
        # Define the loop flow
        workflow.set_entry_point("think")
        
        # Linear flow through the loop
        workflow.add_edge("think", "act")
        workflow.add_edge("act", "observe")
        workflow.add_edge("observe", "decide")
        
        # Conditional edge from decide
        def should_continue(state: ContinuousAgentState) -> str:
            """Decide whether to continue the loop or end"""
            if state.get('should_continue', True):
                return "think"  # Loop back
            else:
                return "end"
        
        workflow.add_conditional_edges(
            "decide",
            should_continue,
            {
                "think": "think",
                "end": END
            }
        )
        
        return workflow.compile()
    
    def run_continuous_task(self, goal: str, max_iterations: int = 10) -> ContinuousAgentState:
        """Run a task with continuous reasoning loop"""
        initial_state = ContinuousAgentState(
            messages=[HumanMessage(content=goal)],
            current_goal=goal,
            iteration_count=1,
            max_iterations=max_iterations,
            working_memory={},
            observations=[],
            planned_actions=[],
            last_action=None,
            last_result=None,
            should_continue=True,
            exit_reason=None,
            current_phase="think"
        )
        
        # Add initial message
        initial_state['messages'].append(
            AIMessage(content=f"Starting continuous reasoning loop for goal: {goal}")
        )
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        # Add summary
        final_state['messages'].append(
            AIMessage(content=f"Completed after {final_state['iteration_count']} iterations. Reason: {final_state.get('exit_reason', 'Unknown')}")
        )
        
        return final_state
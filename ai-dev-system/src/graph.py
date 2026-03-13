from langgraph.graph import StateGraph, END
from src.state import GraphState
from src.agents.spec_agent import spec_agent_node
from src.agents.validator_agent import validator_agent_node
from src.agents.coding_agent import coding_agent_node
from src.agents.testing_agent import testing_agent_node
from src.agents.pr_agent import pr_agent_node

def build_graph():
    """
    Constructs the LangGraph StateGraph, defines the node routing logic 
    and returns the compiled workflow according to spec.
    """
    workflow = StateGraph(GraphState)
    
    # 1. Add all agent nodes to the State Graph
    workflow.add_node("Spec Agent", spec_agent_node)
    workflow.add_node("Validator Agent", validator_agent_node)
    workflow.add_node("Coding Agent", coding_agent_node)
    workflow.add_node("Testing Agent", testing_agent_node)
    workflow.add_node("PR Agent", pr_agent_node)
    
    # Configuration of initial entry point
    workflow.set_entry_point("Spec Agent")
    
    # Simple linear edge between Spec Generation and Validation
    workflow.add_edge("Spec Agent", "Validator Agent")
    
    # Conditional logic out of Validator
    def route_validation(state: GraphState):
        if state.get("spec_feedback", "") == "VALID":
            return "Coding Agent"
        return "Spec Agent"
        
    workflow.add_conditional_edges("Validator Agent", route_validation)
    
    # Linear edge to testing
    workflow.add_edge("Coding Agent", "Testing Agent")
    
    # Complex rules based routing on testing failures and loops
    def route_testing(state: GraphState):
        if state.get("tests_passed", False):
            return "PR Agent"
        
        # Max iteration threshold is 3
        if state.get("iteration_count", 0) < 3:
            return "Coding Agent"
            
        # If over 3 iteration loops, terminate as failure
        return END

    workflow.add_conditional_edges("Testing Agent", route_testing)
    
    # Once PR is raised, complete execution successfully
    workflow.add_edge("PR Agent", END)
    
    return workflow.compile()

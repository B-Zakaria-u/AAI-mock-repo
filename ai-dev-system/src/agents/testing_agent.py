import os
from src.state import GraphState
from src.tools.docker import run_tests_in_sandbox

def testing_agent_node(state: GraphState) -> dict:
    """
    Triggers the docker testing sandbox. 
    Parses output to determine if tests have passed or failed.
    """
    # Look for our workspace to run tests inside
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
    
    # Run pytest securely via Docker custom tool
    result = run_tests_in_sandbox.invoke(workspace_dir)
    
    # Rough check for failures or Python crash/error messages
    tests_passed = "Tests failed" not in result and "Failed to execute sandbox" not in result

    return {
        "test_output": result,
        "tests_passed": tests_passed
    }

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
    
    # Run testing script securely via Docker custom tool
    print("[ Testing Agent ] Spinning up Docker sandbox to execute test.sh...")
    result = run_tests_in_sandbox.invoke(workspace_dir)
    
    # Generic check for failure keywords or explicit sandbox errors
    failed_keywords = ["Tests failed", "Failed to execute sandbox", "FAIL", "ERR!"]
    tests_passed = not any(kw in result for kw in failed_keywords)
    
    if tests_passed:
        print("[ Testing Agent ] Result: PASS. Code is fully verified.")
    else:
        print("[ Testing Agent ] Result: FAIL. Tests did not pass.")

    return {
        "test_output": result,
        "tests_passed": tests_passed
    }

import os
from src.state import GraphState
from src.tools.docker.sandbox import run_tests_in_sandbox
from src.config.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

def testing_agent_node(state: GraphState) -> dict:
    """
    Triggers the docker testing sandbox to run script.sh.
    Uses an LLM as an independent tester to determine if tests have passed.
    """
    # Look for our workspace to run tests inside
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
    
    llm = get_llm()
    ticket_text = state.get("ticket_text", "")
    
    # Need to generate script.sh dynamically based on the issue
    print("[ Testing Agent ] Generating test script (script.sh)...")
    gen_messages = [
        SystemMessage(content=(
            "You are an expert test engineer. The user has an issue they want to test. "
            "Write a bash script that will test this codebase for the issue. "
            "If it's a Python project, it might run pytest or create test files and run them. "
            "Output ONLY the raw script content, no markdown code blocks or explanations."
        )),
        HumanMessage(content=f"Issue ticket:\n{ticket_text}")
    ]
    script_content = str(llm.invoke(gen_messages).content).strip()
    
    # Cleanup markdown block if the LLM adds it anyway
    if script_content.startswith("```"):
        lines = script_content.splitlines()
        script_content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        
    script_path = os.path.join(workspace_dir, "script.sh")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
        
    # Run testing script securely via Docker custom tool
    print("[ Testing Agent ] Spinning up Docker sandbox to execute script.sh...")
    result = run_tests_in_sandbox.invoke(workspace_dir)
    
    llm = get_llm()
    eval_messages = [
        SystemMessage(content=(
            "You are an independent tester in a software company. "
            "You just executed script.sh in the sandbox. "
            "Evaluate this output and respond with 'PASS' if the tests passed, or 'FAIL' if they didn't."
        )),
        HumanMessage(content=f"Sandbox script.sh output:\n{result}")
    ]
    
    eval_response = llm.invoke(eval_messages).content
    eval_str = str(eval_response).strip().upper()
    
    tests_passed = "PASS" in eval_str and "FAIL" not in eval_str
    
    if tests_passed:
        print("[ Testing Agent ] Result: PASS. Code is fully verified.")
    else:
        print("[ Testing Agent ] Result: FAIL. Tests did not pass.")

    return {
        "test_output": result,
        "tests_passed": tests_passed
    }

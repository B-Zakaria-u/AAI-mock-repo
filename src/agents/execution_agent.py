import os
from src.state import GraphState
from src.tools.docker.sandbox import run_tests_in_sandbox
from src.config.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.logger import log_llm_interaction, log_chat_interaction


def execution_agent_node(state: GraphState) -> dict:
    """
    TDD Approach: Executes the generated script.sh in the Docker sandbox.
    Evaluates the output to determine if tests pass or fail.
    """
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
    llm = get_llm()
    log_file_path = state.get("log_file_path", "")
    chat_log_file_path = state.get("chat_log_file_path", "")
    total_tokens = state.get("total_tokens", 0)
    
    print("[ Execution Agent ] Spinning up Docker sandbox to execute tests...")
    result = run_tests_in_sandbox.invoke({"workspace_path": workspace_dir})
    
    eval_messages = [
        SystemMessage(content=(
            "You are an independent tester. Evaluate the sandbox output below. "
            "Respond with EXACTLY 'PASS' if all tests passed, or 'FAIL' if any test failed or if an error occurred."
        )),
        HumanMessage(content=f"Sandbox output:\n{result}")
    ]

    if chat_log_file_path:
        log_chat_interaction(chat_log_file_path, "Execution Agent", eval_messages)
    
    response = llm.invoke(eval_messages)
    
    # Extract token usage
    usage = response.usage_metadata or {}
    p_tokens = usage.get("input_tokens", 0)
    c_tokens = usage.get("output_tokens", 0)

    if log_file_path:
        model = getattr(llm, "model", getattr(llm, "model_name", "unknown-model"))
        log_llm_interaction(log_file_path, "Execution Agent", model, p_tokens, c_tokens)

    eval_response = response.content
    eval_str = str(eval_response).strip().upper()
    
    tests_passed = "PASS" in eval_str and "FAIL" not in eval_str
    
    if tests_passed:
        print("[ Execution Agent ] Result: PASS. Code is fully verified.")
    else:
        print("[ Execution Agent ] Result: FAIL. Tests did not pass.")
        
    return {
        "test_output": result,
        "tests_passed": tests_passed,
        "total_tokens": total_tokens + p_tokens + c_tokens
    }

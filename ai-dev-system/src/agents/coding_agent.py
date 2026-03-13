import os
from src.state import GraphState
from src.config.llm import get_llm
from src.tools.files import get_file_tools
from src.tools.search import get_search_tools
from src.tools.linter import get_linter_tools
from src.tools.ast_analysis import get_ast_tools
from src.tools.graph_rag import get_graph_rag_tools
from langchain_core.messages import SystemMessage, HumanMessage

def coding_agent_node(state: GraphState) -> dict:
    """
    Uses the file toolkit to write code implementing the provided specification.
    Loops internally to execute tool calls returned by the LLM.
    """
    llm = get_llm()
    spec = state.get("spec", "")
    test_output = state.get("test_output", "")
    iteration_count = state.get("iteration_count", 0)
    
    # Point workspace toolkit one level up to /workspace
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
    file_tools = get_file_tools(workspace_dir)
    search_tools = get_search_tools()
    linter_tools = get_linter_tools()
    ast_tools = get_ast_tools()
    graph_rag_tools = get_graph_rag_tools()
    
    all_tools = file_tools + search_tools + linter_tools + ast_tools + graph_rag_tools
    llm_with_tools = llm.bind_tools(all_tools)
    
    prompt = f"Implement the complete codebase based on this specification:\n\n{spec}\n"
    if test_output:
        prompt += f"\nYour last implementation failed tests with this output:\n{test_output}\nPlease fix the failing code.\n"
        
    messages = [
        SystemMessage(content=(
            "You are a senior Software Engineer. You write clean, testable Python code.\n"
            "Before writing any new code, ALWAYS follow this reasoning sequence:\n"
            "1. Call `summarise_code_graph` on the workspace to understand the existing codebase structure.\n"
            "2. Call `query_code_graph` with a keyword from the spec to retrieve closely related entities.\n"
            "3. Call `list_workspace_symbols` if you need a detailed symbol-level view of specific files.\n"
            "4. Only THEN create or edit files using the file management tools.\n"
            "5. After writing code, call `run_linter` to check for issues before finishing."
        )),
        HumanMessage(content=prompt)
    ]
    
    # One-shot tool execution loop for simplicity
    response = llm_with_tools.invoke(messages)
    
    # If the LLM generates tool_calls, process them (write files, read files, etc.)
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            for t in all_tools:
                if t.name == tool_name:
                    t.invoke(tool_args)
                    
    return {"iteration_count": iteration_count + 1}

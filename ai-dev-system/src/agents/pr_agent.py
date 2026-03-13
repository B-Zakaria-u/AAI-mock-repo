from src.state import GraphState
from src.llm_config import get_llm
from src.tools.gitlab_tools import get_gitlab_tools
from langchain_core.messages import SystemMessage, HumanMessage

def pr_agent_node(state: GraphState) -> dict:
    """
    Prepares and raises a Pull Request/Merge Request via the GitLab toolkit.
    Executes tool calls from the LLM based on bound generic tools.
    """
    llm = get_llm()
    ticket_text = state.get("ticket_text", "")
    
    gitlab_tools = get_gitlab_tools()
    llm_with_tools = llm.bind_tools(gitlab_tools)
    
    prompt = f"The implementation of this ticket has successfully passed tests. Please create a Merge Request for the main branch:\n\n{ticket_text}"
    
    messages = [
        SystemMessage(content="You are a CI/CD agent responsible for creating GitLab Merge Requests."),
        HumanMessage(content=prompt)
    ]
    
    response = llm_with_tools.invoke(messages)
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            for t in gitlab_tools:
                if t.name == tool_name:
                    t.invoke(tool_args)
                    
    # Simulate extraction of PR URL for the demo/state update
    return {"pr_url": "https://gitlab.example.com/project/-/merge_requests/latest"}

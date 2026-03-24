from langchain_community.tools import DuckDuckGoSearchRun

def get_search_tools():
    """
    Returns a web search tool to allow agents to look up documentation, 
    API references, or solutions to errors.
    """
    search = DuckDuckGoSearchRun()
    return [search]

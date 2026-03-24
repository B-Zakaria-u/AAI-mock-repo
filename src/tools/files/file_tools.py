"""File management tools — wraps LangChain FileManagementToolkit (SRP: filesystem I/O only)."""
import os
from langchain_community.agent_toolkits import FileManagementToolkit


def get_file_tools(workspace_dir: str) -> list:
    """
    Return LangChain file-management tools rooted at *workspace_dir*.

    The directory is created on demand so callers never need to check
    for its existence beforehand.
    """
    os.makedirs(workspace_dir, exist_ok=True)
    toolkit = FileManagementToolkit(root_dir=workspace_dir)
    return toolkit.get_tools()

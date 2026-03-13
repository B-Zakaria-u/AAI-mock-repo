import os
from langchain_community.agent_toolkits import FileManagementToolkit

def get_file_tools(workspace_dir: str):
    """
    Instantiates LangChain FileManagementToolkit bounded to the given workspace directory.
    """
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir, exist_ok=True)
        
    toolkit = FileManagementToolkit(
        root_dir=workspace_dir,
    )
    return toolkit.get_tools()

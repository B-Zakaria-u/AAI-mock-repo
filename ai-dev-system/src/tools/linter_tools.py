import subprocess
import os
from langchain_core.tools import tool

@tool
def run_linter(workspace_path: str) -> str:
    """
    Runs flake8 linter on the workspace to check for syntax errors,
    undefined names, and general Python code quality issues.
    
    Args:
        workspace_path (str): The absolute path to the local git workspace to lint.
    """
    abs_workspace = os.path.abspath(workspace_path)
    try:
        # Run flake8. In a stricter sandboxed environment, this could also run inside Docker
        result = subprocess.run(
            ["flake8", abs_workspace, "--max-line-length=100"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return "Linting passed with no issues."
        else:
            return f"Linting found issues:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        return f"Failed to execute linter: {str(e)}"

def get_linter_tools():
    return [run_linter]

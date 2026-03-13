"""Linter tool — SRP: static code quality checking only."""
import os
import subprocess

from langchain_core.tools import tool


@tool
def run_linter(workspace_path: str) -> str:
    """
    Run ``flake8`` on all Python files in *workspace_path*.

    Returns a plain-text report of style and syntax issues, or a success
    message if the code is clean.

    Args:
        workspace_path: Absolute or relative path to the directory to lint.
    """
    abs_workspace = os.path.abspath(workspace_path)
    try:
        result = subprocess.run(
            ["flake8", abs_workspace, "--max-line-length=100"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "Linting passed — no issues found."
        return f"Linting issues found:\n{result.stdout}\n{result.stderr}".strip()
    except Exception as exc:
        return f"Linter execution error: {exc}"


def get_linter_tools() -> list:
    """Return the linting tool list."""
    return [run_linter]

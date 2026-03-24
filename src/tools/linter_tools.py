"""Legacy top-level linter tools — delegates to the sub-package version.

This file exists for backward compatibility. The canonical implementation
lives in ``src.tools.linter.linter_tools``.
"""
import subprocess
import os
from langchain_core.tools import tool
from src.utils.language_detector import detect_language


@tool
def run_linter(workspace_path: str) -> str:
    """
    Runs the appropriate linter for the detected language in the workspace.
    Language-agnostic: dispatches to flake8, eslint, checkstyle, phpcs, etc.

    Args:
        workspace_path (str): The absolute path to the local git workspace to lint.
    """
    # Delegate to the sub-package implementation
    from src.tools.linter.linter_tools import run_linter as _run_linter
    return _run_linter.invoke(workspace_path)


def get_linter_tools():
    return [run_linter]

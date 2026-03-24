import ast
import json
import os
import glob
from langchain_core.tools import tool


import re

def _parse_file(file_path: str) -> dict:
    """
    Internal helper: parses a generic source file with Regex to find classes and functions.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        return {"error": str(e)}

    classes: list[dict] = []
    top_level_funcs: list[dict] = []

    class_pattern = re.compile(r"^\s*(export\s+)?(public\s+)?class\s+([A-Za-z0-9_]+)")
    func_pattern = re.compile(r"^\s*(export\s+)?(public\s+|private\s+|protected\s+)?(static\s+)?(async\s+)?(function|func|def)\s+([A-Za-z0-9_]+)")
    arrow_pattern = re.compile(r"^\s*(export\s+)?(const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(\(.*\)|[^=]+)\s*=>")

    for i, line in enumerate(lines):
        lineno = i + 1
        c_match = class_pattern.search(line)
        if c_match:
            classes.append({"name": c_match.group(3), "lineno": lineno, "methods": []})
            continue
            
        f_match = func_pattern.search(line)
        if f_match:
            top_level_funcs.append({"name": f_match.group(6), "lineno": lineno})
            continue
            
        a_match = arrow_pattern.search(line)
        if a_match:
            top_level_funcs.append({"name": a_match.group(3), "lineno": lineno})

    return {
        "file": file_path,
        "imports": [],
        "top_level_functions": top_level_funcs,
        "classes": classes,
    }


@tool
def analyze_file_ast(file_path: str) -> str:
    """
    Parses a single source file and returns its extracted symbol table as a
    JSON string: top-level functions, and classes.

    Args:
        file_path: Absolute or relative path to the source file to analyse.
    """
    result = _parse_file(file_path)
    return json.dumps(result, indent=2)


@tool
def list_workspace_symbols(workspace_path: str) -> str:
    """
    Walks every source file in the given workspace directory and extracts
    symbol information (functions, classes) for each file.
    Returns a merged JSON map keyed by file path.

    Args:
        workspace_path: Root directory to scan recursively.
    """
    extensions = ("*.py", "*.js", "*.ts", "*.java", "*.go", "*.cpp", "*.c", "*.cs", "*.rb", "*.php")
    
    results = {}
    for ext in extensions:
        pattern = os.path.join(os.path.abspath(workspace_path), "**", ext)
        for fp in glob.glob(pattern, recursive=True):
            results[fp] = _parse_file(fp)

    return json.dumps(results, indent=2)


def get_ast_tools():
    """Returns the list of AST-based LangChain tools."""
    return [analyze_file_ast, list_workspace_symbols]

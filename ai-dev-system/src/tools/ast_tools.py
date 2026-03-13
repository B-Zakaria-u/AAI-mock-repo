import ast
import json
import os
import glob
from langchain_core.tools import tool


def _parse_file(file_path: str) -> dict:
    """
    Internal helper: parses a single Python file with the ast module.
    Returns a structured dict of imports, classes (with methods), and functions.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except OSError as e:
        return {"error": str(e)}

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    imports: list[str] = []
    functions: list[dict] = []
    classes: list[dict] = []

    for node in ast.walk(tree):
        # Collect imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            else:
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        # Collect top-level functions (depth-1 only)
        elif isinstance(node, ast.FunctionDef) and isinstance(
            getattr(node, "parent", None), ast.Module
        ):
            functions.append({"name": node.name, "lineno": node.lineno})

        # Collect classes + their methods
        elif isinstance(node, ast.ClassDef):
            methods = [
                {"name": n.name, "lineno": n.lineno}
                for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append(
                {"name": node.name, "lineno": node.lineno, "methods": methods}
            )

    # Second pass: top-level functions (parent tagging approach via direct iteration)
    top_level_funcs = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top_level_funcs.append({"name": node.name, "lineno": node.lineno})

    return {
        "file": file_path,
        "imports": list(set(imports)),        # deduplicate
        "top_level_functions": top_level_funcs,
        "classes": classes,
    }


@tool
def analyze_file_ast(file_path: str) -> str:
    """
    Parses a single Python file and returns its AST-extracted symbol table as a
    JSON string: imports, top-level functions, and classes with their methods.

    Args:
        file_path: Absolute or relative path to the .py file to analyse.
    """
    result = _parse_file(file_path)
    return json.dumps(result, indent=2)


@tool
def list_workspace_symbols(workspace_path: str) -> str:
    """
    Walks every .py file in the given workspace directory and extracts
    AST symbol information (imports, functions, classes) for each file.
    Returns a merged JSON map keyed by file path.

    Args:
        workspace_path: Root directory to scan recursively for Python files.
    """
    pattern = os.path.join(os.path.abspath(workspace_path), "**", "*.py")
    py_files = glob.glob(pattern, recursive=True)

    results = {}
    for fp in py_files:
        results[fp] = _parse_file(fp)

    return json.dumps(results, indent=2)


def get_ast_tools():
    """Returns the list of AST-based LangChain tools."""
    return [analyze_file_ast, list_workspace_symbols]

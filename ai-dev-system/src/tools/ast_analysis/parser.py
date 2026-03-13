"""Pure AST parsing logic — zero LangChain dependency (SRP / DIP).

This module contains only Python standard-library code so it can be
unit-tested and reused without pulling in the LangChain stack.
"""
import ast
from typing import Any


def parse_file(file_path: str) -> dict[str, Any]:
    """
    Parse a single Python source file and return a structured symbol table.

    Returns
    -------
    dict with keys:
      - ``file``                : str  — the input path
      - ``imports``             : list[str] — all imported module/name strings
      - ``top_level_functions`` : list[dict] — ``{name, lineno}``
      - ``classes``             : list[dict] — ``{name, lineno, methods: [{name, lineno}]}``
      - ``error``               : str  — only present if parsing failed
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
    except OSError as exc:
        return {"file": file_path, "error": str(exc)}

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        return {"file": file_path, "error": f"SyntaxError: {exc}"}

    imports: list[str] = []
    classes: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.extend(f"{module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.ClassDef):
            methods = [
                {"name": child.name, "lineno": child.lineno}
                for child in ast.walk(node)
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append(
                {"name": node.name, "lineno": node.lineno, "methods": methods}
            )

    # Top-level functions only (direct children of the module node)
    top_level_functions = [
        {"name": node.name, "lineno": node.lineno}
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    return {
        "file": file_path,
        "imports": sorted(set(imports)),
        "top_level_functions": top_level_functions,
        "classes": classes,
    }

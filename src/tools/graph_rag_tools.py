import json
import os
from typing import Optional

import networkx as nx
from langchain_core.tools import tool

# We defer the AST import to avoid circular tool registration
from src.tools.ast_tools import _parse_file


# ---------------------------------------------------------------------------
# Internal graph builder
# ---------------------------------------------------------------------------

def _build_code_graph(workspace_path: str) -> nx.DiGraph:
    """
    Walks every .py file in *workspace_path*, extracts AST symbols, and
    constructs a directed NetworkX graph where:

    Nodes:
        - File nodes  (node_type="file")
        - Class nodes (node_type="class",  parent_file=<path>)
        - Function / method nodes (node_type="function", parent_file=<path>)

    Edges:
        - (file)     --[imports]--> (module_name)
        - (file)     --[defines]--> (class | function)
        - (class)    --[defines]--> (method)

    Args:
        workspace_path: Root directory to scan.
    """
    import glob as _glob

    G = nx.DiGraph()
    pattern = os.path.join(os.path.abspath(workspace_path), "**", "*.py")
    py_files = _glob.glob(pattern, recursive=True)

    for fp in py_files:
        symbols = _parse_file(fp)
        if "error" in symbols:
            continue

        file_node = fp
        G.add_node(file_node, node_type="file", label=os.path.basename(fp))

        # Import edges
        for imp in symbols.get("imports", []):
            imp_node = f"import::{imp}"
            if not G.has_node(imp_node):
                G.add_node(imp_node, node_type="module", label=imp)
            G.add_edge(file_node, imp_node, relation="imports")

        # Top-level function nodes
        for func in symbols.get("top_level_functions", []):
            func_node = f"fn::{fp}::{func['name']}"
            G.add_node(
                func_node,
                node_type="function",
                label=func["name"],
                parent_file=fp,
                lineno=func["lineno"],
            )
            G.add_edge(file_node, func_node, relation="defines")

        # Class nodes + method nodes
        for cls in symbols.get("classes", []):
            cls_node = f"cls::{fp}::{cls['name']}"
            G.add_node(
                cls_node,
                node_type="class",
                label=cls["name"],
                parent_file=fp,
                lineno=cls["lineno"],
            )
            G.add_edge(file_node, cls_node, relation="defines")

            for method in cls.get("methods", []):
                method_node = f"method::{fp}::{cls['name']}::{method['name']}"
                G.add_node(
                    method_node,
                    node_type="method",
                    label=method["name"],
                    parent_class=cls["name"],
                    parent_file=fp,
                    lineno=method["lineno"],
                )
                G.add_edge(cls_node, method_node, relation="defines")

    return G


# ---------------------------------------------------------------------------
# Query helper
# ---------------------------------------------------------------------------

def _fuzzy_match(label: str, query: str) -> bool:
    """Simple case-insensitive substring match for graph node retrieval."""
    return query.lower() in label.lower()


# ---------------------------------------------------------------------------
# LangChain tools
# ---------------------------------------------------------------------------

@tool
def query_code_graph(query: str, workspace_path: str) -> str:
    """
    Builds a directed code knowledge graph from the workspace and retrieves
    nodes and their immediate neighbours that are semantically related to the
    query (by fuzzy name match).  Use this before writing new code to
    understand what already exists and how entities relate to each other.

    Args:
        query:          A term or concept to search for (e.g. "llm", "docker",
                        "validate_spec").
        workspace_path: Root directory to scan (e.g. "src" or "workspace").
    """
    G = _build_code_graph(workspace_path)

    matched_nodes = [
        n for n, attrs in G.nodes(data=True)
        if _fuzzy_match(attrs.get("label", ""), query)
    ]

    if not matched_nodes:
        return f"No nodes found matching '{query}' in the code graph."

    lines: list[str] = [f"Graph query results for '{query}':\n"]
    for node in matched_nodes:
        attrs = G.nodes[node]
        node_type = attrs.get("node_type", "unknown")
        label = attrs.get("label", node)
        parent_file = attrs.get("parent_file", "")
        lineno = attrs.get("lineno", "")

        location = f" (in {os.path.basename(parent_file)} line {lineno})" if parent_file else ""
        lines.append(f"  [{node_type.upper()}] {label}{location}")

        # Show outgoing edges (what this node defines / calls / imports)
        for _, target, edge_attrs in G.out_edges(node, data=True):
            t_label = G.nodes[target].get("label", target)
            lines.append(f"      --[{edge_attrs.get('relation', '?')}]--> {t_label}")

        # Show incoming edges (what uses / defines this node)
        for source, _, edge_attrs in G.in_edges(node, data=True):
            s_label = G.nodes[source].get("label", source)
            lines.append(f"      <--[{edge_attrs.get('relation', '?')}]-- {s_label}")

    return "\n".join(lines)


@tool
def summarise_code_graph(workspace_path: str) -> str:
    """
    Builds the full code knowledge graph and returns a high-level summary:
    total node counts per type, total edges, and a list of all files in the
    graph with their defined class and function counts.

    Args:
        workspace_path: Root directory to scan.
    """
    G = _build_code_graph(workspace_path)

    type_counts: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        t = attrs.get("node_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    file_summaries = []
    for node, attrs in G.nodes(data=True):
        if attrs.get("node_type") == "file":
            label = attrs.get("label", node)
            successors = list(G.successors(node))
            n_classes = sum(1 for s in successors if G.nodes[s].get("node_type") == "class")
            n_funcs   = sum(1 for s in successors if G.nodes[s].get("node_type") == "function")
            file_summaries.append(
                f"  {label}: {n_classes} class(es), {n_funcs} top-level function(s)"
            )

    lines = [
        "=== Code Knowledge Graph Summary ===",
        f"Total nodes : {G.number_of_nodes()}",
        f"Total edges : {G.number_of_edges()}",
        "Node breakdown:",
    ]
    for t, count in sorted(type_counts.items()):
        lines.append(f"  {t:<12}: {count}")
    lines.append("\nFiles in graph:")
    lines.extend(sorted(file_summaries))

    return "\n".join(lines)


def get_graph_rag_tools():
    """Returns the list of GraphRAG LangChain tools."""
    return [query_code_graph, summarise_code_graph]

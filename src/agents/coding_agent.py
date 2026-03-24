import os
from src.state import GraphState
from src.config.llm import get_llm
from src.tools.files import get_file_tools
from src.tools.search import get_search_tools
from src.tools.linter import get_linter_tools
from src.tools.ast_analysis import get_ast_tools
from src.tools.graph_rag import get_graph_rag_tools
from src.tools.folders import initiate_directory, clear_directory
from src.utils.language_detector import detect_language
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.utils.logger import log_llm_interaction, log_chat_interaction
import json
from typing import Any

# ── Per-language coding conventions hint ────────────────────────────────────
_LANG_CONVENTIONS: dict[str, str] = {
    "Python": (
        "Use Python idioms: type hints, dataclasses or Pydantic models, f-strings, "
        "and follow PEP 8. Use pytest for tests."
    ),
    "Java": (
        "Use Java idioms: proper access modifiers, JavaDoc comments, and follow "
        "standard Maven/Gradle project layout (src/main/java, src/test/java). "
        "Use JUnit 5 + Mockito for tests."
    ),
    "Kotlin": (
        "Use Kotlin idioms: data classes, extension functions, coroutines where appropriate. "
        "Follow standard Gradle project layout. Use Kotest or JUnit 5 for tests."
    ),
    "PHP": (
        "Use PHP idioms: PSR-12 coding standard, type declarations, namespaces. "
        "Use PHPUnit for tests. Follow Composer project conventions."
    ),
    "JavaScript": (
        "Use modern JavaScript (ES2020+): const/let, arrow functions, async/await, "
        "destructuring. Use Jest or Mocha for tests. Follow the project's existing "
        "package.json scripts."
    ),
    "TypeScript": (
        "Use TypeScript idioms: strict types, interfaces, generics. "
        "Use Jest or Vitest for tests. Follow the project's tsconfig.json."
    ),
    "Go": (
        "Use Go idioms: error wrapping, table-driven tests, interfaces. "
        "Use the standard testing package. Follow standard Go project layout."
    ),
    "Ruby": (
        "Use Ruby idioms: blocks, modules, descriptive method names. "
        "Use RSpec or Minitest for tests. Follow Bundler conventions."
    ),
    "C#": (
        "Use C# idioms: async/await, LINQ, proper exception handling. "
        "Use xUnit or NUnit for tests. Follow .NET project conventions."
    ),
}


def coding_agent_node(state: GraphState) -> dict:
    """
    TDD Approach: Uses the file toolkit to implement the specification.
    Multi-turn (max 10): MUST write files immediately.
    Language-agnostic: detects language/framework from workspace and uses
    appropriate idioms and conventions.
    """
    llm = get_llm()
    spec = state.get("spec", "")
    test_output = state.get("test_output", "")
    iteration_count = state.get("iteration_count", 0)
    log_file_path = state.get("log_file_path", "")
    chat_log_file_path = state.get("chat_log_file_path", "")
    total_tokens = state.get("total_tokens", 0)
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))

    file_tools = get_file_tools(workspace_dir)
    search_tools = get_search_tools()

    all_tools = file_tools + search_tools
    llm_with_tools = llm.bind_tools(all_tools)

    # ── Detect language from workspace ───────────────────────────────────────
    # Prefer cached values from state (set by Spec Agent); re-detect if missing
    detected_language = state.get("detected_language") or ""
    detected_framework = state.get("detected_framework") or ""
    if not detected_language or detected_language == "Unknown":
        lang_info = detect_language(workspace_dir)
        detected_language = lang_info.get("language", "Unknown")
        detected_framework = lang_info.get("framework", "Unknown")

    # ── Workspace file listing ───────────────────────────────────────────────
    workspace_files = []
    ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "env",
                   "target", "build", "dist", ".gradle"}
    if os.path.exists(workspace_dir):
        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), workspace_dir)
                workspace_files.append(rel_path)

    file_list_str = "\n".join([f"- {f}" for f in workspace_files])

    # ── Language conventions hint ────────────────────────────────────────────
    lang_conventions = _LANG_CONVENTIONS.get(detected_language, "")
    lang_note = ""
    if detected_language != "Unknown":
        lang_note = f"\nDetected language: **{detected_language}**"
        if detected_framework != "Unknown":
            lang_note += f" / framework: **{detected_framework}**"
        if lang_conventions:
            lang_note += f"\nFollow these conventions: {lang_conventions}"
        lang_note += "\n"

    # ── Build prompt ─────────────────────────────────────────────────────────
    max_turns = 10
    prompt = f"ACTION: Implement the following specification. You have ONLY {max_turns} turns.\n\n{spec}\n"
    prompt += f"\nWorkspace root is the current directory. All file paths must be strictly relative to it.\n"
    prompt += f"Existing files in workspace:\n{file_list_str}\n"
    prompt += lang_note

    if test_output:
        prompt += f"\nTests failed with:\n{test_output}\nFIX THE CODE NOW.\n"
    else:
        prompt += "\nRead the existing relevant files (if any), then implement the required code files immediately.\n"

    messages = [
        SystemMessage(content=(
            "You are a senior Software Engineer. You write clean, functional code.\n"
            "MANDATORY: You MUST use 'write_file' to create or modify code in Turn 1 or 2.\n"
            "You can call multiple 'write_file' tools in a single turn. Do it for all required files at once.\n"
            "CRITICAL: All file paths provided to tools MUST be relative to the workspace root. Do NOT prepend 'workspace/' or the absolute path.\n"
            "Do NOT waste turns on research. If you know what to write, write it.\n"
            "Use the idioms and conventions of the detected language/framework. "
            "Never default to Python when the spec clearly targets another language."
        )),
        HumanMessage(content=prompt)
    ]

    current_request_tokens = 0

    # Internal multi-turn loop (max turns)
    for i in range(max_turns):
        if chat_log_file_path:
            log_chat_interaction(chat_log_file_path, f"Coding Agent (turn {i+1})", messages)

        print(f"[ Coding Agent ] Internal Turn {i+1} — Invoking LLM...")
        response = llm_with_tools.invoke(messages)

        # Extract token usage
        usage = response.usage_metadata or {}
        p_tokens = usage.get("input_tokens", 0)
        c_tokens = usage.get("output_tokens", 0)
        current_request_tokens += (p_tokens + c_tokens)

        if log_file_path:
            model = getattr(llm, "model", getattr(llm, "model_name", "unknown-model"))
            log_llm_interaction(log_file_path, f"Coding Agent (turn {i+1})", model, p_tokens, c_tokens)

        messages.append(response)

        if not response.tool_calls:
            print("[ Coding Agent ] No more tool calls requested. Finishing turn.")
            break

        print(f"[ Coding Agent ] Executing {len(response.tool_calls)} tool call(s)...")
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_id = tool_call['id']

            print(f"  -> Calling tool: {tool_name}")
            result = "Tool not found."
            for t in all_tools:
                if t.name == tool_name:
                    try:
                        res = t.invoke(tool_args)
                        result = str(res)
                    except Exception as e:
                        result = f"Error: {e}"
                        print(f"     Tool error: {e}")

            messages.append(ToolMessage(content=result, tool_call_id=tool_id))

    return {
        "iteration_count": iteration_count + 1,
        "detected_language": detected_language,
        "detected_framework": detected_framework,
        "total_tokens": total_tokens + current_request_tokens
    }

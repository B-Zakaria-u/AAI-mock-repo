import os
from src.state import GraphState
from src.config.llm import get_llm
from src.utils.logger import log_llm_interaction, log_chat_interaction
from src.utils.language_detector import detect_language
from src.tools.folders import initiate_directory, clear_directory
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage


# ── Language → test framework + script.sh template ──────────────────────────
_TEST_FRAMEWORK_HINTS: dict[str, dict[str, str]] = {
    "Python": {
        "framework": "pytest",
        "file_pattern": "test_<module>.py in workspace/tests/",
        "script_hint": (
            "#!/bin/bash\n"
            "pip install -r /workspace/requirements.txt 2>/dev/null || true\n"
            "pip install pytest\n"
            "cd /workspace && pytest -v"
        ),
    },
    "Java": {
        "framework": "JUnit 5 + Mockito",
        "file_pattern": "<Module>Test.java in src/test/java/",
        "script_hint": (
            "#!/bin/bash\n"
            "cd /workspace && mvn test -B"
            " # OR: ./gradlew test"
        ),
    },
    "Kotlin": {
        "framework": "Kotest or JUnit 5",
        "file_pattern": "<Module>Test.kt in src/test/kotlin/",
        "script_hint": (
            "#!/bin/bash\n"
            "cd /workspace && ./gradlew test"
        ),
    },
    "PHP": {
        "framework": "PHPUnit",
        "file_pattern": "<Module>Test.php in tests/",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y php php-cli composer 2>/dev/null\n"
            "cd /workspace && composer install --no-interaction\n"
            "./vendor/bin/phpunit --testdox"
        ),
    },
    "JavaScript": {
        "framework": "Jest",
        "file_pattern": "<module>.test.js in __tests__/ or alongside source",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y nodejs npm 2>/dev/null\n"
            "cd /workspace && npm install\n"
            "npm test"
        ),
    },
    "TypeScript": {
        "framework": "Jest + ts-jest or Vitest",
        "file_pattern": "<module>.test.ts in __tests__/ or alongside source",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y nodejs npm 2>/dev/null\n"
            "cd /workspace && npm install\n"
            "npm test"
        ),
    },
    "Go": {
        "framework": "testing (standard library)",
        "file_pattern": "<module>_test.go alongside source files",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y golang 2>/dev/null\n"
            "cd /workspace && go test ./..."
        ),
    },
    "Ruby": {
        "framework": "RSpec or Minitest",
        "file_pattern": "<module>_spec.rb in spec/ or test_<module>.rb in test/",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y ruby bundler 2>/dev/null\n"
            "cd /workspace && bundle install\n"
            "bundle exec rspec"
        ),
    },
    "C#": {
        "framework": "xUnit or NUnit",
        "file_pattern": "<Module>Tests.cs in <ProjectName>.Tests/",
        "script_hint": (
            "#!/bin/bash\n"
            "apt-get update -y && apt-get install -y dotnet-sdk-8.0 2>/dev/null\n"
            "cd /workspace && dotnet test"
        ),
    },
}


def testing_agent_node(state: GraphState) -> dict:
    """
    TDD Approach: Generates a test suite and a script.sh execution script.
    Multi-turn (max 10): MUST write files by turn 1 or 2.
    Language-agnostic: detects language/framework and generates tests using
    the appropriate test framework (pytest, JUnit, Jest, PHPUnit, Kotest, etc.)
    and a matching script.sh with the correct install + test commands.
    """
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))

    # Creating the workspace directory
    initiate_directory(workspace_dir)

    # Clearing the workspace directory
    clear_directory(workspace_dir)

    llm = get_llm()
    ticket_text = state.get("ticket_text", "")
    spec = state.get("spec", "")
    log_file_path = state.get("log_file_path", "")
    chat_log_file_path = state.get("chat_log_file_path", "")
    total_tokens = state.get("total_tokens", 0)

    # ── Detect language ──────────────────────────────────────────────────────
    detected_language = state.get("detected_language") or ""
    detected_framework = state.get("detected_framework") or ""
    if not detected_language or detected_language == "Unknown":
        lang_info = detect_language(workspace_dir)
        detected_language = lang_info.get("language", "Unknown")
        detected_framework = lang_info.get("framework", "Unknown")

    # Look up test framework hints
    hints = _TEST_FRAMEWORK_HINTS.get(detected_language, {})
    test_framework = hints.get("framework", "the appropriate test framework for the detected language")
    file_pattern = hints.get("file_pattern", "tests/ directory")
    script_hint = hints.get(
        "script_hint",
        "#!/bin/bash\n# Install dependencies and run the test suite for the detected language"
    )

    from src.tools.files import get_file_tools
    file_tools = get_file_tools(workspace_dir)
    llm_with_tools = llm.bind_tools(file_tools)

    print(f"[ Testing Agent ] Generating TDD test suite for {detected_language}/{detected_framework}...")

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

    max_turns = 10
    gen_prompt = (
        f"You are an expert test engineer. You have ONLY {max_turns} turns.\n\n"
        f"DETECTED LANGUAGE: {detected_language}\n"
        f"DETECTED FRAMEWORK: {detected_framework}\n"
        f"TEST FRAMEWORK TO USE: {test_framework}\n\n"
        "GOAL: Create a complete test suite AND a script.sh execution script.\n\n"
        "INSTRUCTIONS:\n"
        "1. Use the 'write_file' tool to create test files.\n"
        f"   - Name test files following {detected_language} convention: {file_pattern}\n"
        f"   - Use {test_framework} as the test framework.\n"
        "   - Each source file / class should have its own test file.\n"
        "   - Write meaningful tests that cover the spec requirements.\n\n"
        "2. Create a 'script.sh' in the workspace root (NOT in tests/).\n"
        "   - This script will be run inside a Ubuntu Docker container.\n"
        "   - It must: install all required runtimes/dependencies, then run all tests.\n"
        f"   - Reference template for {detected_language}:\n"
        f"```\n{script_hint}\n```\n"
        "   - Adapt as needed based on the actual workspace layout.\n\n"
        "3. You can call multiple 'write_file' tools in a single turn.\n"
        "   DO NOT waste turns on research if the spec is clear.\n\n"
        f"Workspace root is the current directory. All file paths must be strictly relative to it.\n"
        f"Existing files in workspace:\n{file_list_str}\n\n"
        f"Issue ticket:\n{ticket_text}\n\n"
        f"Technical Specification:\n{spec}\n"
    )

    messages = [
        SystemMessage(content=(
            f"You are a test-driven development expert specializing in {detected_language}. "
            f"Write tests using {test_framework}. Use the 'write_file' tool immediately. "
            "Do not hesitate. Create both the test files AND the script.sh runner. "
            "The script.sh MUST install the runtime environment if needed (apt-get, pip, npm, mvn, etc.) "
            "before running tests, as it executes inside a bare Ubuntu container.\n"
            "CRITICAL: All file paths provided to tools MUST be relative to the workspace root. Do NOT prepend 'workspace/' or the absolute path."
        )),
        HumanMessage(content=gen_prompt)
    ]

    current_request_tokens = 0

    # Internal multi-turn loop (max turns)
    for i in range(max_turns):
        if chat_log_file_path:
            log_chat_interaction(chat_log_file_path, f"Testing Agent (turn {i+1})", messages)

        print(f"[ Testing Agent ] Internal Turn {i+1} — Invoking LLM...")
        response = llm_with_tools.invoke(messages)

        # Extract token usage
        usage = response.usage_metadata or {}
        p_tokens = usage.get("input_tokens", 0)
        c_tokens = usage.get("output_tokens", 0)
        current_request_tokens += (p_tokens + c_tokens)

        if log_file_path:
            model = getattr(llm, "model", getattr(llm, "model_name", "unknown-model"))
            log_llm_interaction(log_file_path, f"Testing Agent (turn {i+1})", model, p_tokens, c_tokens)

        messages.append(response)

        if not response.tool_calls:
            print("[ Testing Agent ] No more tool calls requested. Finishing turn.")
            break

        print(f"[ Testing Agent ] Executing {len(response.tool_calls)} tool call(s)...")
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_id = tool_call['id']

            print(f"  -> Calling tool: {tool_name}")
            result = "Tool not found."
            for t in file_tools:
                if t.name == tool_name:
                    try:
                        res = t.invoke(tool_args)
                        result = str(res)
                    except Exception as e:
                        result = f"Error: {e}"
                        print(f"     Tool error: {e}")

            messages.append(ToolMessage(content=result, tool_call_id=tool_id))

    return {
        "tests_generated": True,
        "detected_language": detected_language,
        "detected_framework": detected_framework,
        "total_tokens": total_tokens + current_request_tokens
    }

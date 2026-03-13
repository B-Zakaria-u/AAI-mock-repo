"""PR Agent — SRP: commit, push, and open a GitHub Pull Request.

Replaces the old GitLab-based PR agent with GitHub tooling.
"""
from src.agents.base import BaseAgentNode
from src.config.llm import get_llm
from src.state import GraphState
from src.tools.github.git_tools import commit_and_push
from src.tools.github.pr_tools import create_pull_request
from langchain_core.messages import SystemMessage, HumanMessage


class PRAgent(BaseAgentNode):
    """Commits and pushes the fix, then opens a GitHub Pull Request."""

    def run(self, state: GraphState) -> dict:
        llm = get_llm()
        ticket_text = state.get("ticket_text", "")
        issue_number = state.get("issue_number", 0)
        branch_name = state.get("branch_name", "fix/automated")

        all_tools = [commit_and_push, create_pull_request]
        llm_with_tools = llm.bind_tools(all_tools)

        # ── LLM drafts commit message and PR description ─────────────────────
        draft_messages = [
            SystemMessage(content=(
                "You are a CI/CD agent. Produce a concise git commit message and "
                "a short GitHub PR description for the fix described below. "
                "Format your response as:\n"
                "COMMIT: <one-line commit message>\n"
                "PR_BODY: <short markdown description, include 'Closes #<N>'>"
            )),
            HumanMessage(content=ticket_text),
        ]
        raw = llm.invoke(draft_messages).content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
        draft = str(raw).strip()

        # Parse COMMIT and PR_BODY from the LLM output
        commit_msg = "fix: automated patch via AI Dev System"
        pr_body = f"Automated fix.\n\nCloses #{issue_number}"

        for line in draft.splitlines():
            if line.startswith("COMMIT:"):
                commit_msg = line.replace("COMMIT:", "").strip()
            elif line.startswith("PR_BODY:"):
                pr_body = line.replace("PR_BODY:", "").strip()

        # ── Push the branch ───────────────────────────────────────────────────
        push_result = commit_and_push.invoke({
            "commit_message": commit_msg,
            "branch_name": branch_name,
        })

        # ── Open the PR ───────────────────────────────────────────────────────
        pr_title = f"fix: {ticket_text.splitlines()[0][:72]}"
        pr_result = create_pull_request.invoke({
            "branch_name": branch_name,
            "title": pr_title,
            "body": pr_body,
        })

        # Extract URL from result string
        pr_url = ""
        if "http" in pr_result:
            pr_url = [w for w in pr_result.split() if w.startswith("http")][0]

        return {"pr_url": pr_url}


# LangGraph node callable
pr_agent_node = PRAgent()

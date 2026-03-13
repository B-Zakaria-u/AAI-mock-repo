"""Issue Scout Agent — SRP: GitHub issue discovery, assignment, and repo setup.

This agent is the autonomous entry point of the pipeline. It:
1. Lists open, unassigned issues on the configured GitHub repo.
2. Picks the first issue (LLM selects the most actionable one).
3. Self-assigns the issue so no parallel run picks the same ticket.
4. Clones / pulls the repository into workspace/.
5. Creates a fix branch named ``fix/issue-<N>-<slug>``.
6. Populates state with ticket_text, issue_number, branch_name, repo_url.
"""
import os
import re

from github import Github

from src.agents.base import BaseAgentNode
from src.config.llm import get_llm
from src.state import GraphState
from src.tools.github.issue_tools import list_open_issues, assign_issue
from src.tools.github.git_tools import clone_or_pull_repo, create_branch
from langchain_core.messages import SystemMessage, HumanMessage


def _slugify(text: str, max_len: int = 40) -> str:
    """Convert a string to a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


class IssueScooutAgent(BaseAgentNode):
    """Autonomous GitHub issue picker and repository bootstrapper."""

    def run(self, state: GraphState) -> dict:
        llm = get_llm()
        all_tools = [list_open_issues, assign_issue, clone_or_pull_repo, create_branch]
        llm_with_tools = llm.bind_tools(all_tools)

        # ── Step 1: fetch issues ─────────────────────────────────────────────
        issues_text = list_open_issues.invoke({"max_results": 10})

        if "No open" in issues_text:
            # Nothing to work on — return neutral state so graph can END
            return {
                "ticket_text": "",
                "issue_number": 0,
                "branch_name": "",
                "repo_url": "",
            }

        # ── Step 2: LLM picks the best issue ────────────────────────────────
        pick_messages = [
            SystemMessage(content=(
                "You are an autonomous developer agent. "
                "From the list of open GitHub issues below, pick the single most "
                "actionable and self-contained one for a coding fix. "
                "Respond with ONLY the issue number as a plain integer, nothing else."
            )),
            HumanMessage(content=issues_text),
        ]
        pick_response = llm.invoke(pick_messages)
        raw = pick_response.content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
        raw = str(raw).strip()
        match = re.search(r"\d+", raw)
        if not match:
            return {"ticket_text": "", "issue_number": 0, "branch_name": "", "repo_url": ""}

        issue_number = int(match.group())

        # ── Step 3: self-assign the issue ────────────────────────────────────
        assign_issue.invoke({"issue_number": issue_number})

        # ── Step 4: fetch full issue body via PyGithub ───────────────────────
        token = os.environ.get("GITHUB_TOKEN", "")
        repo_name = os.environ.get("GITHUB_REPOSITORY", "")
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        issue = repo.get_issue(issue_number)
        ticket_text = f"#{issue.number} — {issue.title}\n\n{issue.body or ''}"
        repo_url = repo.clone_url                          # https://github.com/org/repo.git
        slug = _slugify(issue.title)
        branch_name = f"fix/issue-{issue_number}-{slug}"

        # ── Step 5: clone / pull repo ────────────────────────────────────────
        clone_or_pull_repo.invoke({"repo_url": repo_url})

        # ── Step 6: create fix branch ────────────────────────────────────────
        create_branch.invoke({"branch_name": branch_name})

        return {
            "ticket_text": ticket_text,
            "issue_number": issue_number,
            "branch_name": branch_name,
            "repo_url": repo_url,
            "iteration_count": 0,
        }


# LangGraph node callable (used in graph.py)
issue_scout_node = IssueScooutAgent()

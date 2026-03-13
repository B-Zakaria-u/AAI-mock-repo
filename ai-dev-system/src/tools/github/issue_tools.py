"""GitHub issue tools — SRP: issue discovery and self-assignment only."""
import os
from github import Github, GithubException
from langchain_core.tools import tool


def _get_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")
    return Github(token)


def _get_repo(client: Github):
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if not repo_name:
        raise EnvironmentError("GITHUB_REPOSITORY environment variable is not set.")
    return client.get_repo(repo_name)


@tool
def list_open_issues(max_results: int = 10) -> str:
    """
    Fetch open, unassigned issues from the configured GitHub repository.

    Returns a formatted list of issue numbers, titles, and body previews
    so the agent can pick the most relevant one to work on.

    Args:
        max_results: Maximum number of issues to return (default 10).
    """
    try:
        client = _get_client()
        repo = _get_repo(client)
        issues = [
            i for i in repo.get_issues(state="open", assignee="none")
            if not i.pull_request  # exclude PRs from the issue list
        ][:max_results]

        if not issues:
            return "No open unassigned issues found."

        lines = [f"Found {len(issues)} open unassigned issue(s):\n"]
        for issue in issues:
            body_preview = (issue.body or "")[:120].replace("\n", " ")
            lines.append(f"  #{issue.number} — {issue.title}\n    {body_preview}")
        return "\n".join(lines)

    except GithubException as exc:
        return f"GitHub API error: {exc.data}"
    except Exception as exc:
        return f"Error listing issues: {exc}"


@tool
def assign_issue(issue_number: int) -> str:
    """
    Self-assign a GitHub issue to the configured GITHUB_ASSIGNEE.

    This prevents parallel pipeline runs from picking the same ticket.

    Args:
        issue_number: The GitHub issue number to assign.
    """
    try:
        assignee = os.environ.get("GITHUB_ASSIGNEE")
        if not assignee:
            raise EnvironmentError("GITHUB_ASSIGNEE environment variable is not set.")

        client = _get_client()
        repo = _get_repo(client)
        issue = repo.get_issue(issue_number)
        issue.add_to_assignees(assignee)
        return f"Issue #{issue_number} successfully assigned to @{assignee}."

    except GithubException as exc:
        return f"GitHub API error: {exc.data}"
    except Exception as exc:
        return f"Error assigning issue: {exc}"


def get_issue_tools() -> list:
    """Return GitHub issue LangChain tools."""
    return [list_open_issues, assign_issue]

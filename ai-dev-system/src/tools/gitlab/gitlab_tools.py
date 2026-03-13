"""GitLab tools — wraps LangChain GitLabToolkit (SRP: VCS / MR operations only)."""
from langchain_community.agent_toolkits.gitlab.toolkit import GitLabToolkit
from langchain_community.utilities.gitlab import GitLabAPIWrapper


def get_gitlab_tools() -> list:
    """
    Return LangChain GitLab tools.

    Requires these environment variables to be set:
    - ``GITLAB_PERSONAL_ACCESS_TOKEN``
    - ``GITLAB_URL``          (e.g. https://gitlab.com)
    - ``GITLAB_REPOSITORY``   (e.g. my-org/my-repo)
    """
    wrapper = GitLabAPIWrapper()
    toolkit = GitLabToolkit.from_gitlab_api_wrapper(wrapper)
    return toolkit.get_tools()

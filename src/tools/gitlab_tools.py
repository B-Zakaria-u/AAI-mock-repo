import os
from langchain_community.agent_toolkits.gitlab.toolkit import GitLabToolkit
from langchain_community.utilities.gitlab import GitLabAPIWrapper

def get_gitlab_tools():
    """
    Instantiates LangChain GitLabToolkit for interacting with a GitLab repository.
    Relies on standard environment variables like GITLAB_PERSONAL_ACCESS_TOKEN and GITLAB_URL.
    """
    gitlab_wrapper = GitLabAPIWrapper()
    toolkit = GitLabToolkit.from_gitlab_api_wrapper(gitlab_wrapper)
    return toolkit.get_tools()

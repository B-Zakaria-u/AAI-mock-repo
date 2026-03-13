import docker
import os
from langchain_core.tools import tool

@tool
def run_tests_in_sandbox(workspace_path: str) -> str:
    """
    Executes tests inside a sandboxed Docker container securely.
    Mounts the workspace directory and runs pytest.
    
    Args:
        workspace_path (str): The absolute path to the local git workspace to test.
    """
    client = docker.from_env()
    abs_workspace = os.path.abspath(workspace_path)
    
    try:
        # Run tests in an ephemeral lightweight container
        # Note: the local path is mounted into /workspace in the container
        container = client.containers.run(
            image="python:3.11-slim",
            command='sh -c "pip install pytest && cd /workspace && pytest"',
            volumes={abs_workspace: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir="/workspace",
            detach=False,
            remove=True
        )
        return container.decode('utf-8')
    except docker.errors.ContainerError as e:
        # If pytest fails, it exits with non-zero, raising a ContainerError
        stderr_out = e.stderr.decode('utf-8') if e.stderr else str(e)
        return f"Tests failed with error:\n{stderr_out}"
    except Exception as e:
        return f"Failed to execute sandbox run: {str(e)}"

"""Docker sandbox tool — SRP: ephemeral container test execution only.

Security perimeter
------------------
* Only the ``workspace/`` directory is mounted (read-write).
* The container is always removed after execution (``remove=True``).
* Tests are run with ``pytest`` inside ``python:3.11-slim``; no shell
  access or network is granted beyond the image default.
"""
import os

import docker
from langchain_core.tools import tool


@tool
def run_tests_in_sandbox(workspace_path: str) -> str:
    """
    Run ``pytest`` inside an ephemeral Docker container.

    The *workspace_path* directory is mounted as ``/workspace`` inside the
    container.  On success the full pytest stdout is returned; on failure
    the error output is returned so the Coding Agent can iterate.

    Args:
        workspace_path: Absolute path to the local workspace directory.
    """
    client = docker.from_env()
    abs_workspace = os.path.abspath(workspace_path)

    try:
        output = client.containers.run(
            image="python:3.11-slim",
            command='sh -c "pip install pytest --quiet && cd /workspace && pytest"',
            volumes={abs_workspace: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            detach=False,
            remove=True,
        )
        return output.decode("utf-8")
    except docker.errors.ContainerError as exc:
        stderr = exc.stderr.decode("utf-8") if exc.stderr else str(exc)
        return f"Tests failed:\n{stderr}"
    except Exception as exc:
        return f"Sandbox execution error: {exc}"

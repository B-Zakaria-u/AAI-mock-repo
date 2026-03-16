"""Docker sandbox tool — SRP: ephemeral container test execution only.

Security perimeter
------------------
* Only the ``workspace/`` directory is mounted (read-write).
* The container is always removed after execution (``remove=True``).
* Tests are run inside an ``ubuntu:latest`` image. The repository MUST
  provide a ``script.sh`` script to be executed.
"""
import os

import docker
from langchain_core.tools import tool


@tool
def run_tests_in_sandbox(workspace_path: str) -> str:
    """
    Run the repository's ``script.sh`` script inside an ephemeral Ubuntu container.

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
            image="ubuntu:latest",
            command='sh -c "chmod +x /workspace/script.sh && /workspace/script.sh"',
            volumes={abs_workspace: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            detach=False,
            remove=True,
            stderr=True,  # Capture both stdout and stderr
            stdout=True
        )
        return output.decode("utf-8")
    except docker.errors.ContainerError as exc:
        # ContainerError hides the true output if the command exits non-zero.
        # We must pull the full logs directly from the container object itself.
        try:
            full_logs = exc.container.logs(stdout=True, stderr=True).decode("utf-8")
        except:
            full_logs = exc.stderr.decode("utf-8") if exc.stderr else str(exc)
        
        return f"Tests failed:\n{full_logs}"
    except Exception as exc:
        return f"Sandbox execution error: {exc}"

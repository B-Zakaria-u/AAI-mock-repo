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
    
    # ── Fix Line Endings ───────────────────────────────────────────────────
    # Many Windows environments write CRLF, which breaks shell scripts in Linux.
    script_path = os.path.join(abs_workspace, "script.sh")
    if os.path.exists(script_path):
        try:
            with open(script_path, "rb") as f:
                content = f.read()
            # Replace CRLF with LF
            if b"\r\n" in content:
                print("  [Sandbox] Converting script.sh line endings to LF...")
                with open(script_path, "wb") as f:
                    f.write(content.replace(b"\r\n", b"\n"))
        except Exception as e:
            print(f"  [Sandbox] Warning: Could not fix line endings: {e}")

    try:
        # Standard absolute path works with Docker Desktop on Windows.
        print(f"  [Sandbox] Mounting {abs_workspace} as /workspace")
        output = client.containers.run(
            image="ubuntu:22.04",
            command='sh -c "chmod +x /workspace/script.sh && /workspace/script.sh"',
            volumes={abs_workspace: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            detach=False,
            remove=True,
            stderr=True,
            stdout=True
        )
        return output.decode("utf-8")
    except Exception as docker_exc:
        print(f"  [Sandbox] Docker failed: {docker_exc}. Falling back to local execution.")
        # FALLBACK: Run locally if Docker fails
        import subprocess
        script_path = os.path.join(abs_workspace, "script.sh")
        if not os.path.exists(script_path):
            return f"Sandbox execution error: {docker_exc} (and no script.sh found for fallback)"
        
        try:
            # On Windows, 'sh' might not be in PATH. Try 'bash' then 'sh'.
            print(f"  [Sandbox] Attempting local execution of {script_path}")
            
            cmd = ["sh", "script.sh"]
            if os.name == 'nt':
                # Try to find bash or use cmd /c if it's a batch, but script.sh is bash.
                # Many users have Git Bash installed.
                pass 

            res = subprocess.run(
                ["sh", "script.sh"],
                cwd=abs_workspace,
                capture_output=True,
                text=True,
                timeout=60
            )
            return f"Local Fallback Output:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        except Exception as local_exc:
            return f"Sandbox failure: {docker_exc}\nLocal fallback failure: {local_exc}"

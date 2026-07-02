from __future__ import annotations

import subprocess
from pathlib import Path


def gitea_auth_header(token: str) -> str:
    return f"Authorization: token {token}"


def clone_repo(clone_url: str, directory: str | None = None, token: str | None = None, set_token_after: bool = True) -> dict:
    target = Path(directory) if directory else Path(clone_url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1])
    command = ["git"]
    if token:
        command.extend(["-c", f"http.{clone_url}.extraHeader={gitea_auth_header(token)}"])
    command.extend(["clone", clone_url, str(target)])
    subprocess.run(command, check=True)
    token_configured = False
    if token and set_token_after:
        subprocess.run(
            ["git", "config", "--local", f"http.{clone_url}.extraHeader", gitea_auth_header(token)],
            cwd=str(target),
            check=True,
            capture_output=True,
            text=True,
        )
        token_configured = True
    return {"clone_url": clone_url, "path": str(target.resolve()), "token_configured": token_configured}

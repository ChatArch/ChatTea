from __future__ import annotations

import subprocess
from pathlib import Path


def clone_repo(clone_url: str, directory: str | None = None) -> dict:
    target = Path(directory) if directory else Path(clone_url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1])
    command = ["git", "clone", clone_url, str(target)]
    subprocess.run(command, check=True)
    return {"clone_url": clone_url, "path": str(target.resolve())}

from __future__ import annotations

import base64
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from chattea.config import ChatTeaConfig, load_config, normalize_base_url, set_token as save_env_token


@dataclass(frozen=True)
class CredentialTarget:
    protocol: str
    host: str
    path: str

    @property
    def url(self) -> str:
        clean_path = self.path.strip("/")
        return f"{self.protocol}://{self.host}/{clean_path}" if clean_path else f"{self.protocol}://{self.host}"


def _run_git(args: list[str], cwd: str | Path | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def normalize_repo_path(value: str) -> str:
    path = value.strip().strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("Repository must be in owner/name form.")
    return "/".join(parts[-2:])


def credential_target_from_repo(base_url: str, repo: str) -> CredentialTarget:
    parsed = urlparse(normalize_base_url(base_url))
    base_path = parsed.path.strip("/")
    repo_path = normalize_repo_path(repo)
    path = "/".join(part for part in [base_path, repo_path] if part)
    return CredentialTarget(protocol=parsed.scheme, host=parsed.netloc, path=path)


def parse_gitea_remote(remote_url: str) -> CredentialTarget | None:
    value = (remote_url or "").strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if not parsed.hostname:
            return None
        return CredentialTarget(protocol=parsed.scheme, host=parsed.netloc, path=parsed.path.lstrip("/").removesuffix(".git"))
    if value.startswith("git@") and ":" in value:
        host, path = value[4:].split(":", 1)
        return CredentialTarget(protocol="https", host=host, path=path.strip("/").removesuffix(".git"))
    if value.startswith("ssh://"):
        parsed = urlparse(value)
        if not parsed.hostname:
            return None
        return CredentialTarget(protocol="https", host=parsed.netloc.split("@")[-1], path=parsed.path.lstrip("/").removesuffix(".git"))
    return None


def credential_target_variants(target: CredentialTarget) -> list[CredentialTarget]:
    """Return git URL variants that should share the same extraHeader."""
    variants = [target]
    clean_path = target.path.rstrip("/").removesuffix(".git")
    if clean_path and clean_path != target.path:
        variants.append(CredentialTarget(protocol=target.protocol, host=target.host, path=clean_path))
    elif clean_path:
        variants.append(CredentialTarget(protocol=target.protocol, host=target.host, path=f"{clean_path}.git"))
    deduped: list[CredentialTarget] = []
    seen: set[str] = set()
    for variant in variants:
        if variant.url not in seen:
            seen.add(variant.url)
            deduped.append(variant)
    return deduped


def credential_target_from_git_remote(cwd: str | Path | None = None, remote: str = "origin") -> CredentialTarget | None:
    result = _run_git(["remote", "get-url", remote], cwd=cwd)
    if result.returncode != 0:
        return None
    return parse_gitea_remote(result.stdout)


def credential_target_matches_base_url(target: CredentialTarget, base_url: str) -> bool:
    parsed = urlparse(normalize_base_url(base_url))
    return target.protocol == parsed.scheme and target.host == parsed.netloc


def git_extraheader_key(target: CredentialTarget) -> str:
    return f"http.{target.url}.extraHeader"


def gitea_auth_extraheader(token: str) -> str:
    raw = f"x-access-token:{token}".encode("utf-8")
    return "Authorization: Basic " + base64.b64encode(raw).decode("ascii")


def token_from_extraheader(header: str | None) -> str | None:
    value = (header or "").strip()
    prefix = "Authorization: Basic "
    if not value.startswith(prefix):
        return None
    try:
        decoded = base64.b64decode(value[len(prefix) :]).decode("utf-8")
    except Exception:
        return None
    if ":" not in decoded:
        return None
    _username, token = decoded.split(":", 1)
    return token or None


def configure_git_token(target: CredentialTarget, token: str, cwd: str | Path | None = None) -> str:
    key = git_extraheader_key(target)
    _run_git(["config", "--local", key, gitea_auth_extraheader(token)], cwd=cwd, check=True)
    return key


def configure_git_token_variants(target: CredentialTarget, token: str, cwd: str | Path | None = None) -> list[str]:
    return [configure_git_token(variant, token, cwd=cwd) for variant in credential_target_variants(target)]


def read_git_token(target: CredentialTarget | None = None, cwd: str | Path | None = None) -> str | None:
    resolved = target or credential_target_from_git_remote(cwd)
    if resolved is None:
        return None
    for variant in credential_target_variants(resolved):
        result = _run_git(["config", "--local", "--get", git_extraheader_key(variant)], cwd=cwd)
        if result.returncode == 0:
            token = token_from_extraheader(result.stdout)
            if token:
                return token
    return None


def resolve_token(
    token: str | None = None,
    *,
    base_url: str | None = None,
    repo: str | None = None,
    cwd: str | Path | None = None,
    config: ChatTeaConfig | None = None,
) -> str | None:
    if token:
        return token
    loaded = config or load_config()
    resolved_base_url = base_url or loaded.url
    if repo:
        target = credential_target_from_repo(resolved_base_url, repo)
    else:
        target = credential_target_from_git_remote(cwd)
        if target and not credential_target_matches_base_url(target, resolved_base_url):
            target = None
    git_token = read_git_token(target, cwd=cwd) if target else None
    if git_token:
        return git_token
    return loaded.token


def configure_token(
    base_url: str,
    token: str,
    *,
    repo: str | None = None,
    cwd: str | Path | None = None,
    save_env: bool = True,
    configure_git: bool = True,
) -> dict[str, object]:
    normalized_url = normalize_base_url(base_url)
    env_path = save_env_token(normalized_url, token) if save_env else None
    if repo:
        target = credential_target_from_repo(normalized_url, repo)
    else:
        target = credential_target_from_git_remote(cwd)
        if target and not credential_target_matches_base_url(target, normalized_url):
            target = None
    git_key = None
    git_keys: list[str] = []
    if configure_git and target is not None:
        git_keys = configure_git_token_variants(target, token, cwd=cwd)
        git_key = git_keys[0] if git_keys else None
    return {"base_url": normalized_url, "env_path": env_path, "git_key": git_key, "git_keys": git_keys, "git_configured": git_key is not None}


__all__ = [
    "CredentialTarget",
    "configure_git_token",
    "configure_git_token_variants",
    "configure_token",
    "credential_target_from_git_remote",
    "credential_target_from_repo",
    "credential_target_variants",
    "gitea_auth_extraheader",
    "git_extraheader_key",
    "normalize_repo_path",
    "parse_gitea_remote",
    "read_git_token",
    "resolve_token",
    "token_from_extraheader",
]

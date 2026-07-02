from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from chattea.config import ChatTeaConfig, load_config


class GiteaAPIError(RuntimeError):
    pass


class GiteaClient:
    def __init__(self, url: str | None = None, token: str | None = None) -> None:
        config = load_config()
        self.url = (url or config.url).rstrip("/")
        self.token = token if token is not None else config.token

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.url}/api/v1{path}{query}"
        body = None if data is None else json.dumps(data).encode("utf-8")
        headers = {"Accept": "application/json", "User-Agent": "chattea"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        request = Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail)
                if isinstance(payload, dict) and payload.get("message"):
                    detail = str(payload["message"])
            except json.JSONDecodeError:
                pass
            raise GiteaAPIError(f"Gitea API error ({exc.code}) for {path}: {detail}") from exc
        except URLError as exc:
            raise GiteaAPIError(f"Gitea API request failed for {path}: {exc.reason}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return raw.decode("utf-8", errors="replace")

    def version(self) -> dict[str, Any]:
        return self.request("GET", "/version")

    def me(self) -> dict[str, Any]:
        return self.request("GET", "/user")

    def list_repos(self, owner: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if owner:
            return self.request("GET", f"/orgs/{quote(owner)}/repos", params={"limit": limit})
        return self.request("GET", "/user/repos", params={"limit": limit})

    def view_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return self.request("GET", f"/repos/{quote(owner)}/{quote(repo)}")

    def create_repo(
        self,
        name: str,
        owner: str | None = None,
        private: bool = True,
        description: str | None = None,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "private": private,
            "description": description or "",
            "default_branch": default_branch,
            "auto_init": False,
        }
        if owner:
            try:
                me = self.me()
            except GiteaAPIError:
                me = {}
            if owner != me.get("login"):
                return self.request("POST", f"/orgs/{quote(owner)}/repos", data=payload)
        return self.request("POST", "/user/repos", data=payload)

    def migrate_repo(
        self,
        clone_url: str,
        owner: str,
        name: str,
        private: bool = True,
        mirror: bool = False,
        auth_username: str | None = None,
        auth_password: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "clone_addr": clone_url,
            "repo_owner": owner,
            "repo_name": name,
            "private": private,
            "mirror": mirror,
        }
        if auth_username:
            payload["auth_username"] = auth_username
        if auth_password:
            payload["auth_password"] = auth_password
        return self.request("POST", "/repos/migrate", data=payload)


def repo_clone_url(base_url: str, owner: str, repo: str) -> str:
    return f"{base_url.rstrip('/')}/{quote(owner)}/{quote(repo)}.git"

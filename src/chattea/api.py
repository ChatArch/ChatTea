from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from chattea.config import ChatTeaConfig, load_config
from chattea.credentials import resolve_token


class GiteaAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, path: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.path = path


class GiteaClient:
    def __init__(self, url: str | None = None, token: str | None = None) -> None:
        config = load_config()
        self.url = (url or config.url).rstrip("/")
        self.token = resolve_token(token, base_url=self.url, config=config)

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.url}/api/v1{path}{query}"
        body = None if data is None else json.dumps(data).encode("utf-8")
        headers = {"Accept": "application/json", "User-Agent": "chattea"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        if extra_headers:
            headers.update(extra_headers)
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
            raise GiteaAPIError(f"Gitea API error ({exc.code}) for {path}: {detail}", status_code=exc.code, path=path) from exc
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

    @staticmethod
    def basic_auth_header(username: str, password: str) -> dict[str, str]:
        raw = f"{username}:{password}".encode("utf-8")
        return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}

    def list_access_tokens(self, username: str, password: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/users/{quote(username)}/tokens",
            params={"limit": limit},
            extra_headers=self.basic_auth_header(username, password),
        )

    def create_access_token(self, username: str, password: str, name: str, scopes: list[str]) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/users/{quote(username)}/tokens",
            data={"name": name, "scopes": scopes},
            extra_headers=self.basic_auth_header(username, password),
        )

    def delete_access_token(self, username: str, password: str, token_id_or_name: str) -> Any:
        return self.request(
            "DELETE",
            f"/users/{quote(username)}/tokens/{quote(str(token_id_or_name))}",
            extra_headers=self.basic_auth_header(username, password),
        )

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


    @staticmethod
    def _project_params(**kwargs: Any) -> dict[str, Any] | None:
        params = {key: value for key, value in kwargs.items() if value is not None}
        return params or None

    @staticmethod
    def _project_payload(**kwargs: Any) -> dict[str, Any]:
        return {key: value for key, value in kwargs.items() if value is not None}

    def list_repo_projects(self, owner: str, repo: str, state: str = "open", limit: int = 50, page: int | None = None) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/repos/{quote(owner)}/{quote(repo)}/projects",
            params=self._project_params(state=state, limit=limit, page=page),
        )

    def get_repo_project(self, owner: str, repo: str, project_id: int) -> dict[str, Any]:
        return self.request("GET", f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}")

    def create_repo_project(
        self,
        owner: str,
        repo: str,
        title: str,
        description: str | None = None,
        card_type: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/repos/{quote(owner)}/{quote(repo)}/projects",
            data=self._project_payload(title=title, description=description, card_type=card_type),
        )

    def edit_repo_project(
        self,
        owner: str,
        repo: str,
        project_id: int,
        title: str | None = None,
        description: str | None = None,
        state: str | None = None,
        card_type: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "PATCH",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}",
            data=self._project_payload(title=title, description=description, state=state, card_type=card_type),
        )

    def delete_repo_project(self, owner: str, repo: str, project_id: int) -> None:
        return self.request("DELETE", f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}")

    def list_project_columns(self, owner: str, repo: str, project_id: int, limit: int = 50, page: int | None = None) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns",
            params=self._project_params(limit=limit, page=page),
        )

    def create_project_column(self, owner: str, repo: str, project_id: int, title: str, color: str | None = None) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns",
            data=self._project_payload(title=title, color=color),
        )

    def edit_project_column(
        self,
        owner: str,
        repo: str,
        project_id: int,
        column_id: int,
        title: str | None = None,
        color: str | None = None,
        sorting: int | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "PATCH",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns/{column_id}",
            data=self._project_payload(title=title, color=color, sorting=sorting),
        )

    def delete_project_column(self, owner: str, repo: str, project_id: int, column_id: int) -> None:
        return self.request("DELETE", f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns/{column_id}")

    def list_project_column_issues(
        self,
        owner: str,
        repo: str,
        project_id: int,
        column_id: int,
        limit: int = 50,
        page: int | None = None,
    ) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns/{column_id}/issues",
            params=self._project_params(limit=limit, page=page),
        )

    def add_issue_to_project_column(self, owner: str, repo: str, project_id: int, column_id: int, issue_id: int) -> dict[str, Any] | None:
        return self.request("POST", f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns/{column_id}/issues/{issue_id}")

    def remove_issue_from_project_column(self, owner: str, repo: str, project_id: int, column_id: int, issue_id: int) -> None:
        return self.request("DELETE", f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/columns/{column_id}/issues/{issue_id}")

    def move_project_issue(
        self,
        owner: str,
        repo: str,
        project_id: int,
        issue_id: int,
        column_id: int,
        sorting: int | None = None,
    ) -> dict[str, Any] | None:
        return self.request(
            "POST",
            f"/repos/{quote(owner)}/{quote(repo)}/projects/{project_id}/issues/{issue_id}/move",
            data=self._project_payload(column_id=column_id, sorting=sorting),
        )



def repo_clone_url(base_url: str, owner: str, repo: str) -> str:
    return f"{base_url.rstrip('/')}/{quote(owner)}/{quote(repo)}.git"

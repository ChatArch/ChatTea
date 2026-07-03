from __future__ import annotations

import os
import uuid

import pytest

from chattea.api import GiteaClient


pytestmark = pytest.mark.skipif(
    os.getenv("CHATTEA_INTEGRATION") != "1",
    reason="set CHATTEA_INTEGRATION=1 with CHATTEA_TEST_BASE_URL/TOKEN/OWNER to run real Gitea integration tests",
)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"{name} is required for ChatTea integration tests")
    return value


def test_repository_project_board_lifecycle_against_real_gitea():
    base_url = _required_env("CHATTEA_TEST_BASE_URL")
    token = _required_env("CHATTEA_TEST_TOKEN")
    owner = os.getenv("CHATTEA_TEST_OWNER", "gitea_admin")
    repo = f"chattea-project-{uuid.uuid4().hex[:10]}"
    client = GiteaClient(url=base_url, token=token)

    created_repo = None
    project = None
    try:
        created_repo = client.create_repo(name=repo, owner=owner, private=True, description="ChatTea project integration smoke")
        assert created_repo["full_name"].endswith(f"/{repo}")

        issue = client.request("POST", f"/repos/{owner}/{repo}/issues", data={"title": "Project card smoke"})
        issue_id = issue["id"]

        project = client.create_repo_project(owner, repo, "Roadmap", description="Integration smoke", card_type="text_only")
        project_id = project["id"]
        assert project["title"] == "Roadmap"

        todo = client.create_project_column(owner, repo, project_id, "Todo", color="#FF0000")
        done = client.create_project_column(owner, repo, project_id, "Done", color="#00FF00")
        assert todo["title"] == "Todo"
        assert done["title"] == "Done"

        columns = client.list_project_columns(owner, repo, project_id)
        assert {column["title"] for column in columns} >= {"Todo", "Done"}

        client.add_issue_to_project_column(owner, repo, project_id, todo["id"], issue_id)
        todo_issues = client.list_project_column_issues(owner, repo, project_id, todo["id"])
        assert any(item["id"] == issue_id for item in todo_issues)

        client.move_project_issue(owner, repo, project_id, issue_id, done["id"], sorting=0)
        done_issues = client.list_project_column_issues(owner, repo, project_id, done["id"])
        assert any(item["id"] == issue_id for item in done_issues)

        updated = client.edit_project_column(owner, repo, project_id, done["id"], sorting=0)
        assert updated.get("sorting") == 0
    finally:
        if project:
            try:
                client.delete_repo_project(owner, repo, project["id"])
            except Exception:
                pass
        if created_repo:
            try:
                client.request("DELETE", f"/repos/{owner}/{repo}")
            except Exception:
                pass

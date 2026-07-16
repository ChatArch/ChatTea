from __future__ import annotations

from click.testing import CliRunner

from chattea.cli import main
from chattea.commands import notification as notification_commands
from chattea.commands import org as org_commands
from chattea.commands import user as user_commands
from chattea.commands.org import DEFAULT_DEVELOPER_UNITS


class DummyClient:
    def __init__(self) -> None:
        self.calls = []

    def create_user(self, username, email, password, **kwargs):
        self.calls.append(("create_user", username, email, password, kwargs))
        return {"id": 1, "login": username, "email": email, "visibility": kwargs.get("visibility")}

    def delete_user(self, username, **kwargs):
        self.calls.append(("delete_user", username, kwargs))
        return None

    def create_org(self, username, **kwargs):
        self.calls.append(("create_org", username, kwargs))
        return {"id": 2, "username": username, "visibility": kwargs.get("visibility")}

    def create_org_team(self, org, name, **kwargs):
        self.calls.append(("create_org_team", org, name, kwargs))
        return {"id": 3, "name": name, "permission": kwargs.get("permission"), "includes_all_repositories": kwargs.get("includes_all_repositories")}

    def add_team_member(self, team_id, username):
        self.calls.append(("add_team_member", team_id, username))
        return None

    def list_notifications(self, **kwargs):
        self.calls.append(("list_notifications", kwargs))
        return [{"id": 4, "status": "unread", "subject": {"title": "Task"}, "repository": {"full_name": "org/repo"}}]

    def get_notification_thread(self, thread_id):
        self.calls.append(("get_notification_thread", thread_id))
        return {"id": thread_id}

    def mark_notification_thread(self, thread_id, **kwargs):
        self.calls.append(("mark_notification_thread", thread_id, kwargs))
        return None


def test_user_org_notification_commands_are_registered():
    runner = CliRunner()
    for args in [
        ["user", "--help"],
        ["user", "create", "--help"],
        ["org", "--help"],
        ["org", "team", "create", "--help"],
        ["org", "team", "member", "add", "--help"],
        ["notification", "--help"],
        ["notification", "poll", "--help"],
    ]:
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output


def test_user_create_uses_admin_api(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setenv("TASK_USER_PASSWORD", "pw")
    monkeypatch.setattr(user_commands, "client", lambda url=None, token=None: dummy)

    result = CliRunner().invoke(
        main,
        [
            "user",
            "create",
            "--username",
            "task-agent",
            "--email",
            "task-agent@example.invalid",
            "--password-env",
            "TASK_USER_PASSWORD",
            "--visibility",
            "private",
        ],
    )

    assert result.exit_code == 0, result.output
    assert dummy.calls == [
        (
            "create_user",
            "task-agent",
            "task-agent@example.invalid",
            "pw",
            {"full_name": None, "must_change_password": None, "restricted": None, "visibility": "private"},
        )
    ]


def test_org_team_member_flow_builds_expected_api_calls(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(org_commands, "client", lambda url=None, token=None: dummy)
    runner = CliRunner()

    assert runner.invoke(main, ["org", "create", "demo-org"]).exit_code == 0
    assert runner.invoke(main, ["org", "team", "create", "demo-org", "--name", "developers"]).exit_code == 0
    assert runner.invoke(main, ["org", "team", "member", "add", "3", "alice"]).exit_code == 0

    assert dummy.calls == [
        (
            "create_org",
            "demo-org",
            {
                "full_name": None,
                "description": None,
                "email": None,
                "visibility": "private",
                "repo_admin_change_team_access": None,
            },
        ),
        (
            "create_org_team",
            "demo-org",
            "developers",
            {
                "description": None,
                "permission": "write",
                "includes_all_repositories": True,
                "can_create_org_repo": True,
                "units": DEFAULT_DEVELOPER_UNITS,
                "visibility": "private",
            },
        ),
        ("add_team_member", 3, "alice"),
    ]


def test_notification_poll_returns_first_matching_thread(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(notification_commands, "client", lambda url=None, token=None: dummy)

    result = CliRunner().invoke(main, ["notification", "poll", "--max-wait", "1", "--interval", "1", "--json-output"])

    assert result.exit_code == 0, result.output
    assert '"id": 4' in result.output
    assert dummy.calls == [
        (
            "list_notifications",
            {
                "all_": None,
                "status_types": ["unread"],
                "subject_types": ["issue", "pull"],
                "since": None,
                "before": None,
                "limit": 20,
            },
        )
    ]

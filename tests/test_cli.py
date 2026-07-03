from click.testing import CliRunner

from chattea.cli import main


def test_help_lists_first_version_surface():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "set-token" in result.output
    assert "server" in result.output
    assert "repo" in result.output


def test_version_option():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.2.2" in result.output


def test_server_help_lists_lifecycle_commands():
    result = CliRunner().invoke(main, ["server", "--help"])

    assert result.exit_code == 0
    for command in ["install", "init", "serve", "start", "stop", "restart", "status", "logs", "version", "health", "config"]:
        assert command in result.output


def test_repo_help_lists_basic_commands():
    result = CliRunner().invoke(main, ["repo", "--help"])

    assert result.exit_code == 0
    for command in ["list", "view", "create", "clone", "migrate"]:
        assert command in result.output


def test_set_token_writes_config(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    env_path = tmp_path / "arch" / "envs" / "ChatTea" / ".env"

    result = CliRunner().invoke(
        main,
        ["set-token", "--base-url", "http://gitea.local:3000", "--token", "secret-token"],
    )

    assert result.exit_code == 0
    assert "configured: http://gitea.local:3000" in result.output
    assert "secret-token" not in result.output
    assert str(env_path) in result.output
    assert env_path.exists()
    env_text = env_path.read_text()
    assert "CHATTEA_BASE_URL='http://gitea.local:3000'" in env_text
    assert "CHATTEA_TOKEN='secret-token'" in env_text
    assert "CHATTEA_URL" not in env_text


def test_set_token_accepts_legacy_url_option(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))

    result = CliRunner().invoke(
        main,
        ["set-token", "--url", "http://legacy.local:3000", "--token", "secret-token"],
    )

    assert result.exit_code == 0
    env_text = (tmp_path / "arch" / "envs" / "ChatTea" / ".env").read_text()
    assert "CHATTEA_BASE_URL='http://legacy.local:3000'" in env_text


def test_set_token_no_interactive_fails_fast_when_token_missing():
    result = CliRunner().invoke(main, ["set-token", "--base-url", "http://gitea.local:3000", "-I"])

    assert result.exit_code != 0
    assert "token" in result.output.lower()


def test_server_install_no_interactive_fails_fast_when_version_missing():
    result = CliRunner().invoke(main, ["server", "install", "-I"])

    assert result.exit_code != 0
    assert "version" in result.output.lower()


def test_repo_create_no_interactive_fails_fast_when_name_missing():
    result = CliRunner().invoke(main, ["repo", "create", "-I"])

    assert result.exit_code != 0
    assert "name" in result.output.lower()


def test_server_config_commands_read_and_update_app_ini(tmp_path):
    config_path = tmp_path / "app.ini"
    config_path.write_text(
        "[server]\nHTTP_ADDR = 127.0.0.1\nHTTP_PORT = 3000\n\n[security]\nSECRET_KEY = secret\n",
        encoding="utf-8",
    )

    show = CliRunner().invoke(main, ["server", "config", "show", "--config", str(config_path)])
    assert show.exit_code == 0
    assert "HTTP_PORT = 3000" in show.output
    assert "SECRET_KEY = <masked>" in show.output
    assert "secret" not in show.output

    get = CliRunner().invoke(main, ["server", "config", "get", "--config", str(config_path), "--key", "HTTP_PORT", "-I"])
    assert get.exit_code == 0
    assert get.output.strip() == "3000"

    set_result = CliRunner().invoke(
        main,
        ["server", "config", "set", "--config", str(config_path), "--key", "HTTP_PORT", "--value", "3001", "-I"],
    )
    assert set_result.exit_code == 0
    assert "updated:" in set_result.output
    assert "HTTP_PORT = 3001" in config_path.read_text(encoding="utf-8")


def test_repo_list_renders_table(monkeypatch):
    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def list_repos(self, owner=None, limit=50):
            return [{"full_name": "gitea_admin/demo", "private": True, "default_branch": "main", "updated_at": "2026-07-01"}]

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["repo", "list"])

    assert result.exit_code == 0
    assert "gitea_admin/demo" in result.output
    assert "private" in result.output


def test_repo_create_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def create_repo(self, **kwargs):
            captured.update(kwargs)
            return {"full_name": "gitea_admin/demo", "private": kwargs["private"], "html_url": "http://gitea/demo"}

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["repo", "create", "--owner", "gitea_admin", "--name", "demo"])

    assert result.exit_code == 0
    assert "created: gitea_admin/demo (private)" in result.output
    assert captured["owner"] == "gitea_admin"
    assert captured["name"] == "demo"
    assert captured["private"] is True


def test_repo_clone_uses_configured_url_without_git_auth_header(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    CliRunner().invoke(main, ["set-token", "--base-url", "http://gitea.local", "--token", "secret-token"])
    captured = {}

    def fake_clone(clone_url, directory=None):
        captured.update({"clone_url": clone_url, "directory": directory})
        return {"path": "/workspace/demo"}

    monkeypatch.setattr("chattea.commands.repo.git_clone_repo", fake_clone)

    result = CliRunner().invoke(main, ["repo", "clone", "gitea_admin/demo", "demo"])

    assert result.exit_code == 0
    assert "cloned: gitea_admin/demo" in result.output
    assert "token:" not in result.output
    assert captured == {
        "clone_url": "http://gitea.local/gitea_admin/demo.git",
        "directory": "demo",
    }

def test_project_help_lists_single_repo_project_commands():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "project" in result.output

    project = CliRunner().invoke(main, ["project", "--help"])
    assert project.exit_code == 0
    for command in ["list", "view", "create", "edit", "delete", "column", "issue"]:
        assert command in project.output

    column = CliRunner().invoke(main, ["project", "column", "--help"])
    assert column.exit_code == 0
    for command in ["list", "create", "edit", "delete"]:
        assert command in column.output

    issue = CliRunner().invoke(main, ["project", "issue", "--help"])
    assert issue.exit_code == 0
    for command in ["list", "add", "remove", "move"]:
        assert command in issue.output


def test_project_create_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            captured["init"] = {"url": url, "token": token}

        def create_repo_project(self, owner, repo, title, description=None, card_type=None):
            captured.update({"owner": owner, "repo": repo, "title": title, "description": description, "card_type": card_type})
            return {"id": 7, "title": title, "state": "open", "type": "repository"}

    monkeypatch.setattr("chattea.commands.project.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        ["project", "create", "--repo", "gitea_admin/demo", "--title", "Roadmap", "--description", "Plan", "--card-type", "text_only"],
    )

    assert result.exit_code == 0, result.output
    assert "project: 7 Roadmap" in result.output
    assert captured == {
        "init": {"url": None, "token": None},
        "owner": "gitea_admin",
        "repo": "demo",
        "title": "Roadmap",
        "description": "Plan",
        "card_type": "text_only",
    }


def test_project_column_edit_keeps_sorting_zero(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def edit_project_column(self, owner, repo, project_id, column_id, title=None, color=None, sorting=None):
            captured.update({"owner": owner, "repo": repo, "project_id": project_id, "column_id": column_id, "title": title, "color": color, "sorting": sorting})
            return {"id": column_id, "title": title or "Todo", "sorting": sorting, "project_id": project_id}

    monkeypatch.setattr("chattea.commands.project.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        ["project", "column", "edit", "--repo", "gitea_admin/demo", "1", "2", "--title", "Todo", "--sorting", "0"],
    )

    assert result.exit_code == 0, result.output
    assert captured["sorting"] == 0


def test_project_issue_move_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def move_project_issue(self, owner, repo, project_id, issue_id, column_id, sorting=None):
            captured.update({"owner": owner, "repo": repo, "project_id": project_id, "issue_id": issue_id, "column_id": column_id, "sorting": sorting})
            return {"ok": True}

    monkeypatch.setattr("chattea.commands.project.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        ["project", "issue", "move", "--repo", "gitea_admin/demo", "1", "42", "--column", "2", "--sorting", "0"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"owner": "gitea_admin", "repo": "demo", "project_id": 1, "issue_id": 42, "column_id": 2, "sorting": 0}


def test_project_delete_requires_yes_when_non_interactive():
    result = CliRunner().invoke(main, ["project", "delete", "--repo", "gitea_admin/demo", "1", "-I"])

    assert result.exit_code != 0
    assert "--yes" in result.output

def test_project_create_no_interactive_fails_fast_when_required_inputs_missing():
    result = CliRunner().invoke(main, ["project", "create", "-I"])

    assert result.exit_code != 0
    assert "repo" in result.output.lower() or "title" in result.output.lower()


def test_project_list_no_interactive_fails_fast_when_repo_missing():
    result = CliRunner().invoke(main, ["project", "list", "-I"])

    assert result.exit_code != 0
    assert "repo" in result.output.lower()

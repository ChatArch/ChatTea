from click.testing import CliRunner
import subprocess

from chattea.api import GiteaAPIError
from chattea.cli import main


def test_help_lists_first_version_surface():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "set-token" in result.output
    assert "auth" in result.output
    assert "token" in result.output
    assert "api" in result.output
    assert "issue" in result.output
    assert "label" in result.output
    assert "milestone" in result.output
    assert "pr" in result.output
    assert "release" in result.output
    assert "server" in result.output
    assert "repo" in result.output


def test_version_option():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.3.1" in result.output


def test_server_help_lists_lifecycle_commands():
    result = CliRunner().invoke(main, ["server", "--help"])

    assert result.exit_code == 0
    for command in ["install", "init", "bootstrap", "serve", "start", "stop", "restart", "status", "logs", "version", "health", "config", "backup", "migrate"]:
        assert command in result.output


def test_repo_help_lists_basic_commands():
    result = CliRunner().invoke(main, ["repo", "--help"])

    assert result.exit_code == 0
    for command in ["list", "view", "create", "edit", "generate", "clone", "migrate"]:
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


def test_set_token_configures_repo_local_git_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", "https://gitea.local/gitea_admin/demo.git"], cwd=repo, check=True, capture_output=True, text=True)
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(
        main,
        ["set-token", "--base-url", "https://gitea.local", "--token", "secret-token"],
        catch_exceptions=False,
        obj={},
    )

    assert result.exit_code == 0
    assert "git_config: http.https://gitea.local/gitea_admin/demo.extraHeader" in result.output
    assert "secret-token" not in result.output
    header = subprocess.run(
        ["git", "config", "--local", "--get", "http.https://gitea.local/gitea_admin/demo.extraHeader"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Authorization: Basic " in header
    git_suffix_header = subprocess.run(
        ["git", "config", "--local", "--get", "http.https://gitea.local/gitea_admin/demo.git.extraHeader"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Authorization: Basic " in git_suffix_header


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


def test_auth_login_writes_config_like_set_token(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))

    result = CliRunner().invoke(
        main,
        ["auth", "login", "--base-url", "http://gitea.local:3000", "--token", "secret-token"],
    )

    assert result.exit_code == 0
    assert "configured: http://gitea.local:3000" in result.output
    assert "secret-token" not in result.output
    env_text = (tmp_path / "arch" / "envs" / "ChatTea" / ".env").read_text()
    assert "CHATTEA_BASE_URL='http://gitea.local:3000'" in env_text
    assert "CHATTEA_TOKEN='secret-token'" in env_text


def test_server_install_defaults_to_latest_internal_gitea(monkeypatch, tmp_path):
    captured = {}

    def fake_install_gitea(version=None, prefix=None, arch=None, force=False):
        captured.update({"version": version, "prefix": prefix, "arch": arch, "force": force})
        return tmp_path / "bin" / "gitea"

    monkeypatch.setattr("chattea.commands.server.install_gitea", fake_install_gitea)

    result = CliRunner().invoke(main, ["server", "install", "-I"])

    assert result.exit_code == 0, result.output
    assert captured["version"] == "latest"
    assert "installed:" in result.output


def test_server_bootstrap_reads_chatenv_and_masks_password(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("CHATTEA_BASE_URL", "http://gitea.local:3000")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_USER", "root")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_EMAIL", "root@example.invalid")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_PASSWORD", "super-secret-password")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_TOKEN_NAME", "default")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_TOKEN_SCOPES", "all")

    def fake_bootstrap_gitea_server(**kwargs):
        captured.update(kwargs)
        return {
            "binary": tmp_path / "bin" / "gitea",
            "config": tmp_path / "gitea" / "custom" / "conf" / "app.ini",
            "work_path": tmp_path / "gitea",
            "admin_user": kwargs["admin_user"],
            "token": "generat...token",
            "credentials": {"env_path": tmp_path / "arch" / "envs" / "ChatTea" / ".env"},
            "service": None,
        }

    monkeypatch.setattr("chattea.commands.server.bootstrap_gitea_server", fake_bootstrap_gitea_server)

    result = CliRunner().invoke(main, ["server", "bootstrap", "-I"])

    assert result.exit_code == 0, result.output
    assert "super-secret-password" not in result.output
    assert "token: generat...token" in result.output
    assert captured["base_url"] == "http://gitea.local:3000"
    assert captured["admin_user"] == "root"
    assert captured["admin_password"] == "super-secret-password"
    assert captured["admin_email"] == "root@example.invalid"
    assert captured["token_name"] == "default"
    assert captured["token_scopes"] == "all"


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


def test_server_backup_dump_calls_gitea_dump(monkeypatch, tmp_path):
    captured = {}

    def fake_dump(**kwargs):
        captured.update(kwargs)
        return tmp_path / "dump.zip"

    monkeypatch.setattr("chattea.commands.server.dump_gitea_backup", fake_dump)

    result = CliRunner().invoke(main, ["server", "backup", "dump", "--database", "mysql", "--db-only", "--json-output"])

    assert result.exit_code == 0, result.output
    assert '"database": "mysql"' in result.output
    assert captured["database"] == "mysql"
    assert captured["db_only"] is True


def test_server_migrate_mysql_requires_confirmation():
    result = CliRunner().invoke(main, ["server", "migrate", "mysql"])

    assert result.exit_code != 0
    assert "Re-run with --yes" in result.output


def test_server_migrate_mysql_calls_migration(monkeypatch, tmp_path):
    captured = {}

    def fake_migrate(**kwargs):
        captured.update(kwargs)
        return {
            "dump": tmp_path / "dump.zip",
            "sql": tmp_path / "gitea-db.sql",
            "config": tmp_path / "app.ini",
            "config_backup": tmp_path / "app.ini.backup",
            "mysql_socket": tmp_path / "mysql.sock",
            "database": kwargs["database"],
        }

    monkeypatch.setattr("chattea.commands.server.migrate_sqlite_to_mysql", fake_migrate)

    result = CliRunner().invoke(
        main,
        ["server", "migrate", "mysql", "--yes", "--database", "gitea_test", "--mysql-instance", "default", "--skip-gitea-migrate"],
    )

    assert result.exit_code == 0, result.output
    assert "database: gitea_test" in result.output
    assert captured["database"] == "gitea_test"
    assert captured["mysql_instance"] == "default"
    assert captured["run_migrate"] is False


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
    assert captured["template"] is False


def test_repo_create_accepts_explicit_private(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def create_repo(self, **kwargs):
            captured.update(kwargs)
            return {"full_name": "gitea_admin/demo", "private": kwargs["private"]}

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["repo", "create", "--owner", "gitea_admin", "--name", "demo", "--private"])

    assert result.exit_code == 0, result.output
    assert "created: gitea_admin/demo (private)" in result.output
    assert captured["private"] is True


def test_repo_create_rejects_public_and_private_together():
    result = CliRunner().invoke(main, ["repo", "create", "--name", "demo", "--public", "--private"])

    assert result.exit_code != 0
    assert "--public or --private" in result.output


def test_repo_create_template_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def create_repo(self, **kwargs):
            captured.update(kwargs)
            return {"full_name": "gitea_admin/template", "private": kwargs["private"], "template": kwargs["template"]}

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["repo", "create", "--owner", "gitea_admin", "--name", "template", "--template"])

    assert result.exit_code == 0, result.output
    assert "created: gitea_admin/template (private)" in result.output
    assert captured["template"] is True


def test_repo_edit_template_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def edit_repo(self, owner, repo, **kwargs):
            captured.update({"owner": owner, "repo": repo, **kwargs})
            return {"full_name": f"{owner}/{repo}", "template": kwargs["template"], "private": kwargs["private"]}

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["repo", "edit", "gitea_admin/demo", "--template", "--public"])

    assert result.exit_code == 0, result.output
    assert "updated: gitea_admin/demo" in result.output
    assert captured["owner"] == "gitea_admin"
    assert captured["repo"] == "demo"
    assert captured["template"] is True
    assert captured["private"] is False


def test_repo_edit_requires_update_field():
    result = CliRunner().invoke(main, ["repo", "edit", "gitea_admin/demo"])

    assert result.exit_code != 0
    assert "at least one field" in result.output


def test_repo_generate_calls_api(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def generate_repo_from_template(self, template_owner, template_repo, **kwargs):
            captured.update({"template_owner": template_owner, "template_repo": template_repo, **kwargs})
            return {"full_name": f"{kwargs['owner']}/{kwargs['name']}", "private": kwargs["private"]}

    monkeypatch.setattr("chattea.commands.repo.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        [
            "repo",
            "generate",
            "--template",
            "gitea_admin/template",
            "--owner",
            "gitea_admin",
            "--name",
            "generated",
            "--copy-git-content",
            "--copy-labels",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "generated: gitea_admin/generated" in result.output
    assert captured["template_owner"] == "gitea_admin"
    assert captured["template_repo"] == "template"
    assert captured["private"] is True
    assert captured["git_content"] is True
    assert captured["labels"] is True


def test_repo_generate_requires_copy_item():
    result = CliRunner().invoke(
        main,
        ["repo", "generate", "--template", "gitea_admin/template", "--owner", "gitea_admin", "--name", "generated"],
    )

    assert result.exit_code != 0
    assert "at least one template item" in result.output


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
    for command in ["list", "view", "create", "edit", "delete", "column", "card", "issue"]:
        assert command in project.output

    column = CliRunner().invoke(main, ["project", "column", "--help"])
    assert column.exit_code == 0
    for command in ["list", "create", "edit", "delete"]:
        assert command in column.output

    card = CliRunner().invoke(main, ["project", "card", "--help"])
    assert card.exit_code == 0
    for command in ["list", "add", "remove", "move"]:
        assert command in card.output

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


def test_project_card_move_is_primary_alias(monkeypatch):
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
        ["project", "card", "move", "--repo", "gitea_admin/demo", "1", "42", "--column", "2", "--sorting", "0"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"owner": "gitea_admin", "repo": "demo", "project_id": 1, "issue_id": 42, "column_id": 2, "sorting": 0}


def test_api_command_calls_raw_route(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            captured["init"] = {"url": url, "token": token}

        def request(self, method, path, data=None, params=None):
            captured.update({"method": method, "path": path, "data": data, "params": params})
            return {"ok": True}

    monkeypatch.setattr("chattea.commands.api.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        ["api", "/repos/gitea_admin/demo/issues", "--method", "POST", "--data", '{"title":"Bug"}', "--param", "state=open"],
    )

    assert result.exit_code == 0, result.output
    assert '"ok": true' in result.output
    assert captured == {
        "init": {"url": None, "token": None},
        "method": "POST",
        "path": "/repos/gitea_admin/demo/issues",
        "data": {"title": "Bug"},
        "params": {"state": "open"},
    }


def test_token_create_uses_password_env_and_masks_token(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            captured["init"] = {"url": url, "token": token}

        def create_access_token(self, username, password, name, scopes):
            captured.update({"username": username, "password": password, "name": name, "scopes": scopes})
            return {"id": 1, "name": name, "token": "generated-token", "scopes": scopes}

    monkeypatch.setattr("chattea.commands.token.GiteaClient", FakeClient)
    monkeypatch.setenv("GITEA_PASSWORD", "pw")

    result = CliRunner().invoke(
        main,
        ["token", "create", "--base-url", "http://gitea.local", "--username", "gitea_admin", "--password-env", "GITEA_PASSWORD"],
    )

    assert result.exit_code == 0, result.output
    assert "generated-token" not in result.output
    assert "token: generat...token" in result.output
    assert captured == {"init": {"url": "http://gitea.local", "token": ""}, "username": "gitea_admin", "password": "pw", "name": "default", "scopes": ["all"]}


def test_token_bootstrap_creates_token_and_configures_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("GITEA_PASSWORD", "pw")
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            captured["init"] = {"url": url, "token": token}

        def create_access_token(self, username, password, name, scopes):
            captured.update({"username": username, "password": password, "name": name, "scopes": scopes})
            return {"id": 1, "name": name, "sha1": "generated-token", "scopes": scopes}

    monkeypatch.setattr("chattea.commands.token.GiteaClient", FakeClient)

    result = CliRunner().invoke(
        main,
        ["token", "bootstrap", "--base-url", "http://gitea.local", "--username", "gitea_admin", "--password-env", "GITEA_PASSWORD", "--name", "chattea", "--scope", "write:repository,write:issue"],
    )

    assert result.exit_code == 0, result.output
    assert "generated-token" not in result.output
    assert "token_action: created" in result.output
    assert "configured: http://gitea.local" in result.output
    env_text = (tmp_path / "arch" / "envs" / "ChatTea" / ".env").read_text()
    assert "CHATTEA_BASE_URL='http://gitea.local'" in env_text
    assert "CHATTEA_TOKEN='generated-token'" in env_text
    assert captured["scopes"] == ["write:repository", "write:issue"]


def test_repo_collaboration_help_lists_new_command_groups():
    for group, commands in {
        "issue": ["list", "view", "create", "comment", "label", "assign"],
        "label": ["list", "view", "create", "edit", "delete"],
        "milestone": ["list", "view", "create", "edit", "close", "delete"],
        "pr": ["list", "view", "create", "merge", "diff", "patch", "review"],
        "release": ["list", "view", "latest", "create", "asset"],
    }.items():
        result = CliRunner().invoke(main, [group, "--help"])
        assert result.exit_code == 0, result.output
        for command in commands:
            assert command in result.output


def test_repo_collaboration_cli_calls_importable_client(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, url=None, token=None):
            calls.append(("init", url, token))

        def create_issue(self, owner, repo, title, body=None, **kwargs):
            calls.append(("create_issue", owner, repo, title, body, kwargs))
            return {"number": 7, "title": title}

        def get_pull_diff(self, owner, repo, index, diff_type="diff"):
            calls.append(("get_pull_diff", owner, repo, index, diff_type))
            return "diff --git a/demo b/demo"

        def create_release(self, owner, repo, tag_name, **kwargs):
            calls.append(("create_release", owner, repo, tag_name, kwargs))
            return {"id": 3, "tag_name": tag_name}

    monkeypatch.setattr("chattea.commands._shared.GiteaClient", FakeClient)

    issue_result = CliRunner().invoke(main, ["issue", "create", "--repo", "gitea_admin/demo", "--title", "Bug", "--label", "1,2", "--assignee", "root"])
    pr_result = CliRunner().invoke(main, ["pr", "diff", "--repo", "gitea_admin/demo", "5"])
    release_result = CliRunner().invoke(main, ["release", "create", "--repo", "gitea_admin/demo", "--tag", "v1.0.0", "--draft"])

    assert issue_result.exit_code == 0, issue_result.output
    assert pr_result.exit_code == 0, pr_result.output
    assert release_result.exit_code == 0, release_result.output
    assert "created: #7 Bug" in issue_result.output
    assert "diff --git" in pr_result.output
    assert "created: 3 v1.0.0" in release_result.output
    assert ("create_issue", "gitea_admin", "demo", "Bug", None, {"labels": [1, 2], "milestone": None, "assignees": ["root"], "closed": None}) in calls
    assert ("get_pull_diff", "gitea_admin", "demo", 5, "diff") in calls
    assert ("create_release", "gitea_admin", "demo", "v1.0.0", {"name": None, "body": None, "target_commitish": None, "draft": True, "prerelease": None}) in calls


def test_gitea_api_errors_render_without_traceback(monkeypatch):
    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def create_release(self, owner, repo, tag_name, **kwargs):
            raise GiteaAPIError("Gitea API error (422) for /repos/smoke/cli-demo/releases: repo is empty", status_code=422)

    monkeypatch.setattr("chattea.commands._shared.GiteaClient", FakeClient)

    result = CliRunner().invoke(main, ["release", "create", "--repo", "smoke/cli-demo", "--tag", "v0.1.0"])

    assert result.exit_code != 0
    assert "Error: Gitea API error (422)" in result.output
    assert "Traceback" not in result.output

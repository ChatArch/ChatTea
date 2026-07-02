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
    assert "0.2.0" in result.output


def test_server_help_lists_lifecycle_commands():
    result = CliRunner().invoke(main, ["server", "--help"])

    assert result.exit_code == 0
    for command in ["install", "init", "serve", "start", "stop", "restart", "status", "logs", "version", "health"]:
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
    assert "CHATTEA_GITEA_BASE_URL='http://gitea.local:3000'" in env_text
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
    assert "CHATTEA_GITEA_BASE_URL='http://legacy.local:3000'" in env_text


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

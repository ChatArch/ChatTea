from pathlib import Path

from chattea import server as server_ops
from chattea.api import GiteaClient
from chattea.config import (
    ChatTeaConfig,
    ChatTeaEnvConfig,
    DEFAULT_BASE_URL,
    DEFAULT_HTTP_PORT,
    DEFAULT_LISTEN_ADDR,
    default_chattea_home,
    load_config,
    save_config,
)


def test_config_round_trip_uses_chatenv(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    save_config(ChatTeaConfig(url="http://gitea.local:3000", token="token"))

    config = load_config()

    assert config.url == "http://gitea.local:3000"
    assert config.token == "token"
    assert config.home == tmp_path / "arch" / "chattea"
    assert config.gitea_binary == tmp_path / "arch" / "chattea" / "bin" / "gitea"
    assert config.gitea_work_path == tmp_path / "arch" / "chattea" / "gitea"
    env_text = (tmp_path / "arch" / "envs" / "ChatTea" / ".env").read_text(encoding="utf-8")
    assert "CHATTEA_BASE_URL='http://gitea.local:3000'" in env_text
    assert "CHATTEA_URL" not in env_text


def test_legacy_json_config_is_read_when_chatenv_has_no_value(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    path = tmp_path / "config.json"
    path.write_text('{"url": "http://legacy.local", "token": "legacy-token"}', encoding="utf-8")

    config = load_config(path)

    assert config.url == "http://legacy.local"
    assert config.token == "legacy-token"


def test_legacy_chattea_url_env_is_read_but_not_registered(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("CHATTEA_URL", "http://legacy-env.local:3000")

    config = load_config()
    fields = {field.env_key: field for field in ChatTeaEnvConfig.get_fields().values()}

    assert config.url == "http://legacy-env.local:3000"
    assert "CHATTEA_URL" not in fields


def test_default_chattea_home_comes_from_chatarch_home(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))

    assert default_chattea_home() == tmp_path / "arch" / "chattea"


def test_chatenv_provider_fields_are_registered():
    fields = {field.env_key: field for field in ChatTeaEnvConfig.get_fields().values()}

    assert ChatTeaEnvConfig.get_storage_name() == "ChatTea"
    assert ChatTeaEnvConfig._aliases == ["chattea", "gitea", "tea"]
    assert fields["CHATTEA_TOKEN"].is_sensitive is True
    assert set(fields) == {
        "CHATTEA_BASE_URL",
        "CHATTEA_TOKEN",
        "CHATTEA_HOME",
        "CHATTEA_BINARY",
        "CHATTEA_WORK_PATH",
        "CHATTEA_CONFIG",
    }
    assert fields["CHATTEA_BASE_URL"].default == DEFAULT_BASE_URL


def test_chatenv_config_test_validates_values(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))

    ChatTeaEnvConfig.test()

    assert "looks valid" in capsys.readouterr().out


def test_pyproject_registers_chatenv_provider():
    text = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '[project.entry-points."chatenv.configs"]' in text
    assert 'chattea = "chattea.config"' in text


def test_render_app_ini_contains_core_settings():
    rendered = server_ops.render_app_ini(
        Path("/srv/gitea"),
        "git",
        http_port=3001,
        base_url="https://git.example.com",
        listen_addr="127.0.0.1",
    )

    assert "WORK_PATH = /srv/gitea" in rendered
    assert "DOMAIN = git.example.com" in rendered
    assert "HTTP_ADDR = 127.0.0.1" in rendered
    assert "HTTP_PORT = 3001" in rendered
    assert "ROOT_URL = https://git.example.com/" in rendered
    assert "INSTALL_LOCK = true" in rendered
    assert "DB_TYPE = sqlite3" in rendered


def test_write_user_service(tmp_path, monkeypatch):
    service_dir = tmp_path / "systemd" / "user"
    monkeypatch.setattr(server_ops, "service_file_path", lambda service_name=server_ops.DEFAULT_SERVICE_NAME: service_dir / service_name)

    path = server_ops.write_user_service(
        tmp_path / "bin" / "gitea",
        tmp_path / "gitea" / "custom" / "conf" / "app.ini",
        tmp_path / "gitea",
    )

    text = path.read_text()
    assert path.name == "chattea-gitea.service"
    assert "ExecStart=" in text
    assert "gitea web" in text
    assert "--config" in text


def test_create_repo_uses_orgs_endpoint_for_org_owner(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="token")

    def fake_request(method, path, data=None, params=None):
        calls.append((method, path, data, params))
        if path == "/user":
            return {"login": "gitea_admin"}
        return {"full_name": "ChatArch/demo", "private": True}

    monkeypatch.setattr(client, "request", fake_request)

    payload = client.create_repo(name="demo", owner="ChatArch")

    assert payload["full_name"] == "ChatArch/demo"
    assert calls[0][1] == "/user"
    assert calls[1][0] == "POST"
    assert calls[1][1] == "/orgs/ChatArch/repos"


def test_create_repo_uses_user_endpoint_for_current_user(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="token")

    def fake_request(method, path, data=None, params=None):
        calls.append((method, path, data, params))
        if path == "/user":
            return {"login": "gitea_admin"}
        return {"full_name": "gitea_admin/demo", "private": True}

    monkeypatch.setattr(client, "request", fake_request)

    payload = client.create_repo(name="demo", owner="gitea_admin")

    assert payload["full_name"] == "gitea_admin/demo"
    assert calls[1][0] == "POST"
    assert calls[1][1] == "/user/repos"

def test_project_api_methods_use_repo_scoped_endpoints(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="token")

    def fake_request(method, path, data=None, params=None):
        calls.append((method, path, data, params))
        return {"method": method, "path": path}

    monkeypatch.setattr(client, "request", fake_request)

    client.list_repo_projects("gitea_admin", "demo", state="all", limit=25)
    client.get_repo_project("gitea_admin", "demo", 1)
    client.create_repo_project("gitea_admin", "demo", "Roadmap", description="Plan", card_type="text_only")
    client.edit_repo_project("gitea_admin", "demo", 1, title="Next", state="closed")
    client.delete_repo_project("gitea_admin", "demo", 1)
    client.list_project_columns("gitea_admin", "demo", 1)
    client.create_project_column("gitea_admin", "demo", 1, "Todo", color="#FF0000")
    client.edit_project_column("gitea_admin", "demo", 1, 2, sorting=0)
    client.delete_project_column("gitea_admin", "demo", 1, 2)
    client.list_project_column_issues("gitea_admin", "demo", 1, 2, limit=10)
    client.add_issue_to_project_column("gitea_admin", "demo", 1, 2, 42)
    client.remove_issue_from_project_column("gitea_admin", "demo", 1, 2, 42)
    client.move_project_issue("gitea_admin", "demo", 1, 42, 3, sorting=0)

    assert calls == [
        ("GET", "/repos/gitea_admin/demo/projects", None, {"state": "all", "limit": 25}),
        ("GET", "/repos/gitea_admin/demo/projects/1", None, None),
        ("POST", "/repos/gitea_admin/demo/projects", {"title": "Roadmap", "description": "Plan", "card_type": "text_only"}, None),
        ("PATCH", "/repos/gitea_admin/demo/projects/1", {"title": "Next", "state": "closed"}, None),
        ("DELETE", "/repos/gitea_admin/demo/projects/1", None, None),
        ("GET", "/repos/gitea_admin/demo/projects/1/columns", None, {"limit": 50}),
        ("POST", "/repos/gitea_admin/demo/projects/1/columns", {"title": "Todo", "color": "#FF0000"}, None),
        ("PATCH", "/repos/gitea_admin/demo/projects/1/columns/2", {"sorting": 0}, None),
        ("DELETE", "/repos/gitea_admin/demo/projects/1/columns/2", None, None),
        ("GET", "/repos/gitea_admin/demo/projects/1/columns/2/issues", None, {"limit": 10}),
        ("POST", "/repos/gitea_admin/demo/projects/1/columns/2/issues/42", None, None),
        ("DELETE", "/repos/gitea_admin/demo/projects/1/columns/2/issues/42", None, None),
        ("POST", "/repos/gitea_admin/demo/projects/1/issues/42/move", {"column_id": 3, "sorting": 0}, None),
    ]

def test_runtime_dependency_bounds_are_release_reviewed():
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10 test environment
        import tomli as tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = set(data["project"]["dependencies"])

    assert "chatenv>=0.2.2,<0.3.0" in deps
    assert "chatstyle>=0.1.0,<0.2.0" in deps
    assert "click>=8.4.2,<9.0" in deps

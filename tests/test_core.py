from pathlib import Path
import hashlib
import lzma

from chattea import server as server_ops
from chattea.api import GiteaClient
from chattea.commands.api import call_api, parse_json_data, parse_query_params
from chattea.commands.project import add_card, list_cards, move_card, remove_card
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


def test_internal_gitea_asset_urls_use_chatarch_release():
    binary_url, checksum_url = server_ops.internal_gitea_asset_urls("v1.0.0", "amd64")

    assert binary_url == "https://github.com/ChatArch/gitea/releases/download/v1.0.0/gitea-1.0.0-linux-amd64.xz"
    assert checksum_url == f"{binary_url}.sha256"


def test_install_binary_defaults_to_latest_internal_release(monkeypatch, tmp_path):
    compressed = lzma.compress(b"#!/bin/sh\necho chatarch gitea\n")
    checksum = hashlib.sha256(compressed).hexdigest()
    downloads = []

    class FakeResponse:
        def __init__(self, data: bytes):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self.data

    def fake_urlopen(url, timeout=30):
        if url == server_ops.CHATARCH_GITEA_RELEASE_API:
            return FakeResponse(b'{"tag_name":"v1.0.0"}')
        if url.endswith(".sha256"):
            return FakeResponse(f"{checksum}  gitea-1.0.0-linux-amd64.xz\n".encode())
        raise AssertionError(url)

    def fake_urlretrieve(url, filename):
        downloads.append(url)
        Path(filename).write_bytes(compressed)
        return filename, None

    monkeypatch.setattr(server_ops.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(server_ops.urllib.request, "urlretrieve", fake_urlretrieve)

    binary = server_ops.install_binary(prefix=tmp_path, arch="amd64", force=True)

    assert binary == tmp_path / "bin" / "gitea"
    assert binary.read_bytes() == b"#!/bin/sh\necho chatarch gitea\n"
    assert downloads == ["https://github.com/ChatArch/gitea/releases/download/v1.0.0/gitea-1.0.0-linux-amd64.xz"]


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


def test_project_card_functions_are_importable_aliases(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, url=None, token=None):
            pass

        def list_project_column_issues(self, owner, repo, project_id, column_id, limit=50):
            calls.append(("list", owner, repo, project_id, column_id, limit))
            return []

        def add_issue_to_project_column(self, owner, repo, project_id, column_id, issue_id):
            calls.append(("add", owner, repo, project_id, column_id, issue_id))
            return {"ok": True}

        def remove_issue_from_project_column(self, owner, repo, project_id, column_id, issue_id):
            calls.append(("remove", owner, repo, project_id, column_id, issue_id))

        def move_project_issue(self, owner, repo, project_id, issue_id, column_id, sorting=None):
            calls.append(("move", owner, repo, project_id, issue_id, column_id, sorting))
            return {"ok": True}

    monkeypatch.setattr("chattea.commands.project.GiteaClient", FakeClient)

    list_cards("gitea_admin/demo", 1, 2, limit=10)
    add_card("gitea_admin/demo", 1, 2, 42)
    remove_card("gitea_admin/demo", 1, 2, 42)
    move_card("gitea_admin/demo", 1, 42, 3, sorting=0)

    assert calls == [
        ("list", "gitea_admin", "demo", 1, 2, 10),
        ("add", "gitea_admin", "demo", 1, 2, 42),
        ("remove", "gitea_admin", "demo", 1, 2, 42),
        ("move", "gitea_admin", "demo", 1, 42, 3, 0),
    ]


def test_raw_api_helpers(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, url=None, token=None):
            captured["init"] = {"url": url, "token": token}

        def request(self, method, path, data=None, params=None):
            captured.update({"method": method, "path": path, "data": data, "params": params})
            return {"ok": True}

    monkeypatch.setattr("chattea.commands.api.GiteaClient", FakeClient)

    assert parse_query_params(("state=open", "limit=5")) == {"state": "open", "limit": "5"}
    assert parse_json_data('{"title":"Roadmap"}') == {"title": "Roadmap"}
    assert call_api("post", "repos/gitea_admin/demo/issues", {"title": "Roadmap"}, {"draft": False}, url="http://gitea", token="token") == {"ok": True}
    assert captured == {
        "init": {"url": "http://gitea", "token": "token"},
        "method": "POST",
        "path": "/repos/gitea_admin/demo/issues",
        "data": {"title": "Roadmap"},
        "params": {"draft": False},
    }


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

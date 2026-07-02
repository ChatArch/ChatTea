from pathlib import Path

from chattea import server as server_ops
from chattea.api import GiteaClient
from chattea.config import ChatTeaConfig, load_config, save_config


def test_config_round_trip(tmp_path):
    path = tmp_path / "config.json"
    save_config(ChatTeaConfig(url="http://gitea.local", token="token"), path)

    config = load_config(path)

    assert config.url == "http://gitea.local"
    assert config.token == "token"


def test_render_app_ini_contains_core_settings():
    rendered = server_ops.render_app_ini(Path("/srv/gitea"), "git", 3000, "127.0.0.1")

    assert "WORK_PATH = /srv/gitea" in rendered
    assert "HTTP_PORT = 3000" in rendered
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

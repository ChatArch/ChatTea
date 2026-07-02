from pathlib import Path

from chattea import server as server_ops
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

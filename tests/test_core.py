from pathlib import Path
import hashlib
import lzma
import subprocess

from chattea import server as server_ops
from chattea.api import GiteaAPIError, GiteaClient
from chattea.commands.api import call_api, parse_json_data, parse_query_params
from chattea.commands.project import add_card, list_cards, move_card, remove_card
from chattea.commands.server import bootstrap_gitea_server
from chattea.commands.token import bootstrap_access_token
from chattea.credentials import configure_token, git_extraheader_key, read_git_token, resolve_token, token_from_extraheader
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


def _init_git_repo(path: Path, remote_url: str) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=path, check=True, capture_output=True, text=True)


def test_configure_token_writes_repo_local_git_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, "https://gitea.local/gitea_admin/demo.git")

    result = configure_token("https://gitea.local", "repo-token", cwd=repo, save_env=False)

    assert result["git_configured"] is True
    assert result["git_key"] == "http.https://gitea.local/gitea_admin/demo.extraHeader"
    assert result["git_keys"] == [
        "http.https://gitea.local/gitea_admin/demo.extraHeader",
        "http.https://gitea.local/gitea_admin/demo.git.extraHeader",
    ]
    assert read_git_token(cwd=repo) == "repo-token"
    assert token_from_extraheader(subprocess.run(["git", "config", "--local", "--get", str(result["git_key"])], cwd=repo, check=True, capture_output=True, text=True).stdout) == "repo-token"
    assert token_from_extraheader(subprocess.run(["git", "config", "--local", "--get", "http.https://gitea.local/gitea_admin/demo.git.extraHeader"], cwd=repo, check=True, capture_output=True, text=True).stdout) == "repo-token"


def test_gitea_client_resolves_token_from_git_config(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, "https://gitea.local/gitea_admin/demo.git")
    configure_token("https://gitea.local", "repo-token", cwd=repo, save_env=False)
    monkeypatch.chdir(repo)

    client = GiteaClient(url="https://gitea.local")

    assert resolve_token(base_url="https://gitea.local", cwd=repo) == "repo-token"
    assert client.token == "repo-token"


def test_resolve_token_ignores_git_credentials_for_other_hosts(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("CHATTEA_BASE_URL", "https://gitea.local")
    monkeypatch.setenv("CHATTEA_TOKEN", "gitea-token")
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo, "https://github.com/ChatArch/ChatTea.git")
    configure_token("https://github.com", "github-token", repo="ChatArch/ChatTea", cwd=repo, save_env=False)

    assert resolve_token(base_url="https://gitea.local", cwd=repo) == "gitea-token"


def test_legacy_json_config_is_read_when_chatenv_has_no_value(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    path = tmp_path / "config.json"
    path.write_text('{"url": "http://legacy.local", "token": "legacy-token"}', encoding="utf-8")

    config = load_config(path)

    assert config.url == "http://legacy.local"
    assert config.token == "legacy-token"


def test_bootstrap_values_are_read_from_chatenv(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_USER", "root")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_EMAIL", "root@example.invalid")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_ADMIN_PASSWORD", "bootstrap-password")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_TOKEN_NAME", "default")
    monkeypatch.setenv("CHATTEA_BOOTSTRAP_TOKEN_SCOPES", "all")

    config = load_config()

    assert config.bootstrap_admin_user == "root"
    assert config.bootstrap_admin_email == "root@example.invalid"
    assert config.bootstrap_admin_password == "bootstrap-password"
    assert config.bootstrap_token_name == "default"
    assert config.bootstrap_token_scopes == "all"


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
    assert fields["CHATTEA_BOOTSTRAP_ADMIN_PASSWORD"].is_sensitive is True
    assert set(fields) == {
        "CHATTEA_BASE_URL",
        "CHATTEA_TOKEN",
        "CHATTEA_HOME",
        "CHATTEA_BINARY",
        "CHATTEA_WORK_PATH",
        "CHATTEA_CONFIG",
        "CHATTEA_BOOTSTRAP_ADMIN_USER",
        "CHATTEA_BOOTSTRAP_ADMIN_EMAIL",
        "CHATTEA_BOOTSTRAP_ADMIN_PASSWORD",
        "CHATTEA_BOOTSTRAP_TOKEN_NAME",
        "CHATTEA_BOOTSTRAP_TOKEN_SCOPES",
    }
    assert fields["CHATTEA_BASE_URL"].default == DEFAULT_BASE_URL
    assert fields["CHATTEA_BOOTSTRAP_TOKEN_NAME"].default == "default"
    assert fields["CHATTEA_BOOTSTRAP_TOKEN_SCOPES"].default == "all"


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


def test_bootstrap_gitea_server_composes_local_admin_and_credentials(monkeypatch, tmp_path):
    calls = []
    binary = tmp_path / "bin" / "gitea"
    config = tmp_path / "gitea" / "custom" / "conf" / "app.ini"
    work = tmp_path / "gitea"

    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setattr("chattea.commands.server.install_gitea", lambda version=None, prefix=None, force=False: calls.append(("install", version, prefix, force)) or binary)
    monkeypatch.setattr("chattea.commands.server.init_gitea_server", lambda **kwargs: calls.append(("init", kwargs)) or config)
    monkeypatch.setattr("chattea.commands.server.create_admin_user", lambda username, password, email, **kwargs: calls.append(("create-user", username, password, email, kwargs)) or {"username": username})
    monkeypatch.setattr("chattea.commands.server.generate_admin_token", lambda username, **kwargs: calls.append(("generate-token", username, kwargs)) or "generated-token")
    monkeypatch.setattr("chattea.commands.server.configure_credentials", lambda base_url, token: calls.append(("configure", base_url, token)) or {"base_url": base_url, "env_path": tmp_path / "env"})

    result = bootstrap_gitea_server(
        base_url="http://gitea.local:3000",
        admin_user="root",
        admin_password="pw",
        admin_email="root@example.invalid",
        token_name="default",
        token_scopes="all",
        version="latest",
        work_path=work,
    )

    assert result["binary"] == binary
    assert result["config"] == config
    assert result["admin_user"] == "root"
    assert result["token"] == "generat...token"
    assert result["token_source"] == "generated"
    assert calls == [
        ("install", "latest", None, False),
        ("init", {"work_path": work, "config_path": None, "binary": binary, "base_url": "http://gitea.local:3000", "listen_addr": None, "http_port": None, "force": False}),
        ("create-user", "root", "pw", "root@example.invalid", {"binary": binary, "config_path": config, "work_path": work}),
        ("generate-token", "root", {"token_name": "default", "token_scopes": "all", "binary": binary, "config_path": config, "work_path": work}),
        ("configure", "http://gitea.local:3000", "generated-token"),
    ]


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


def test_access_token_api_methods_use_basic_auth(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="")

    def fake_request(method, path, data=None, params=None, extra_headers=None):
        calls.append((method, path, data, params, extra_headers))
        if method == "POST":
            return {"name": data["name"], "token": "generated-token", "scopes": data["scopes"]}
        if method == "GET":
            return [{"id": 1, "name": "chattea"}]
        return None

    monkeypatch.setattr(client, "request", fake_request)

    assert client.create_access_token("gitea_admin", "pw", "chattea", ["all"])["token"] == "generated-token"
    assert client.list_access_tokens("gitea_admin", "pw") == [{"id": 1, "name": "chattea"}]
    assert client.delete_access_token("gitea_admin", "pw", "1") is None

    assert calls[0][0:4] == ("POST", "/users/gitea_admin/tokens", {"name": "chattea", "scopes": ["all"]}, None)
    assert calls[1][0:4] == ("GET", "/users/gitea_admin/tokens", None, {"limit": 50})
    assert calls[2][0:4] == ("DELETE", "/users/gitea_admin/tokens/1", None, None)
    for call in calls:
        assert call[4]["Authorization"].startswith("Basic ")


def test_request_raw_expands_list_query_params(monkeypatch):
    captured = []
    client = GiteaClient(url="http://gitea.local", token="token")

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout=30):
        captured.append(request.full_url)
        return FakeResponse()

    monkeypatch.setattr("chattea.api.urlopen", fake_urlopen)

    client.request_raw("GET", "/notifications", params={"status-types": ["unread", "read"], "limit": 20})

    assert captured == ["http://gitea.local/api/v1/notifications?status-types=unread&status-types=read&limit=20"]


def test_bootstrap_access_token_rotates_existing_default_token(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    calls = []

    def fake_create(username, password, *, name="default", scopes=None, base_url=None):
        calls.append(("create", username, name, scopes, base_url))
        if len([call for call in calls if call[0] == "create"]) == 1:
            raise GiteaAPIError("token already exists", status_code=409, path="/users/root/tokens")
        return {"name": name, "sha1": "rotated-token", "scopes": scopes}

    def fake_delete(username, password, token_id_or_name, *, base_url=None):
        calls.append(("delete", username, token_id_or_name, base_url))

    monkeypatch.setattr("chattea.commands.token.create_access_token", fake_create)
    monkeypatch.setattr("chattea.commands.token.delete_access_token", fake_delete)
    monkeypatch.setattr("chattea.commands.token.configure_credentials", lambda base_url, token: calls.append(("configure", base_url, token)) or {"base_url": base_url})

    result = bootstrap_access_token("root", "pw", base_url="http://gitea.local:3000", name="default", scopes=["all"])

    assert result["token_action"] == "rotated"
    assert result["token"]["sha1"] == "rotated-token"
    assert calls == [
        ("create", "root", "default", ["all"], "http://gitea.local:3000"),
        ("delete", "root", "default", "http://gitea.local:3000"),
        ("create", "root", "default", ["all"], "http://gitea.local:3000"),
        ("configure", "http://gitea.local:3000", "rotated-token"),
    ]


def test_bootstrap_gitea_server_reuses_configured_token_when_admin_token_exists(monkeypatch, tmp_path):
    calls = []
    binary = tmp_path / "bin" / "gitea"
    config = tmp_path / "gitea" / "custom" / "conf" / "app.ini"
    work = tmp_path / "gitea"

    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    save_config(ChatTeaConfig(url="http://gitea.local:3000", token="existing-token"))
    monkeypatch.setattr("chattea.commands.server.install_gitea", lambda version=None, prefix=None, force=False: binary)
    monkeypatch.setattr("chattea.commands.server.init_gitea_server", lambda **kwargs: config)
    monkeypatch.setattr("chattea.commands.server.create_admin_user", lambda username, password, email, **kwargs: calls.append(("create-user", username)) or {"username": username})

    def duplicate_token(username, **kwargs):
        calls.append(("generate-token", username, kwargs))
        import click

        raise click.ClickException("Gitea access token named 'default' already exists.")

    monkeypatch.setattr("chattea.commands.server.generate_admin_token", duplicate_token)
    monkeypatch.setattr("chattea.commands.server.configure_credentials", lambda base_url, token: calls.append(("configure", base_url, token)) or {"base_url": base_url})

    result = bootstrap_gitea_server(
        base_url="http://gitea.local:3000",
        admin_user="root",
        admin_password="pw",
        admin_email="root@example.invalid",
        token_name="default",
        token_scopes="all",
        work_path=work,
    )

    assert result["token"] == "existin...token"
    assert result["token_source"] == "reused"
    assert calls[-1] == ("configure", "http://gitea.local:3000", "existing-token")


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


def test_repo_collaboration_api_methods_use_repo_scoped_endpoints(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="token")

    def fake_request(method, path, data=None, params=None, extra_headers=None):
        calls.append((method, path, data, params))
        if path.endswith(".diff"):
            return "diff --git a/demo b/demo"
        return {"method": method, "path": path}

    monkeypatch.setattr(client, "request", fake_request)

    client.list_issues("gitea_admin", "demo", state="all", limit=10)
    client.get_issue("gitea_admin", "demo", 1)
    client.create_issue("gitea_admin", "demo", "Bug", body="Body", labels=[1], assignees=["root"])
    client.edit_issue("gitea_admin", "demo", 1, state="closed")
    client.list_issue_comments("gitea_admin", "demo", 1)
    client.create_issue_comment("gitea_admin", "demo", 1, "Looks good")
    client.edit_issue_comment("gitea_admin", "demo", 9, "Updated")
    client.delete_issue_comment("gitea_admin", "demo", 9)
    client.add_issue_labels("gitea_admin", "demo", 1, [2])
    client.remove_issue_label("gitea_admin", "demo", 1, 2)
    client.add_issue_assignees("gitea_admin", "demo", 1, ["root"])
    client.list_labels("gitea_admin", "demo")
    client.create_label("gitea_admin", "demo", "bug", "ff0000")
    client.edit_label("gitea_admin", "demo", 1, name="defect")
    client.delete_label("gitea_admin", "demo", 1)
    client.list_milestones("gitea_admin", "demo", state="all")
    client.create_milestone("gitea_admin", "demo", "v1")
    client.edit_milestone("gitea_admin", "demo", 1, state="closed")
    client.delete_milestone("gitea_admin", "demo", 1)
    client.list_pulls("gitea_admin", "demo", state="open")
    client.get_pull("gitea_admin", "demo", 2)
    client.get_pull_diff("gitea_admin", "demo", 2)
    client.create_pull("gitea_admin", "demo", "PR", "feature", "main")
    client.edit_pull("gitea_admin", "demo", 2, state="closed")
    client.merge_pull("gitea_admin", "demo", 2, merge_style="merge")
    client.list_pull_commits("gitea_admin", "demo", 2)
    client.list_pull_files("gitea_admin", "demo", 2)
    client.list_pull_reviews("gitea_admin", "demo", 2)
    client.create_pull_review("gitea_admin", "demo", 2, body="ok")
    client.submit_pull_review("gitea_admin", "demo", 2, 3, event="APPROVE")
    client.list_releases("gitea_admin", "demo")
    client.get_latest_release("gitea_admin", "demo")
    client.create_release("gitea_admin", "demo", "v1.0.0")
    client.edit_release("gitea_admin", "demo", 1, name="v1")
    client.list_release_assets("gitea_admin", "demo", 1)
    client.delete_release_asset("gitea_admin", "demo", 1, 2)

    assert ("GET", "/repos/gitea_admin/demo/issues", None, {"state": "all", "limit": 10}) in calls
    assert ("POST", "/repos/gitea_admin/demo/issues", {"title": "Bug", "body": "Body", "labels": [1], "assignees": ["root"]}, None) in calls
    assert ("PATCH", "/repos/gitea_admin/demo/issues/1", {"state": "closed"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/issues/1/comments", {"body": "Looks good"}, None) in calls
    assert ("PATCH", "/repos/gitea_admin/demo/issues/comments/9", {"body": "Updated"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/issues/1/labels", {"labels": [2]}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/issues/1/assignees", {"assignees": ["root"]}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/labels", {"name": "bug", "color": "ff0000"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/milestones", {"title": "v1"}, None) in calls
    assert ("GET", "/repos/gitea_admin/demo/pulls/2.diff", None, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/pulls", {"title": "PR", "head": "feature", "base": "main"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/pulls/2/merge", {"Do": "merge"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/pulls/2/reviews", {"body": "ok"}, None) in calls
    assert ("POST", "/repos/gitea_admin/demo/releases", {"tag_name": "v1.0.0"}, None) in calls
    assert ("GET", "/repos/gitea_admin/demo/releases/1/assets", None, {"limit": 50}) in calls


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

from __future__ import annotations

import os
import platform
import secrets
import shutil
import subprocess
import urllib.request
from pathlib import Path


DEFAULT_PREFIX = Path("~/.local/share/chattea/gitea").expanduser()
DEFAULT_WORK_PATH = Path("~/gitea").expanduser()
DEFAULT_SERVICE_NAME = "chattea-gitea.service"


def detect_asset_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise ValueError(f"Unsupported architecture: {platform.machine()}")


def install_binary(version: str, prefix: Path = DEFAULT_PREFIX, force: bool = False, arch: str | None = None) -> Path:
    arch = arch or detect_asset_arch()
    bin_dir = prefix.expanduser() / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / "gitea"
    if binary.exists() and not force:
        return binary
    url = f"https://dl.gitea.com/gitea/{version}/gitea-{version}-linux-{arch}"
    temp = binary.with_suffix(".download")
    urllib.request.urlretrieve(url, temp)
    temp.chmod(0o755)
    temp.replace(binary)
    return binary


def generate_secret(size: int = 48) -> str:
    return secrets.token_urlsafe(size)


def render_app_ini(
    work_path: Path,
    run_user: str,
    http_port: int,
    domain: str,
    root_url: str | None = None,
) -> str:
    work = work_path.expanduser()
    root = root_url or f"http://{domain}:{http_port}/"
    return f"""APP_NAME = Gitea
RUN_USER = {run_user}
RUN_MODE = prod
WORK_PATH = {work}

[repository]
ROOT = {work}/data/gitea-repositories
DEFAULT_BRANCH = main

[server]
APP_DATA_PATH = {work}/data
DOMAIN = {domain}
HTTP_ADDR = 0.0.0.0
HTTP_PORT = {http_port}
ROOT_URL = {root}
DISABLE_SSH = true
LFS_START_SERVER = true

[database]
DB_TYPE = sqlite3
PATH = {work}/data/gitea.db
LOG_SQL = false

[session]
PROVIDER = file
PROVIDER_CONFIG = {work}/data/sessions

[log]
MODE = console,file
LEVEL = Info
ROOT_PATH = {work}/log

[security]
INSTALL_LOCK = true
SECRET_KEY = {generate_secret()}
INTERNAL_TOKEN = {generate_secret(64)}
PASSWORD_HASH_ALGO = pbkdf2

[oauth2]
JWT_SECRET = {generate_secret(32)}

[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = false
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false

[mailer]
ENABLED = false

[actions]
ENABLED = false
"""


def init_instance(
    work_path: Path = DEFAULT_WORK_PATH,
    binary: Path | None = None,
    http_port: int = 3000,
    domain: str = "127.0.0.1",
    run_user: str | None = None,
    force: bool = False,
) -> Path:
    work = work_path.expanduser()
    config = work / "custom" / "conf" / "app.ini"
    if config.exists() and not force:
        return config
    for child in [work / "custom" / "conf", work / "data", work / "log"]:
        child.mkdir(parents=True, exist_ok=True)
    user = run_user or os.environ.get("USER") or "git"
    config.write_text(render_app_ini(work, user, http_port, domain), encoding="utf-8")
    config.chmod(0o600)
    if binary:
        run_gitea(binary, ["migrate"], config=config, work_path=work, check=False)
    return config


def run_gitea(
    binary: Path,
    args: list[str],
    config: Path | None = None,
    work_path: Path | None = None,
    check: bool = True,
):
    command = [str(binary.expanduser())]
    if config:
        command.extend(["--config", str(config.expanduser())])
    if work_path:
        command.extend(["--work-path", str(work_path.expanduser())])
    command.extend(args)
    return subprocess.run(command, check=check)


def service_file_path(service_name: str = DEFAULT_SERVICE_NAME) -> Path:
    return Path("~/.config/systemd/user").expanduser() / service_name


def write_user_service(
    binary: Path,
    config: Path,
    work_path: Path,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> Path:
    path = service_file_path(service_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    home = Path.home()
    content = f"""[Unit]
Description=ChatTea managed Gitea service
After=network.target

[Service]
Type=simple
WorkingDirectory={work_path.expanduser()}
ExecStart={binary.expanduser()} web --config {config.expanduser()} --work-path {work_path.expanduser()}
Restart=always
RestartSec=5s
Environment=HOME={home}

[Install]
WantedBy=default.target
"""
    path.write_text(content, encoding="utf-8")
    return path


def systemctl_user(args: list[str], check: bool = True):
    return subprocess.run(["systemctl", "--user", *args], check=check, capture_output=True, text=True)


def journalctl_user(service_name: str = DEFAULT_SERVICE_NAME, follow: bool = False, lines: int = 100):
    command = ["journalctl", "--user", "-u", service_name, "-n", str(lines), "--no-pager"]
    if follow:
        command.append("-f")
    return subprocess.run(command, check=False)


def find_binary(prefix: Path = DEFAULT_PREFIX) -> Path:
    candidate = prefix.expanduser() / "bin" / "gitea"
    if candidate.exists():
        return candidate
    resolved = shutil.which("gitea")
    if resolved:
        return Path(resolved)
    return candidate

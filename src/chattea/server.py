from __future__ import annotations

import hashlib
import json
import lzma
import os
import platform
import shutil
import secrets
import subprocess
import urllib.request
from pathlib import Path

from chattea.config import (
    DEFAULT_BASE_URL,
    DEFAULT_HTTP_PORT,
    DEFAULT_LISTEN_ADDR,
    DEFAULT_SERVICE_NAME,
    base_url_host,
    default_chattea_home,
    default_gitea_work_path,
    normalize_base_url,
    validate_http_port,
    validate_listen_addr,
)

DEFAULT_PREFIX = default_chattea_home()
DEFAULT_WORK_PATH = default_gitea_work_path(DEFAULT_PREFIX)
CHATARCH_GITEA_REPO = "ChatArch/gitea"
CHATARCH_GITEA_RELEASE_API = f"https://api.github.com/repos/{CHATARCH_GITEA_REPO}/releases/latest"
CHATARCH_GITEA_RELEASE_BASE = f"https://github.com/{CHATARCH_GITEA_REPO}/releases/download"
DATABASE_BACKEND_SQLITE = "sqlite3"
DATABASE_BACKEND_MYSQL = "mysql"
SUPPORTED_DATABASE_BACKENDS = (DATABASE_BACKEND_SQLITE, DATABASE_BACKEND_MYSQL)


def detect_asset_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise ValueError(f"Unsupported architecture: {platform.machine()}")


def normalize_release_version(version: str) -> str:
    """Return a release asset version without a leading v prefix."""
    return version[1:] if version.startswith("v") else version


def resolve_latest_internal_gitea_version() -> str:
    """Resolve the latest ChatArch Gitea release version from GitHub."""
    with urllib.request.urlopen(CHATARCH_GITEA_RELEASE_API, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise RuntimeError("Could not resolve latest ChatArch Gitea release tag")
    return normalize_release_version(tag)


def internal_gitea_asset_urls(version: str, arch: str) -> tuple[str, str]:
    """Return ChatArch Gitea binary and checksum asset URLs."""
    asset_version = normalize_release_version(version)
    tag = f"v{asset_version}"
    asset = f"gitea-{asset_version}-linux-{arch}.xz"
    base = f"{CHATARCH_GITEA_RELEASE_BASE}/{tag}"
    return f"{base}/{asset}", f"{base}/{asset}.sha256"


def _expected_sha256(text: str) -> str:
    first = text.strip().split()[0]
    if len(first) != 64:
        raise RuntimeError("Invalid sha256 file for ChatArch Gitea asset")
    return first


def install_binary(version: str | None = None, prefix: Path = DEFAULT_PREFIX, force: bool = False, arch: str | None = None) -> Path:
    arch = arch or detect_asset_arch()
    resolved_version = resolve_latest_internal_gitea_version() if version is None or version in {"", "latest"} else normalize_release_version(version)
    bin_dir = prefix.expanduser() / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / "gitea"
    if binary.exists() and not force:
        return binary
    url, checksum_url = internal_gitea_asset_urls(resolved_version, arch)
    temp_xz = binary.with_suffix(".download.xz")
    temp = binary.with_suffix(".download")
    urllib.request.urlretrieve(url, temp_xz)
    checksum_text = urllib.request.urlopen(checksum_url, timeout=30).read().decode("utf-8")
    expected = _expected_sha256(checksum_text)
    actual = hashlib.sha256(temp_xz.read_bytes()).hexdigest()
    if actual != expected:
        temp_xz.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {url}")
    temp.write_bytes(lzma.decompress(temp_xz.read_bytes()))
    temp_xz.unlink(missing_ok=True)
    temp.chmod(0o755)
    temp.replace(binary)
    return binary


def generate_secret(size: int = 48) -> str:
    return secrets.token_urlsafe(size)


def render_database_section(
    work_path: Path,
    *,
    backend: str = DATABASE_BACKEND_SQLITE,
    host: str | None = None,
    name: str = "gitea",
    user: str = "root",
    password: str = "",
    ssl_mode: str = "disable",
) -> str:
    """Render the Gitea [database] section for a supported backend."""
    work = work_path.expanduser()
    if backend == DATABASE_BACKEND_SQLITE:
        return f"""[database]
DB_TYPE = sqlite3
PATH = {work}/data/gitea.db
LOG_SQL = false
"""
    if backend == DATABASE_BACKEND_MYSQL:
        if not host:
            raise ValueError("MySQL database backend requires a host or socket path")
        return f"""[database]
DB_TYPE = mysql
HOST = {host}
NAME = {name}
USER = {user}
PASSWD = {password}
SSL_MODE = {ssl_mode}
LOG_SQL = false
"""
    raise ValueError(f"Unsupported database backend: {backend}")


def render_app_ini(
    work_path: Path,
    run_user: str,
    http_port: int = DEFAULT_HTTP_PORT,
    base_url: str = DEFAULT_BASE_URL,
    listen_addr: str = DEFAULT_LISTEN_ADDR,
    database_backend: str = DATABASE_BACKEND_SQLITE,
    database_host: str | None = None,
    database_name: str = "gitea",
    database_user: str = "root",
    database_password: str = "",
    database_ssl_mode: str = "disable",
) -> str:
    work = work_path.expanduser()
    root_url = normalize_base_url(base_url) + "/"
    domain = base_url_host(root_url)
    port = validate_http_port(http_port)
    http_addr = validate_listen_addr(listen_addr)
    database_section = render_database_section(
        work,
        backend=database_backend,
        host=database_host,
        name=database_name,
        user=database_user,
        password=database_password,
        ssl_mode=database_ssl_mode,
    ).rstrip()
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
HTTP_ADDR = {http_addr}
HTTP_PORT = {port}
ROOT_URL = {root_url}
DISABLE_SSH = true
LFS_START_SERVER = true

{database_section}

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
    config_path: Path | None = None,
    http_port: int = DEFAULT_HTTP_PORT,
    base_url: str = DEFAULT_BASE_URL,
    listen_addr: str = DEFAULT_LISTEN_ADDR,
    run_user: str | None = None,
    database_backend: str = DATABASE_BACKEND_SQLITE,
    database_host: str | None = None,
    database_name: str = "gitea",
    database_user: str = "root",
    database_password: str = "",
    database_ssl_mode: str = "disable",
    force: bool = False,
) -> Path:
    work = work_path.expanduser()
    config = (config_path or work / "custom" / "conf" / "app.ini").expanduser()
    if config.exists() and not force:
        return config
    for child in [config.parent, work / "data", work / "log"]:
        child.mkdir(parents=True, exist_ok=True)
    user = run_user or os.environ.get("USER") or "git"
    config.write_text(
        render_app_ini(
            work,
            user,
            http_port=http_port,
            base_url=base_url,
            listen_addr=listen_addr,
            database_backend=database_backend,
            database_host=database_host,
            database_name=database_name,
            database_user=database_user,
            database_password=database_password,
            database_ssl_mode=database_ssl_mode,
        ),
        encoding="utf-8",
    )
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


def _read_ini_value(config: Path, section: str, key: str) -> str | None:
    current_section: str | None = None
    for line in config.expanduser().read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
        if current_section != section:
            continue
        existing_key, sep, value = line.partition("=")
        if sep and existing_key.strip().upper() == key.upper():
            return value.strip()
    return None


def chatdata_mysql_service_dependency(config: Path) -> str | None:
    """Return the ChatData MySQL unit required by app.ini, when detectable."""
    if (_read_ini_value(config, "database", "DB_TYPE") or "").lower() != DATABASE_BACKEND_MYSQL:
        return None
    host = _read_ini_value(config, "database", "HOST") or ""
    parts = Path(host).parts
    for index, part in enumerate(parts[:-1]):
        if part == "mysql" and index > 0 and parts[index - 1] == "instances" and index + 1 < len(parts):
            instance = parts[index + 1]
            if instance:
                return f"chatdata-mysql-{instance}.service"
    return None


def write_user_service(
    binary: Path,
    config: Path,
    work_path: Path,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> Path:
    path = service_file_path(service_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    home = Path.home()
    dependency = chatdata_mysql_service_dependency(config)
    after_units = " ".join(["network.target", *([dependency] if dependency else [])])
    requires_line = f"Requires={dependency}\n" if dependency else ""
    content = f"""[Unit]
Description=ChatTea managed Gitea service
After={after_units}
{requires_line}
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

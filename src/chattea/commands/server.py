from __future__ import annotations

import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs

from chattea import server as server_ops
from chattea.api import GiteaAPIError, GiteaClient
from chattea.config import DEFAULT_BASE_URL, DEFAULT_HTTP_PORT, DEFAULT_LISTEN_ADDR, load_config, mask_token
from chattea.credentials import configure_token as configure_credentials
from chattea.commands.token import DEFAULT_TOKEN_NAME, DEFAULT_TOKEN_SCOPES


SENSITIVE_CONFIG_KEYS = {"SECRET_KEY", "INTERNAL_TOKEN", "JWT_SECRET", "LFS_JWT_SECRET"}
SENSITIVE_DATABASE_KEYS = {"PASSWD", "PASSWORD"}
DEFAULT_DATABASE_BACKEND = server_ops.DATABASE_BACKEND_SQLITE
DEFAULT_MYSQL_INSTANCE = "default"
DEFAULT_MYSQL_VERSION = "8.4.6"
DEFAULT_MYSQL_DATABASE = "gitea"
DEFAULT_MYSQL_PORT = 3307
DEFAULT_MYSQL_BIND_ADDRESS = "127.0.0.1"


INSTALL_SCHEMA = CommandSchema(
    name="server install",
    fields=(
        CommandField("version", prompt="ChatArch Gitea version", required=False, default="latest", prompt_if_missing=True),
        CommandField(
            "database_backend",
            prompt="Gitea database backend infra",
            kind="select",
            required=True,
            default=DEFAULT_DATABASE_BACKEND,
            choices=server_ops.SUPPORTED_DATABASE_BACKENDS,
            prompt_if_missing=True,
        ),
    ),
)

INIT_SCHEMA = CommandSchema(
    name="server init",
    fields=(
        CommandField("base_url", prompt="Gitea base URL", required=True, default=DEFAULT_BASE_URL, prompt_if_missing=True),
        CommandField("listen_addr", prompt="Gitea listen address", required=True, default=DEFAULT_LISTEN_ADDR, prompt_if_missing=True),
        CommandField("http_port", prompt="Gitea HTTP port", kind="int", required=True, default=DEFAULT_HTTP_PORT, prompt_if_missing=True),
        CommandField(
            "database_backend",
            prompt="Gitea database backend",
            kind="select",
            required=True,
            default=DEFAULT_DATABASE_BACKEND,
            choices=server_ops.SUPPORTED_DATABASE_BACKENDS,
            prompt_if_missing=True,
        ),
    ),
)

BOOTSTRAP_SCHEMA = CommandSchema(
    name="server bootstrap",
    fields=(
        CommandField("base_url", prompt="Gitea base URL", required=True, default=DEFAULT_BASE_URL, prompt_if_missing=True),
        CommandField("admin_user", prompt="Initial admin username", required=True, default="gitea_admin", prompt_if_missing=True),
        CommandField("admin_email", prompt="Initial admin email", required=True, default="gitea_admin@example.invalid", prompt_if_missing=True),
        CommandField("admin_password", prompt="Initial admin password", required=True, sensitive=True),
        CommandField("token_name", prompt="Initial token name", required=True, default=DEFAULT_TOKEN_NAME, prompt_if_missing=True),
        CommandField("token_scopes", prompt="Initial token scopes", required=True, default=",".join(DEFAULT_TOKEN_SCOPES), prompt_if_missing=True),
        CommandField(
            "database_backend",
            prompt="Gitea database backend",
            kind="select",
            required=True,
            default=DEFAULT_DATABASE_BACKEND,
            choices=server_ops.SUPPORTED_DATABASE_BACKENDS,
            prompt_if_missing=True,
        ),
    ),
)

CONFIG_KEY_SCHEMA = CommandSchema(
    name="server config get",
    fields=(
        CommandField("section", prompt="Gitea app.ini section", required=True, default="server", prompt_if_missing=True),
        CommandField("key", prompt="Gitea app.ini key", required=True),
    ),
)

CONFIG_SET_SCHEMA = CommandSchema(
    name="server config set",
    fields=(
        CommandField("section", prompt="Gitea app.ini section", required=True, default="server", prompt_if_missing=True),
        CommandField("key", prompt="Gitea app.ini key", required=True),
        CommandField("value", prompt="Gitea app.ini value", required=True),
    ),
)

def _required_path(value: Path | None, name: str) -> Path:
    if value is None:
        raise click.ClickException(f"Missing resolved path for {name}.")
    return value


def resolve_gitea_config_path(config_path: Path | None = None) -> Path:
    """Return the managed Gitea app.ini path."""
    config = load_config()
    return config_path or _required_path(config.gitea_config, "CHATTEA_CONFIG")


def read_gitea_config(config_path: Path | None = None, mask_sensitive: bool = True) -> str:
    """Read the managed Gitea app.ini content."""
    path = resolve_gitea_config_path(config_path)
    text = path.read_text(encoding="utf-8")
    return mask_gitea_config(text) if mask_sensitive else text


def mask_gitea_config(text: str) -> str:
    """Mask known sensitive app.ini keys before displaying config content."""
    lines: list[str] = []
    for line in text.splitlines():
        key, sep, _value = line.partition("=")
        if sep and key.strip().upper() in SENSITIVE_CONFIG_KEYS | SENSITIVE_DATABASE_KEYS:
            lines.append(f"{key.rstrip()} = <masked>")
            continue
        lines.append(line)
    return "\n".join(lines)


def get_gitea_config_value(section: str, key: str, config_path: Path | None = None) -> str:
    """Return one value from the managed Gitea app.ini."""
    path = resolve_gitea_config_path(config_path)
    current_section: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
        if current_section != section:
            continue
        existing_key, sep, value = line.partition("=")
        if sep and existing_key.strip() == key:
            return value.strip()
    raise KeyError(f"{section}.{key} not found in {path}")


def set_gitea_config_value(section: str, key: str, value: str, config_path: Path | None = None) -> Path:
    """Set one value in the managed Gitea app.ini, creating the section/key when needed."""
    path = resolve_gitea_config_path(config_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    current_section: str | None = None
    seen_section = False
    updated = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if seen_section and not updated:
                output.append(f"{key} = {value}")
                updated = True
            current_section = stripped[1:-1].strip()
            seen_section = current_section == section
            output.append(line)
            continue
        if seen_section and current_section == section:
            existing_key, sep, _old_value = line.partition("=")
            if sep and existing_key.strip() == key:
                output.append(f"{key} = {value}")
                updated = True
                continue
        output.append(line)

    if not seen_section and not updated:
        if output and output[-1].strip():
            output.append("")
        output.extend([f"[{section}]", f"{key} = {value}"])
    elif seen_section and not updated:
        output.append(f"{key} = {value}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return path


def install_gitea(version: str | None = None, prefix: Path | None = None, arch: str | None = None, force: bool = False) -> Path:
    """Download or reuse the managed ChatArch Gitea binary."""
    config = load_config()
    resolved_prefix = prefix or config.home or server_ops.DEFAULT_PREFIX
    return server_ops.install_binary(version, prefix=resolved_prefix, arch=arch, force=force)


def init_gitea_server(
    work_path: Path | None = None,
    config_path: Path | None = None,
    binary: Path | None = None,
    base_url: str | None = None,
    listen_addr: str | None = None,
    http_port: int | None = None,
    run_user: str | None = None,
    database_backend: str = DEFAULT_DATABASE_BACKEND,
    database_host: str | None = None,
    database_name: str = DEFAULT_MYSQL_DATABASE,
    database_user: str = "root",
    database_password: str = "",
    force: bool = False,
) -> Path:
    """Create or reuse the managed Gitea app.ini."""
    config = load_config()
    return server_ops.init_instance(
        work_path=work_path or _required_path(config.gitea_work_path, "CHATTEA_WORK_PATH"),
        binary=binary or _required_path(config.gitea_binary, "CHATTEA_BINARY"),
        config_path=config_path or _required_path(config.gitea_config, "CHATTEA_CONFIG"),
        base_url=base_url or config.url,
        listen_addr=listen_addr or DEFAULT_LISTEN_ADDR,
        http_port=http_port or DEFAULT_HTTP_PORT,
        run_user=run_user,
        database_backend=database_backend,
        database_host=database_host,
        database_name=database_name,
        database_user=database_user,
        database_password=database_password,
        force=force,
    )


def _password_from_env(env_name: str | None) -> str | None:
    if not env_name:
        return None
    value = os.getenv(env_name)
    if not value:
        raise click.ClickException(f"Environment variable {env_name} is not set or is empty.")
    return value


def _validate_mysql_auth(user: str, password: str) -> None:
    if user.strip().lower() == "root" and password:
        raise click.ClickException("Do not set a MySQL password for the local root user. Use the default passwordless root user or choose a non-root --mysql-user/--user.")


def _raise_for_completed_process(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or f"{action} failed with exit code {result.returncode}").strip()
    raise click.ClickException(detail)


def _wait_for_mysql(mysql_ops, *, name: str, version: str, home: Path | None, timeout: int = 30) -> dict[str, object]:
    deadline = time.time() + timeout
    last_ping: dict[str, object] | None = None
    while time.time() < deadline:
        last_ping = mysql_ops.ping(name=name, version=version, home=home)
        if last_ping.get("ok"):
            return last_ping
        time.sleep(1)
    detail = last_ping.get("stderr") if last_ping else "MySQL did not become ready"
    raise click.ClickException(str(detail or "MySQL did not become ready"))


def prepare_database_backend(
    *,
    backend: str = DEFAULT_DATABASE_BACKEND,
    mysql_instance: str = DEFAULT_MYSQL_INSTANCE,
    mysql_version: str = DEFAULT_MYSQL_VERSION,
    mysql_home: Path | None = None,
    mysql_database: str = DEFAULT_MYSQL_DATABASE,
    mysql_user: str = "root",
    mysql_password: str = "",
    mysql_port: int = DEFAULT_MYSQL_PORT,
    mysql_bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
    install_mysql: bool = True,
    install_mysql_service: bool = True,
    start_mysql: bool = True,
) -> dict[str, object]:
    """Prepare the selected database backend and return app.ini database settings."""
    if backend == server_ops.DATABASE_BACKEND_SQLITE:
        return {"backend": backend, "gitea": {"database_backend": backend}, "mysql": None}
    if backend != server_ops.DATABASE_BACKEND_MYSQL:
        raise click.ClickException(f"Unsupported database backend: {backend}")

    _validate_mysql_auth(mysql_user, mysql_password)
    mysql_ops = _chatdata_mysql_module()
    result: dict[str, object] = {"backend": backend}
    if install_mysql:
        result["install"] = mysql_ops.install_mysql(version=mysql_version, home=mysql_home)
    result["instance"] = mysql_ops.init_instance(
        name=mysql_instance,
        version=mysql_version,
        home=mysql_home,
        port=mysql_port,
        bind_address=mysql_bind_address,
    )
    if install_mysql_service:
        result["service"] = mysql_ops.install_service(name=mysql_instance, version=mysql_version, home=mysql_home)
    if start_mysql:
        _raise_for_completed_process(mysql_ops.systemctl_user(mysql_instance, "start"), f"start {mysql_instance}")
    result["ping"] = _wait_for_mysql(mysql_ops, name=mysql_instance, version=mysql_version, home=mysql_home)
    mysql_ops.create_database(mysql_database, name=mysql_instance, version=mysql_version, home=mysql_home)
    if hasattr(mysql_ops, "ensure_database_user"):
        mysql_ops.ensure_database_user(mysql_database, user=mysql_user, password=mysql_password, name=mysql_instance, version=mysql_version, home=mysql_home)
    elif mysql_user != "root" or mysql_password:
        raise click.ClickException("This ChatData version cannot create MySQL users. Use --mysql-user root or upgrade ChatData.")
    layout = mysql_ops.mysql_layout(name=mysql_instance, version=mysql_version, home=mysql_home)
    result["layout"] = mysql_ops.export_layout(name=mysql_instance, version=mysql_version, home=mysql_home)
    return {
        "backend": backend,
        "gitea": {
            "database_backend": backend,
            "database_host": str(layout.socket),
            "database_name": mysql_database,
            "database_user": mysql_user,
            "database_password": mysql_password,
        },
        "mysql": result,
    }


def _gitea_admin_base_command(binary: Path, config_path: Path, work_path: Path) -> list[str]:
    return [str(binary.expanduser()), "--config", str(config_path.expanduser()), "--work-path", str(work_path.expanduser()), "admin", "user"]


def _safe_process_detail(exc: subprocess.CalledProcessError, *secrets: str | None) -> str:
    detail = exc.stderr or exc.stdout or str(exc)
    for secret in secrets:
        if secret:
            detail = detail.replace(secret, "[REDACTED]")
    return detail.strip()


def _looks_already_exists(detail: str) -> bool:
    lowered = detail.lower()
    return "already exists" in lowered or "already been used" in lowered or ("already" in lowered and "exist" in lowered)


def _looks_token_name_exists(detail: str) -> bool:
    lowered = detail.lower()
    return "token" in lowered and _looks_already_exists(lowered)


def _configured_token_for_base_url(base_url: str) -> str | None:
    config = load_config()
    if config.token and config.url.rstrip("/") == base_url.rstrip("/"):
        return config.token
    return None


def create_admin_user(
    username: str,
    password: str,
    email: str,
    *,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
    must_change_password: bool = False,
) -> dict[str, str]:
    """Create the initial local Gitea admin through the Gitea admin CLI."""
    resolved = load_config()
    target_binary = binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY")
    target_config = config_path or _required_path(resolved.gitea_config, "CHATTEA_CONFIG")
    target_work = work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH")
    command = [
        *_gitea_admin_base_command(target_binary, target_config, target_work),
        "create",
        "--username",
        username,
        "--password",
        password,
        "--email",
        email,
        "--admin",
        f"--must-change-password={'true' if must_change_password else 'false'}",
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = _safe_process_detail(exc, password)
        if not _looks_already_exists(detail):
            raise click.ClickException(detail) from exc
    return {"username": username, "email": email}


def generate_admin_token(
    username: str,
    *,
    token_name: str = DEFAULT_TOKEN_NAME,
    token_scopes: str = ",".join(DEFAULT_TOKEN_SCOPES),
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
) -> str:
    """Generate an initial access token through the local Gitea admin CLI."""
    resolved = load_config()
    target_binary = binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY")
    target_config = config_path or _required_path(resolved.gitea_config, "CHATTEA_CONFIG")
    target_work = work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH")
    try:
        result = subprocess.run(
            [
                *_gitea_admin_base_command(target_binary, target_config, target_work),
                "generate-access-token",
                "--username",
                username,
                "--token-name",
                token_name,
                "--scopes",
                token_scopes,
                "--raw",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = _safe_process_detail(exc)
        if _looks_token_name_exists(detail):
            raise click.ClickException(f"Gitea access token named {token_name!r} already exists.") from exc
        raise click.ClickException(detail) from exc
    token = result.stdout.strip()
    if not token:
        raise click.ClickException("Gitea admin CLI did not return a token.")
    return token


def bootstrap_gitea_server(
    *,
    base_url: str,
    admin_user: str,
    admin_password: str,
    admin_email: str,
    token_name: str = DEFAULT_TOKEN_NAME,
    token_scopes: str = ",".join(DEFAULT_TOKEN_SCOPES),
    version: str | None = "latest",
    prefix: Path | None = None,
    work_path: Path | None = None,
    config_path: Path | None = None,
    binary: Path | None = None,
    listen_addr: str | None = None,
    http_port: int | None = None,
    database_backend: str = DEFAULT_DATABASE_BACKEND,
    mysql_instance: str = DEFAULT_MYSQL_INSTANCE,
    mysql_version: str = DEFAULT_MYSQL_VERSION,
    mysql_home: Path | None = None,
    mysql_database: str = DEFAULT_MYSQL_DATABASE,
    mysql_user: str = "root",
    mysql_password: str = "",
    mysql_port: int = DEFAULT_MYSQL_PORT,
    mysql_bind_address: str = DEFAULT_MYSQL_BIND_ADDRESS,
    install_mysql: bool = True,
    install_mysql_service: bool = True,
    start_mysql: bool = True,
    force: bool = False,
    start_service: bool = False,
) -> dict[str, object]:
    """Bootstrap a local ChatArch Gitea and configure ChatTea credentials."""
    installed_binary = binary or install_gitea(version, prefix=prefix, force=force)
    database = prepare_database_backend(
        backend=database_backend,
        mysql_instance=mysql_instance,
        mysql_version=mysql_version,
        mysql_home=mysql_home,
        mysql_database=mysql_database,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_port=mysql_port,
        mysql_bind_address=mysql_bind_address,
        install_mysql=install_mysql,
        install_mysql_service=install_mysql_service,
        start_mysql=start_mysql,
    )
    resolved_config = init_gitea_server(
        work_path=work_path,
        config_path=config_path,
        binary=installed_binary,
        base_url=base_url,
        listen_addr=listen_addr,
        http_port=http_port,
        **database["gitea"],
        force=force,
    )
    resolved = load_config()
    resolved_work = work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH")
    create_admin_user(admin_user, admin_password, admin_email, binary=installed_binary, config_path=resolved_config, work_path=resolved_work)
    try:
        token = generate_admin_token(admin_user, token_name=token_name, token_scopes=token_scopes, binary=installed_binary, config_path=resolved_config, work_path=resolved_work)
        token_source = "generated"
    except click.ClickException as exc:
        if not _looks_token_name_exists(str(exc)):
            raise
        token = _configured_token_for_base_url(base_url)
        if not token:
            raise click.ClickException(
                f"Gitea access token named {token_name!r} already exists, but no existing CHATTEA_TOKEN is configured for {base_url}. "
                "Use a different --token-name or run chattea set-token with the existing token."
            ) from exc
        token_source = "reused"
    credentials = configure_credentials(base_url, token)
    service = start_gitea_service(binary=installed_binary, config_path=resolved_config, work_path=resolved_work) if start_service else None
    return {
        "binary": installed_binary,
        "config": resolved_config,
        "work_path": resolved_work,
        "admin_user": admin_user,
        "token": mask_token(token),
        "token_name": token_name,
        "token_scopes": token_scopes,
        "token_source": token_source,
        "database_backend": database["backend"],
        "mysql": database["mysql"],
        "credentials": credentials,
        "service": service,
    }


def serve_gitea(binary: Path | None = None, config_path: Path | None = None, work_path: Path | None = None):
    """Run the managed Gitea instance in the foreground."""
    resolved = load_config()
    return server_ops.run_gitea(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY"),
        ["web"],
        config=config_path or _required_path(resolved.gitea_config, "CHATTEA_CONFIG"),
        work_path=work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH"),
    )


def start_gitea_service(binary: Path | None = None, config_path: Path | None = None, work_path: Path | None = None) -> Path:
    """Install and start the managed user-level systemd service."""
    resolved = load_config()
    service_file = server_ops.write_user_service(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY"),
        config_path or _required_path(resolved.gitea_config, "CHATTEA_CONFIG"),
        work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH"),
    )
    server_ops.systemctl_user(["daemon-reload"])
    server_ops.systemctl_user(["enable", "--now", server_ops.DEFAULT_SERVICE_NAME])
    return service_file


def stop_gitea_service() -> None:
    """Stop the managed user-level systemd service."""
    server_ops.systemctl_user(["stop", server_ops.DEFAULT_SERVICE_NAME])


def restart_gitea_service() -> None:
    """Restart the managed user-level systemd service."""
    server_ops.systemctl_user(["restart", server_ops.DEFAULT_SERVICE_NAME])


def status_gitea_service():
    """Return the managed user-level systemd service status."""
    return server_ops.systemctl_user(["--no-pager", "--full", "status", server_ops.DEFAULT_SERVICE_NAME], check=False)


def logs_gitea_service(follow: bool = False, lines: int = 100):
    """Return journalctl output for the managed user-level systemd service."""
    return server_ops.journalctl_user(server_ops.DEFAULT_SERVICE_NAME, follow=follow, lines=lines)


def gitea_version(binary: Path | None = None, url: str | None = None) -> dict | None:
    """Read the Gitea server version, falling back to the binary when needed."""
    config = load_config()
    if url:
        return GiteaClient(url=url).version()
    if binary:
        server_ops.run_gitea(binary, ["--version"])
        return None
    try:
        return GiteaClient(url=config.url, token=config.token).version()
    except GiteaAPIError:
        server_ops.run_gitea(_required_path(config.gitea_binary, "CHATTEA_BINARY"), ["--version"])
        return None


def check_gitea_health(url: str | None = None) -> dict:
    """Check whether the configured Gitea API endpoint is reachable."""
    config = load_config()
    target_url = (url or config.url).rstrip("/")
    payload = GiteaClient(url=target_url).version()
    return {"ok": True, "url": target_url, "version": payload.get("version")}


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def dump_gitea_backup(
    *,
    output: Path | None = None,
    database: str | None = None,
    tempdir: Path | None = None,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
    db_only: bool = False,
) -> Path:
    """Run `gitea dump` for backup or cross-database SQL export."""
    resolved = load_config()
    target_binary = binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY")
    target_config = config_path or _required_path(resolved.gitea_config, "CHATTEA_CONFIG")
    target_work = work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH")
    dump_database = database or get_gitea_config_value("database", "DB_TYPE", config_path=target_config)
    backup_dir = target_work / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target_output = (output or backup_dir / f"gitea-dump-{dump_database}-{_timestamp()}.zip").expanduser()
    target_output.parent.mkdir(parents=True, exist_ok=True)
    target_tempdir = (tempdir or backup_dir / "tmp").expanduser()
    target_tempdir.mkdir(parents=True, exist_ok=True)
    args = ["dump", "--file", str(target_output), "--tempdir", str(target_tempdir), "--database", dump_database]
    if db_only:
        args.extend([
            "--skip-repository",
            "--skip-log",
            "--skip-custom-dir",
            "--skip-lfs-data",
            "--skip-attachment-data",
            "--skip-package-data",
            "--skip-index",
        ])
    server_ops.run_gitea(target_binary, args, config=target_config, work_path=target_work)
    return target_output


def extract_gitea_dump_sql(dump_path: Path, output_dir: Path | None = None) -> Path:
    """Extract gitea-db.sql from a Gitea dump archive."""
    target_dir = (output_dir or dump_path.with_suffix(".extract")).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dump_path.expanduser()) as archive:
        sql_members = [name for name in archive.namelist() if name.endswith("gitea-db.sql")]
        if not sql_members:
            raise click.ClickException(f"No gitea-db.sql found in {dump_path}")
        sql_name = sql_members[0]
        target = target_dir / "gitea-db.sql"
        target.write_bytes(archive.read(sql_name))
        return target


def _backup_file(path: Path) -> Path:
    backup = path.with_name(f"{path.name}.backup-{_timestamp()}")
    backup.write_bytes(path.read_bytes())
    backup.chmod(0o600)
    return backup


def configure_gitea_mysql_database(
    *,
    config_path: Path | None = None,
    host: str,
    database: str,
    user: str = "root",
    password: str = "",
    backup: bool = True,
) -> dict[str, object]:
    """Switch the managed Gitea app.ini [database] section to MySQL."""
    target_config = resolve_gitea_config_path(config_path)
    backup_path = _backup_file(target_config) if backup else None
    for key, value in {
        "DB_TYPE": "mysql",
        "HOST": host,
        "NAME": database,
        "USER": user,
        "PASSWD": password,
        "SSL_MODE": "disable",
        "LOG_SQL": "false",
    }.items():
        set_gitea_config_value("database", key, value, config_path=target_config)
    return {"config": target_config, "backup": backup_path, "database": database, "host": host, "user": user}


def _chatdata_mysql_module():
    try:
        from chatdata import mysql as mysql_ops
    except ImportError as exc:
        raise click.ClickException("ChatData is required for MySQL backend support. Install ChatData or use `pip install -e /path/to/ChatData` first.") from exc
    return mysql_ops


def migrate_sqlite_to_mysql(
    *,
    mysql_instance: str = "default",
    mysql_version: str = "8.4.6",
    mysql_home: Path | None = None,
    database: str = "gitea",
    user: str = "root",
    password: str = "",
    dump_dir: Path | None = None,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
    stop_service: bool = False,
    restart_service: bool = False,
    run_migrate: bool = True,
) -> dict[str, object]:
    """Migrate the managed Gitea database from SQLite to a ChatData MySQL instance."""
    _validate_mysql_auth(user, password)
    mysql_ops = _chatdata_mysql_module()
    resolved = load_config()
    target_work = work_path or _required_path(resolved.gitea_work_path, "CHATTEA_WORK_PATH")
    migration_dir = (dump_dir or target_work / "backups" / f"sqlite-to-mysql-{_timestamp()}").expanduser()
    migration_dir.mkdir(parents=True, exist_ok=True)
    if stop_service:
        server_ops.systemctl_user(["stop", server_ops.DEFAULT_SERVICE_NAME], check=False)
    dump_path = dump_gitea_backup(
        output=migration_dir / "gitea-dump-mysql.zip",
        database="mysql",
        tempdir=migration_dir / "tmp",
        binary=binary,
        config_path=config_path,
        work_path=target_work,
        db_only=True,
    )
    sql_path = extract_gitea_dump_sql(dump_path, migration_dir)
    mysql_ops.create_database(database, name=mysql_instance, version=mysql_version, home=mysql_home)
    if hasattr(mysql_ops, "ensure_database_user"):
        mysql_ops.ensure_database_user(database, user=user, password=password, name=mysql_instance, version=mysql_version, home=mysql_home)
    elif user != "root" or password:
        raise click.ClickException("This ChatData version cannot create MySQL users. Use --user root or upgrade ChatData.")
    mysql_ops.query_file(sql_path, name=mysql_instance, version=mysql_version, home=mysql_home, database=database)
    layout = mysql_ops.mysql_layout(name=mysql_instance, version=mysql_version, home=mysql_home)
    config_result = configure_gitea_mysql_database(
        config_path=config_path,
        host=str(layout.socket),
        database=database,
        user=user,
        password=password,
        backup=True,
    )
    if run_migrate:
        resolved_config = config_result["config"]
        server_ops.run_gitea(binary or _required_path(resolved.gitea_binary, "CHATTEA_BINARY"), ["migrate"], config=resolved_config, work_path=target_work)
    if restart_service:
        server_ops.systemctl_user(["start", server_ops.DEFAULT_SERVICE_NAME], check=False)
    return {
        "dump": dump_path,
        "sql": sql_path,
        "config": config_result["config"],
        "config_backup": config_result["backup"],
        "mysql_socket": layout.socket,
        "database": database,
        "stopped_service": stop_service,
        "restarted_service": restart_service,
    }


@click.group(name="server")
def server_group() -> None:
    """Install and manage a local Gitea server."""


@server_group.group(name="config")
def config_group() -> None:
    """Inspect and edit the managed Gitea app.ini."""


@server_group.group(name="backup")
def backup_group() -> None:
    """Back up or export the managed Gitea instance."""


@backup_group.command(name="dump")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Dump archive path. Defaults to CHATTEA_WORK_PATH/backups.")
@click.option("--database", default=None, type=click.Choice(["sqlite3", "mysql", "postgres", "mssql"]), help="SQL syntax for database dump. Defaults to app.ini database.DB_TYPE.")
@click.option("--tempdir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Temporary directory for gitea dump.")
@click.option("--db-only", is_flag=True, help="Skip repositories, custom dir, logs, packages, attachments and indexes.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
@click.option("--json-output", is_flag=True)
def backup_dump(
    output: Path | None,
    database: str | None,
    tempdir: Path | None,
    db_only: bool,
    binary: Path | None,
    config_path: Path | None,
    work_path: Path | None,
    json_output: bool,
) -> None:
    """Run Gitea dump for backup or cross-database SQL export."""
    try:
        dump_path = dump_gitea_backup(output=output, database=database, tempdir=tempdir, binary=binary, config_path=config_path, work_path=work_path, db_only=db_only)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise click.ClickException(str(exc)) from exc
    payload = {"dump": dump_path, "database": database or "auto", "db_only": db_only}
    click.echo(json.dumps(payload, indent=2, default=str) if json_output else f"dump: {dump_path}")


@server_group.group(name="migrate")
def migrate_group() -> None:
    """Migrate the managed Gitea backend."""


@migrate_group.command(name="mysql")
@click.option("--mysql-instance", default="default", show_default=True, help="ChatData MySQL instance name.")
@click.option("--mysql-version", default="8.4.6", show_default=True, help="ChatData MySQL runtime version.")
@click.option("--mysql-home", type=click.Path(file_okay=False, path_type=Path), default=None, help="ChatData home override. Defaults to CHATDATA_HOME.")
@click.option("--database", default="gitea", show_default=True, help="Target MySQL database name.")
@click.option("--user", default="root", show_default=True, help="Target MySQL user for Gitea app.ini.")
@click.option("--password-env", default=None, help="Environment variable containing the MySQL password. Empty by default for local insecure dev instance.")
@click.option("--dump-dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Directory for migration dump and extracted SQL.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
@click.option("--stop-service", is_flag=True, help="Stop the managed Gitea user service before dumping.")
@click.option("--restart-service", is_flag=True, help="Start the managed Gitea user service after migration.")
@click.option("--gitea-migrate/--skip-gitea-migrate", "run_migrate", default=True, show_default=True, help="Run `gitea migrate` after switching app.ini.")
@click.option("--yes", is_flag=True, help="Confirm app.ini migration to MySQL.")
@click.option("--json-output", is_flag=True)
def migrate_mysql(
    mysql_instance: str,
    mysql_version: str,
    mysql_home: Path | None,
    database: str,
    user: str,
    password_env: str | None,
    dump_dir: Path | None,
    binary: Path | None,
    config_path: Path | None,
    work_path: Path | None,
    stop_service: bool,
    restart_service: bool,
    run_migrate: bool,
    yes: bool,
    json_output: bool,
) -> None:
    """Migrate the managed Gitea SQLite database into a ChatData MySQL instance."""
    if not yes:
        raise click.ClickException("This changes the managed Gitea app.ini database backend. Re-run with --yes after taking a backup.")
    password = _password_from_env(password_env) or ""
    try:
        result = migrate_sqlite_to_mysql(
            mysql_instance=mysql_instance,
            mysql_version=mysql_version,
            mysql_home=mysql_home,
            database=database,
            user=user,
            password=password,
            dump_dir=dump_dir,
            binary=binary,
            config_path=config_path,
            work_path=work_path,
            stop_service=stop_service,
            restart_service=restart_service,
            run_migrate=run_migrate,
        )
    except (OSError, subprocess.CalledProcessError, click.ClickException) as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        safe = {key: value for key, value in result.items() if key != "password"}
        click.echo(json.dumps(safe, indent=2, default=str))
        return
    click.echo(f"dump: {result['dump']}")
    click.echo(f"sql: {result['sql']}")
    click.echo(f"config: {result['config']}")
    click.echo(f"config_backup: {result['config_backup']}")
    click.echo(f"mysql_socket: {result['mysql_socket']}")
    click.echo(f"database: {result['database']}")


@config_group.command(name="path")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
def config_path_command(config_path: Path | None) -> None:
    """Show the managed Gitea app.ini path."""
    click.echo(resolve_gitea_config_path(config_path))


@config_group.command(name="show")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--no-mask", is_flag=True, help="Show sensitive app.ini values in plain text.")
def config_show(config_path: Path | None, no_mask: bool) -> None:
    """Show the managed Gitea app.ini content."""
    try:
        click.echo(read_gitea_config(config_path, mask_sensitive=not no_mask))
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc


@config_group.command(name="get")
@click.option("--section", default=None, help="Gitea app.ini section, for example server.")
@click.option("--key", default=None, help="Gitea app.ini key, for example HTTP_PORT.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@add_interactive_option
def config_get(section: str | None, key: str | None, config_path: Path | None, interactive: bool | None) -> None:
    """Read one value from the managed Gitea app.ini."""
    provided_section = section if interactive is True else section or "server"
    values = resolve_command_inputs(
        schema=CONFIG_KEY_SCHEMA,
        provided={"section": provided_section, "key": key},
        interactive=interactive,
        usage="Usage: chattea server config get --section SECTION --key KEY [-i|-I]",
    )
    try:
        click.echo(get_gitea_config_value(values["section"], values["key"], config_path=config_path))
    except (KeyError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc


@config_group.command(name="set")
@click.option("--section", default=None, help="Gitea app.ini section, for example server.")
@click.option("--key", default=None, help="Gitea app.ini key, for example HTTP_PORT.")
@click.option("--value", default=None, help="Value to write into app.ini.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@add_interactive_option
def config_set(section: str | None, key: str | None, value: str | None, config_path: Path | None, interactive: bool | None) -> None:
    """Write one value into the managed Gitea app.ini."""
    provided_section = section if interactive is True else section or "server"
    values = resolve_command_inputs(
        schema=CONFIG_SET_SCHEMA,
        provided={"section": provided_section, "key": key, "value": value},
        interactive=interactive,
        usage="Usage: chattea server config set --section SECTION --key KEY --value VALUE [-i|-I]",
    )
    try:
        path = set_gitea_config_value(values["section"], values["key"], values["value"], config_path=config_path)
    except OSError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"updated: {path}")


@server_group.command(name="install")
@click.option("--version", default=None, help="ChatArch Gitea version, for example 1.0.0. Defaults to latest.")
@click.option("--prefix", type=click.Path(file_okay=False, path_type=Path), default=None, help="Install prefix. Defaults to CHATTEA_HOME.")
@click.option("--arch", default=None, help="Asset architecture override, for example amd64 or arm64.")
@click.option("--database-backend", type=click.Choice(server_ops.SUPPORTED_DATABASE_BACKENDS), default=None, help="Also prepare database backend infra. Defaults to sqlite3.")
@click.option("--mysql-instance", default=DEFAULT_MYSQL_INSTANCE, show_default=True, help="ChatData MySQL instance name when --database-backend mysql.")
@click.option("--mysql-version", default=DEFAULT_MYSQL_VERSION, show_default=True, help="ChatData MySQL runtime version.")
@click.option("--mysql-home", type=click.Path(file_okay=False, path_type=Path), default=None, help="ChatData home override. Defaults to CHATDATA_HOME.")
@click.option("--mysql-database", default=DEFAULT_MYSQL_DATABASE, show_default=True, help="MySQL database name to create for Gitea.")
@click.option("--mysql-user", default="root", show_default=True, help="MySQL user for later Gitea app.ini generation.")
@click.option("--mysql-password-env", default=None, help="Environment variable containing the MySQL password. Empty by default for local ChatData MySQL.")
@click.option("--mysql-port", default=DEFAULT_MYSQL_PORT, show_default=True, type=int, help="ChatData MySQL port for a new instance.")
@click.option("--mysql-bind-address", default=DEFAULT_MYSQL_BIND_ADDRESS, show_default=True, help="ChatData MySQL bind address for a new instance.")
@click.option("--install-mysql/--no-install-mysql", default=True, show_default=True, help="Install/reuse ChatData MySQL runtime when selecting mysql.")
@click.option("--mysql-service/--no-mysql-service", "install_mysql_service", default=True, show_default=True, help="Install/enable ChatData MySQL user service when selecting mysql.")
@click.option("--start-mysql/--no-start-mysql", default=True, show_default=True, help="Start ChatData MySQL after install.")
@click.option("--force", is_flag=True, help="Overwrite an existing binary.")
@add_interactive_option
def install(
    version: str | None,
    prefix: Path | None,
    arch: str | None,
    database_backend: str | None,
    mysql_instance: str,
    mysql_version: str,
    mysql_home: Path | None,
    mysql_database: str,
    mysql_user: str,
    mysql_password_env: str | None,
    mysql_port: int,
    mysql_bind_address: str,
    install_mysql: bool,
    install_mysql_service: bool,
    start_mysql: bool,
    force: bool,
    interactive: bool | None,
) -> None:
    """Download Gitea and optionally prepare database backend infra."""
    provided = {
        "version": version if interactive is True else version or "latest",
        "database_backend": database_backend if interactive is True else database_backend or DEFAULT_DATABASE_BACKEND,
    }
    values = resolve_command_inputs(
        schema=INSTALL_SCHEMA,
        provided=provided,
        interactive=interactive,
        usage="Usage: chattea server install [--version VERSION] [--database-backend sqlite3|mysql] [-i|-I]",
    )
    binary = install_gitea(values.get("version") or "latest", prefix=prefix, arch=arch, force=force)
    click.echo(f"installed: {binary}")
    database = prepare_database_backend(
        backend=values["database_backend"],
        mysql_instance=mysql_instance,
        mysql_version=mysql_version,
        mysql_home=mysql_home,
        mysql_database=mysql_database,
        mysql_user=mysql_user,
        mysql_password=_password_from_env(mysql_password_env) or "",
        mysql_port=mysql_port,
        mysql_bind_address=mysql_bind_address,
        install_mysql=install_mysql,
        install_mysql_service=install_mysql_service,
        start_mysql=start_mysql,
    )
    click.echo(f"database_backend: {database['backend']}")
    if database["mysql"]:
        layout = database["mysql"]["layout"]
        click.echo(f"mysql_socket: {layout['socket']}")


@server_group.command(name="init")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--base-url", default=None, help="Gitea public website/API base URL. Defaults to CHATTEA_BASE_URL.")
@click.option("--listen-addr", default=None, help="Gitea listen IP/host written to app.ini. Defaults to 127.0.0.1.")
@click.option("--http-port", default=None, type=int, help="Gitea listen port written to app.ini. Defaults to 3000.")
@click.option("--database-backend", type=click.Choice(server_ops.SUPPORTED_DATABASE_BACKENDS), default=None, help="Gitea database backend. Defaults to sqlite3.")
@click.option("--mysql-instance", default=DEFAULT_MYSQL_INSTANCE, show_default=True, help="ChatData MySQL instance name when --database-backend mysql.")
@click.option("--mysql-version", default=DEFAULT_MYSQL_VERSION, show_default=True, help="ChatData MySQL runtime version.")
@click.option("--mysql-home", type=click.Path(file_okay=False, path_type=Path), default=None, help="ChatData home override. Defaults to CHATDATA_HOME.")
@click.option("--mysql-database", default=DEFAULT_MYSQL_DATABASE, show_default=True, help="MySQL database name for Gitea.")
@click.option("--mysql-user", default="root", show_default=True, help="MySQL user written to app.ini.")
@click.option("--mysql-password-env", default=None, help="Environment variable containing the MySQL password. Empty by default for local ChatData MySQL.")
@click.option("--mysql-port", default=DEFAULT_MYSQL_PORT, show_default=True, type=int, help="ChatData MySQL port for a new instance.")
@click.option("--mysql-bind-address", default=DEFAULT_MYSQL_BIND_ADDRESS, show_default=True, help="ChatData MySQL bind address for a new instance.")
@click.option("--install-mysql/--no-install-mysql", default=True, show_default=True, help="Install/reuse ChatData MySQL runtime when selecting mysql.")
@click.option("--mysql-service/--no-mysql-service", "install_mysql_service", default=True, show_default=True, help="Install/enable ChatData MySQL user service when selecting mysql.")
@click.option("--start-mysql/--no-start-mysql", default=True, show_default=True, help="Start ChatData MySQL before initializing Gitea.")
@click.option("--run-user", default=None)
@click.option("--force", is_flag=True)
@add_interactive_option
def init(
    work_path: Path | None,
    config_path: Path | None,
    binary: Path | None,
    base_url: str | None,
    listen_addr: str | None,
    http_port: int | None,
    database_backend: str | None,
    mysql_instance: str,
    mysql_version: str,
    mysql_home: Path | None,
    mysql_database: str,
    mysql_user: str,
    mysql_password_env: str | None,
    mysql_port: int,
    mysql_bind_address: str,
    install_mysql: bool,
    install_mysql_service: bool,
    start_mysql: bool,
    run_user: str | None,
    force: bool,
    interactive: bool | None,
) -> None:
    """Create a minimal Gitea app.ini."""
    config = load_config()
    provided = {
        "base_url": base_url,
        "listen_addr": listen_addr,
        "http_port": http_port,
        "database_backend": database_backend,
    }
    if interactive is not True:
        provided = {
            "base_url": base_url or config.url,
            "listen_addr": listen_addr or DEFAULT_LISTEN_ADDR,
            "http_port": http_port or DEFAULT_HTTP_PORT,
            "database_backend": database_backend or DEFAULT_DATABASE_BACKEND,
        }
    values = resolve_command_inputs(
        schema=INIT_SCHEMA,
        provided=provided,
        interactive=interactive,
        usage="Usage: chattea server init [--base-url URL] [--database-backend sqlite3|mysql] [-i|-I]",
    )
    database = prepare_database_backend(
        backend=values["database_backend"],
        mysql_instance=mysql_instance,
        mysql_version=mysql_version,
        mysql_home=mysql_home,
        mysql_database=mysql_database,
        mysql_user=mysql_user,
        mysql_password=_password_from_env(mysql_password_env) or "",
        mysql_port=mysql_port,
        mysql_bind_address=mysql_bind_address,
        install_mysql=install_mysql,
        install_mysql_service=install_mysql_service,
        start_mysql=start_mysql,
    )
    resolved_config = init_gitea_server(
        work_path=work_path,
        binary=binary,
        config_path=config_path,
        base_url=values["base_url"],
        listen_addr=values["listen_addr"],
        http_port=values["http_port"],
        run_user=run_user,
        **database["gitea"],
        force=force,
    )
    click.echo(f"config: {resolved_config}")
    click.echo(f"database_backend: {database['backend']}")
    if database["mysql"]:
        layout = database["mysql"]["layout"]
        click.echo(f"mysql_socket: {layout['socket']}")


@server_group.command(name="bootstrap")
@click.option("--version", default="latest", show_default=True, help="ChatArch Gitea version. Defaults to latest.")
@click.option("--prefix", type=click.Path(file_okay=False, path_type=Path), default=None, help="Install prefix. Defaults to CHATTEA_HOME.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Existing Gitea binary path. Skips install when provided.")
@click.option("--base-url", default=None, help="Gitea public website/API base URL. Defaults to CHATTEA_BASE_URL.")
@click.option("--listen-addr", default=None, help="Gitea listen IP/host written to app.ini. Defaults to 127.0.0.1.")
@click.option("--http-port", default=None, type=int, help="Gitea listen port written to app.ini. Defaults to 3000.")
@click.option("--database-backend", type=click.Choice(server_ops.SUPPORTED_DATABASE_BACKENDS), default=None, help="Gitea database backend. Defaults to sqlite3.")
@click.option("--mysql-instance", default=DEFAULT_MYSQL_INSTANCE, show_default=True, help="ChatData MySQL instance name when --database-backend mysql.")
@click.option("--mysql-version", default=DEFAULT_MYSQL_VERSION, show_default=True, help="ChatData MySQL runtime version.")
@click.option("--mysql-home", type=click.Path(file_okay=False, path_type=Path), default=None, help="ChatData home override. Defaults to CHATDATA_HOME.")
@click.option("--mysql-database", default=DEFAULT_MYSQL_DATABASE, show_default=True, help="MySQL database name for Gitea.")
@click.option("--mysql-user", default="root", show_default=True, help="MySQL user written to app.ini.")
@click.option("--mysql-password-env", default=None, help="Environment variable containing the MySQL password. Empty by default for local ChatData MySQL.")
@click.option("--mysql-port", default=DEFAULT_MYSQL_PORT, show_default=True, type=int, help="ChatData MySQL port for a new instance.")
@click.option("--mysql-bind-address", default=DEFAULT_MYSQL_BIND_ADDRESS, show_default=True, help="ChatData MySQL bind address for a new instance.")
@click.option("--install-mysql/--no-install-mysql", default=True, show_default=True, help="Install/reuse ChatData MySQL runtime when selecting mysql.")
@click.option("--mysql-service/--no-mysql-service", "install_mysql_service", default=True, show_default=True, help="Install/enable ChatData MySQL user service when selecting mysql.")
@click.option("--start-mysql/--no-start-mysql", default=True, show_default=True, help="Start ChatData MySQL before initializing Gitea.")
@click.option("--admin-user", default=None, help="Initial admin username. Defaults to CHATTEA_BOOTSTRAP_ADMIN_USER.")
@click.option("--admin-email", default=None, help="Initial admin email. Defaults to CHATTEA_BOOTSTRAP_ADMIN_EMAIL.")
@click.option("--admin-password-env", default=None, help="Environment variable containing the initial admin password.")
@click.option("--token-name", default=None, help="Initial access token name. Defaults to CHATTEA_BOOTSTRAP_TOKEN_NAME or default.")
@click.option("--token-scopes", default=None, help="Initial access token scopes. Defaults to CHATTEA_BOOTSTRAP_TOKEN_SCOPES or all.")
@click.option("--force", is_flag=True, help="Overwrite app.ini and binary when applicable.")
@click.option("--start-service", is_flag=True, help="Start the user-level systemd service after bootstrap.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@add_interactive_option
def bootstrap(
    version: str | None,
    prefix: Path | None,
    work_path: Path | None,
    config_path: Path | None,
    binary: Path | None,
    base_url: str | None,
    listen_addr: str | None,
    http_port: int | None,
    database_backend: str | None,
    mysql_instance: str,
    mysql_version: str,
    mysql_home: Path | None,
    mysql_database: str,
    mysql_user: str,
    mysql_password_env: str | None,
    mysql_port: int,
    mysql_bind_address: str,
    install_mysql: bool,
    install_mysql_service: bool,
    start_mysql: bool,
    admin_user: str | None,
    admin_email: str | None,
    admin_password_env: str | None,
    token_name: str | None,
    token_scopes: str | None,
    force: bool,
    start_service: bool,
    json_output: bool,
    interactive: bool | None,
) -> None:
    """Bootstrap a local Gitea server, admin user, token, and ChatTea credentials."""
    config = load_config()
    password = _password_from_env(admin_password_env) or config.bootstrap_admin_password
    provided = {
        "base_url": base_url if interactive is True else base_url or config.url,
        "admin_user": admin_user if interactive is True else admin_user or config.bootstrap_admin_user,
        "admin_email": admin_email if interactive is True else admin_email or config.bootstrap_admin_email,
        "admin_password": password,
        "token_name": token_name if interactive is True else token_name or config.bootstrap_token_name,
        "token_scopes": token_scopes if interactive is True else token_scopes or config.bootstrap_token_scopes,
        "database_backend": database_backend if interactive is True else database_backend or DEFAULT_DATABASE_BACKEND,
    }
    values = resolve_command_inputs(
        schema=BOOTSTRAP_SCHEMA,
        provided=provided,
        interactive=interactive,
        usage="Usage: chattea server bootstrap [--base-url URL] [--admin-user USER] [--database-backend sqlite3|mysql] [-i|-I]",
    )
    result = bootstrap_gitea_server(
        base_url=values["base_url"],
        admin_user=values["admin_user"],
        admin_password=values["admin_password"],
        admin_email=values["admin_email"],
        token_name=values["token_name"],
        token_scopes=values["token_scopes"],
        version=version,
        prefix=prefix,
        work_path=work_path,
        config_path=config_path,
        binary=binary,
        listen_addr=listen_addr,
        http_port=http_port,
        database_backend=values["database_backend"],
        mysql_instance=mysql_instance,
        mysql_version=mysql_version,
        mysql_home=mysql_home,
        mysql_database=mysql_database,
        mysql_user=mysql_user,
        mysql_password=_password_from_env(mysql_password_env) or "",
        mysql_port=mysql_port,
        mysql_bind_address=mysql_bind_address,
        install_mysql=install_mysql,
        install_mysql_service=install_mysql_service,
        start_mysql=start_mysql,
        force=force,
        start_service=start_service,
    )
    if json_output:
        click.echo(json.dumps(result, indent=2, default=str))
        return
    click.echo(f"binary: {result['binary']}")
    click.echo(f"config: {result['config']}")
    click.echo(f"work_path: {result['work_path']}")
    click.echo(f"database_backend: {result['database_backend']}")
    if result.get("mysql"):
        layout = result["mysql"]["layout"]
        click.echo(f"mysql_socket: {layout['socket']}")
    click.echo(f"admin: {result['admin_user']}")
    click.echo(f"token: {result['token']}")
    if result.get("token_source"):
        click.echo(f"token_source: {result['token_source']}")
    credentials = result["credentials"]
    if isinstance(credentials, dict) and credentials.get("env_path"):
        click.echo(f"chatenv: {credentials['env_path']}")
    if result.get("service"):
        click.echo(f"service: {result['service']}")


@server_group.command(name="serve")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
def serve(binary: Path | None, config_path: Path | None, work_path: Path | None) -> None:
    """Run Gitea in the foreground."""
    serve_gitea(binary=binary, config_path=config_path, work_path=work_path)


@server_group.command(name="start")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_WORK_PATH.")
def start(binary: Path | None, config_path: Path | None, work_path: Path | None) -> None:
    """Install and start a user systemd service."""
    service_file = start_gitea_service(binary=binary, config_path=config_path, work_path=work_path)
    click.echo(f"started: {server_ops.DEFAULT_SERVICE_NAME}")
    click.echo(f"service: {service_file}")


@server_group.command(name="stop")
def stop() -> None:
    """Stop the user systemd service."""
    stop_gitea_service()
    click.echo(f"stopped: {server_ops.DEFAULT_SERVICE_NAME}")


@server_group.command(name="restart")
def restart() -> None:
    """Restart the user systemd service."""
    restart_gitea_service()
    click.echo(f"restarted: {server_ops.DEFAULT_SERVICE_NAME}")


@server_group.command(name="status")
def status() -> None:
    """Show the user systemd service status."""
    result = status_gitea_service()
    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.stderr:
        click.echo(result.stderr.rstrip(), err=True)
    raise SystemExit(result.returncode)


@server_group.command(name="logs")
@click.option("--follow", "follow", is_flag=True)
@click.option("--lines", default=100, show_default=True)
def logs(follow: bool, lines: int) -> None:
    """Show service logs."""
    result = logs_gitea_service(follow=follow, lines=lines)
    raise SystemExit(result.returncode)


@server_group.command(name="version")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_BINARY.")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_BASE_URL.")
@click.option("--json-output", is_flag=True)
def version(binary: Path | None, url: str | None, json_output: bool) -> None:
    """Show Gitea binary or server version."""
    payload = gitea_version(binary=binary, url=url)
    if payload is not None:
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))


@server_group.command(name="health")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_BASE_URL.")
@click.option("--json-output", is_flag=True)
def health(url: str | None, json_output: bool) -> None:
    """Check whether the Gitea API is reachable."""
    try:
        result = check_gitea_health(url=url)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2) if json_output else f"ok: {result['url']} ({result['version']})")

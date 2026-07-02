from __future__ import annotations

import json
from pathlib import Path

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs

from chattea import server as server_ops
from chattea.api import GiteaAPIError, GiteaClient
from chattea.config import DEFAULT_BASE_URL, DEFAULT_HTTP_PORT, DEFAULT_LISTEN_ADDR, load_config


INSTALL_SCHEMA = CommandSchema(
    name="server install",
    fields=(CommandField("version", prompt="Gitea version", required=True),),
)

INIT_SCHEMA = CommandSchema(
    name="server init",
    fields=(
        CommandField("base_url", prompt="Gitea base URL", required=True, default=DEFAULT_BASE_URL, prompt_if_missing=True),
        CommandField("listen_addr", prompt="Gitea listen address", required=True, default=DEFAULT_LISTEN_ADDR, prompt_if_missing=True),
        CommandField("http_port", prompt="Gitea HTTP port", kind="int", required=True, default=DEFAULT_HTTP_PORT, prompt_if_missing=True),
    ),
)


def _required_path(value: Path | None, name: str) -> Path:
    if value is None:
        raise click.ClickException(f"Missing resolved path for {name}.")
    return value


def install_gitea(version: str, prefix: Path | None = None, arch: str | None = None, force: bool = False) -> Path:
    """Download or reuse the managed Gitea binary."""
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
    force: bool = False,
) -> Path:
    """Create or reuse the managed Gitea app.ini."""
    config = load_config()
    return server_ops.init_instance(
        work_path=work_path or _required_path(config.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
        binary=binary or _required_path(config.gitea_binary, "CHATTEA_GITEA_BINARY"),
        config_path=config_path or _required_path(config.gitea_config, "CHATTEA_GITEA_CONFIG"),
        base_url=base_url or config.url,
        listen_addr=listen_addr or config.gitea_listen_addr,
        http_port=http_port or config.gitea_http_port,
        run_user=run_user,
        force=force,
    )


def serve_gitea(binary: Path | None = None, config_path: Path | None = None, work_path: Path | None = None):
    """Run the managed Gitea instance in the foreground."""
    resolved = load_config()
    return server_ops.run_gitea(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_GITEA_BINARY"),
        ["web"],
        config=config_path or _required_path(resolved.gitea_config, "CHATTEA_GITEA_CONFIG"),
        work_path=work_path or _required_path(resolved.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
    )


def start_gitea_service(binary: Path | None = None, config_path: Path | None = None, work_path: Path | None = None) -> Path:
    """Install and start the managed user-level systemd service."""
    resolved = load_config()
    service_file = server_ops.write_user_service(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_GITEA_BINARY"),
        config_path or _required_path(resolved.gitea_config, "CHATTEA_GITEA_CONFIG"),
        work_path or _required_path(resolved.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
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
        server_ops.run_gitea(_required_path(config.gitea_binary, "CHATTEA_GITEA_BINARY"), ["--version"])
        return None


def check_gitea_health(url: str | None = None) -> dict:
    """Check whether the configured Gitea API endpoint is reachable."""
    config = load_config()
    target_url = (url or config.url).rstrip("/")
    payload = GiteaClient(url=target_url).version()
    return {"ok": True, "url": target_url, "version": payload.get("version")}


@click.group(name="server")
def server_group() -> None:
    """Install and manage a local Gitea server."""


@server_group.command(name="install")
@click.option("--version", default=None, help="Gitea version, for example 1.26.4.")
@click.option("--prefix", type=click.Path(file_okay=False, path_type=Path), default=None, help="Install prefix. Defaults to CHATTEA_HOME.")
@click.option("--arch", default=None, help="Asset architecture override, for example amd64 or arm64.")
@click.option("--force", is_flag=True, help="Overwrite an existing binary.")
@add_interactive_option
def install(version: str | None, prefix: Path | None, arch: str | None, force: bool, interactive: bool | None) -> None:
    """Download the Gitea binary."""
    values = resolve_command_inputs(
        schema=INSTALL_SCHEMA,
        provided={"version": version},
        interactive=interactive,
        usage="Usage: chattea server install --version VERSION [-i|-I]",
    )
    binary = install_gitea(values["version"], prefix=prefix, arch=arch, force=force)
    click.echo(f"installed: {binary}")


@server_group.command(name="init")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--base-url", default=None, help="Gitea public website/API base URL. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--listen-addr", default=None, help="Gitea listen IP/host. Defaults to CHATTEA_GITEA_LISTEN_ADDR.")
@click.option("--http-port", default=None, type=int, help="Gitea listen port. Defaults to CHATTEA_GITEA_HTTP_PORT.")
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
    }
    if interactive is not True:
        provided = {
            "base_url": base_url or config.url,
            "listen_addr": listen_addr or config.gitea_listen_addr,
            "http_port": http_port or config.gitea_http_port,
        }
    values = resolve_command_inputs(
        schema=INIT_SCHEMA,
        provided=provided,
        interactive=interactive,
        usage="Usage: chattea server init [--base-url URL] [--listen-addr IP] [--http-port PORT] [-i|-I]",
    )
    resolved_config = init_gitea_server(
        work_path=work_path,
        binary=binary,
        config_path=config_path,
        base_url=values["base_url"],
        listen_addr=values["listen_addr"],
        http_port=values["http_port"],
        run_user=run_user,
        force=force,
    )
    click.echo(f"config: {resolved_config}")


@server_group.command(name="serve")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
def serve(binary: Path | None, config_path: Path | None, work_path: Path | None) -> None:
    """Run Gitea in the foreground."""
    serve_gitea(binary=binary, config_path=config_path, work_path=work_path)


@server_group.command(name="start")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
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
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--json-output", is_flag=True)
def version(binary: Path | None, url: str | None, json_output: bool) -> None:
    """Show Gitea binary or server version."""
    payload = gitea_version(binary=binary, url=url)
    if payload is not None:
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))


@server_group.command(name="health")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--json-output", is_flag=True)
def health(url: str | None, json_output: bool) -> None:
    """Check whether the Gitea API is reachable."""
    try:
        result = check_gitea_health(url=url)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2) if json_output else f"ok: {result['url']} ({result['version']})")

from __future__ import annotations

import json
from pathlib import Path

import click

from chattea import server as server_ops
from chattea.api import GiteaAPIError, GiteaClient
from chattea.config import load_config


def _required_path(value: Path | None, name: str) -> Path:
    if value is None:
        raise click.ClickException(f"Missing resolved path for {name}.")
    return value


@click.group(name="server")
def server_group() -> None:
    """Install and manage a local Gitea server."""


@server_group.command(name="install")
@click.option("--version", required=True, help="Gitea version, for example 1.26.4.")
@click.option("--prefix", type=click.Path(file_okay=False, path_type=Path), default=None, help="Install prefix. Defaults to CHATTEA_HOME.")
@click.option("--arch", default=None, help="Asset architecture override, for example amd64 or arm64.")
@click.option("--force", is_flag=True, help="Overwrite an existing binary.")
def install(version: str, prefix: Path | None, arch: str | None, force: bool) -> None:
    """Download the Gitea binary."""
    config = load_config()
    resolved_prefix = prefix or config.home or server_ops.DEFAULT_PREFIX
    binary = server_ops.install_binary(version, prefix=resolved_prefix, arch=arch, force=force)
    click.echo(f"installed: {binary}")


@server_group.command(name="init")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
@click.option("--config", "config_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--http-port", default=None, type=int, help="Gitea HTTP port. Defaults to CHATTEA_GITEA_HTTP_PORT.")
@click.option("--domain", default=None, help="Gitea domain. Defaults to CHATTEA_GITEA_DOMAIN.")
@click.option("--run-user", default=None)
@click.option("--force", is_flag=True)
def init(
    work_path: Path | None,
    config_path: Path | None,
    binary: Path | None,
    http_port: int | None,
    domain: str | None,
    run_user: str | None,
    force: bool,
) -> None:
    """Create a minimal Gitea app.ini."""
    config = load_config()
    resolved_config = server_ops.init_instance(
        work_path=work_path or _required_path(config.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
        binary=binary or _required_path(config.gitea_binary, "CHATTEA_GITEA_BINARY"),
        config_path=config_path or _required_path(config.gitea_config, "CHATTEA_GITEA_CONFIG"),
        http_port=http_port or config.gitea_http_port,
        domain=domain or config.gitea_domain,
        run_user=run_user,
        force=force,
    )
    click.echo(f"config: {resolved_config}")


@server_group.command(name="serve")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--config", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
def serve(binary: Path | None, config: Path | None, work_path: Path | None) -> None:
    """Run Gitea in the foreground."""
    resolved = load_config()
    server_ops.run_gitea(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_GITEA_BINARY"),
        ["web"],
        config=config or _required_path(resolved.gitea_config, "CHATTEA_GITEA_CONFIG"),
        work_path=work_path or _required_path(resolved.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
    )


@server_group.command(name="start")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--config", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea app.ini path. Defaults to CHATTEA_GITEA_CONFIG.")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=None, help="Gitea work path. Defaults to CHATTEA_GITEA_WORK_PATH.")
@click.option("--service-name", default=None, help="User systemd service name. Defaults to CHATTEA_GITEA_SERVICE_NAME.")
def start(binary: Path | None, config: Path | None, work_path: Path | None, service_name: str | None) -> None:
    """Install and start a user systemd service."""
    resolved = load_config()
    resolved_service = service_name or resolved.gitea_service_name
    service_file = server_ops.write_user_service(
        binary or _required_path(resolved.gitea_binary, "CHATTEA_GITEA_BINARY"),
        config or _required_path(resolved.gitea_config, "CHATTEA_GITEA_CONFIG"),
        work_path or _required_path(resolved.gitea_work_path, "CHATTEA_GITEA_WORK_PATH"),
        resolved_service,
    )
    server_ops.systemctl_user(["daemon-reload"])
    server_ops.systemctl_user(["enable", "--now", resolved_service])
    click.echo(f"started: {resolved_service}")
    click.echo(f"service: {service_file}")


@server_group.command(name="stop")
@click.option("--service-name", default=None, help="User systemd service name. Defaults to CHATTEA_GITEA_SERVICE_NAME.")
def stop(service_name: str | None) -> None:
    """Stop the user systemd service."""
    resolved_service = service_name or load_config().gitea_service_name
    server_ops.systemctl_user(["stop", resolved_service])
    click.echo(f"stopped: {resolved_service}")


@server_group.command(name="restart")
@click.option("--service-name", default=None, help="User systemd service name. Defaults to CHATTEA_GITEA_SERVICE_NAME.")
def restart(service_name: str | None) -> None:
    """Restart the user systemd service."""
    resolved_service = service_name or load_config().gitea_service_name
    server_ops.systemctl_user(["restart", resolved_service])
    click.echo(f"restarted: {resolved_service}")


@server_group.command(name="status")
@click.option("--service-name", default=None, help="User systemd service name. Defaults to CHATTEA_GITEA_SERVICE_NAME.")
def status(service_name: str | None) -> None:
    """Show the user systemd service status."""
    resolved_service = service_name or load_config().gitea_service_name
    result = server_ops.systemctl_user(["--no-pager", "--full", "status", resolved_service], check=False)
    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.stderr:
        click.echo(result.stderr.rstrip(), err=True)
    raise SystemExit(result.returncode)


@server_group.command(name="logs")
@click.option("--service-name", default=None, help="User systemd service name. Defaults to CHATTEA_GITEA_SERVICE_NAME.")
@click.option("--follow", "follow", is_flag=True)
@click.option("--lines", default=100, show_default=True)
def logs(service_name: str | None, follow: bool, lines: int) -> None:
    """Show service logs."""
    resolved_service = service_name or load_config().gitea_service_name
    result = server_ops.journalctl_user(resolved_service, follow=follow, lines=lines)
    raise SystemExit(result.returncode)


@server_group.command(name="version")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Gitea binary path. Defaults to CHATTEA_GITEA_BINARY.")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_URL.")
@click.option("--json-output", is_flag=True)
def version(binary: Path | None, url: str | None, json_output: bool) -> None:
    """Show Gitea binary or server version."""
    config = load_config()
    if url:
        payload = GiteaClient(url=url).version()
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))
        return
    if binary:
        server_ops.run_gitea(binary, ["--version"])
        return
    try:
        payload = GiteaClient(url=config.url, token=config.token).version()
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))
    except GiteaAPIError:
        server_ops.run_gitea(_required_path(config.gitea_binary, "CHATTEA_GITEA_BINARY"), ["--version"])


@server_group.command(name="health")
@click.option("--url", default=None, help="Gitea base URL. Defaults to CHATTEA_URL.")
@click.option("--json-output", is_flag=True)
def health(url: str | None, json_output: bool) -> None:
    """Check whether the Gitea API is reachable."""
    config = load_config()
    target_url = (url or config.url).rstrip("/")
    try:
        payload = GiteaClient(url=target_url).version()
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    result = {"ok": True, "url": target_url, "version": payload.get("version")}
    click.echo(json.dumps(result, indent=2) if json_output else f"ok: {result['url']} ({result['version']})")

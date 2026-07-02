from __future__ import annotations

import json
from pathlib import Path

import click

from chattea import server as server_ops
from chattea.api import GiteaAPIError, GiteaClient
from chattea.config import load_config


@click.group(name="server")
def server_group() -> None:
    """Install and manage a local Gitea server."""


@server_group.command(name="install")
@click.option("--version", required=True, help="Gitea version, for example 1.26.4.")
@click.option("--prefix", type=click.Path(file_okay=False, path_type=Path), default=server_ops.DEFAULT_PREFIX, show_default=True)
@click.option("--arch", default=None, help="Asset architecture override, for example amd64 or arm64.")
@click.option("--force", is_flag=True, help="Overwrite an existing binary.")
def install(version: str, prefix: Path, arch: str | None, force: bool) -> None:
    """Download the Gitea binary."""
    binary = server_ops.install_binary(version, prefix=prefix, arch=arch, force=force)
    click.echo(f"installed: {binary}")


@server_group.command(name="init")
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=server_ops.DEFAULT_WORK_PATH, show_default=True)
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--http-port", default=3000, show_default=True)
@click.option("--domain", default="127.0.0.1", show_default=True)
@click.option("--run-user", default=None)
@click.option("--force", is_flag=True)
def init(work_path: Path, binary: Path | None, http_port: int, domain: str, run_user: str | None, force: bool) -> None:
    """Create a minimal Gitea app.ini."""
    config = server_ops.init_instance(work_path=work_path, binary=binary, http_port=http_port, domain=domain, run_user=run_user, force=force)
    click.echo(f"config: {config}")


@server_group.command(name="serve")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--config", type=click.Path(dir_okay=False, path_type=Path), default=server_ops.DEFAULT_WORK_PATH / "custom" / "conf" / "app.ini", show_default=True)
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=server_ops.DEFAULT_WORK_PATH, show_default=True)
def serve(binary: Path | None, config: Path, work_path: Path) -> None:
    """Run Gitea in the foreground."""
    resolved_binary = binary or server_ops.find_binary()
    server_ops.run_gitea(resolved_binary, ["web"], config=config, work_path=work_path)


@server_group.command(name="start")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--config", type=click.Path(dir_okay=False, path_type=Path), default=server_ops.DEFAULT_WORK_PATH / "custom" / "conf" / "app.ini", show_default=True)
@click.option("--work-path", type=click.Path(file_okay=False, path_type=Path), default=server_ops.DEFAULT_WORK_PATH, show_default=True)
@click.option("--service-name", default=server_ops.DEFAULT_SERVICE_NAME, show_default=True)
def start(binary: Path | None, config: Path, work_path: Path, service_name: str) -> None:
    """Install and start a user systemd service."""
    resolved_binary = binary or server_ops.find_binary()
    service_file = server_ops.write_user_service(resolved_binary, config, work_path, service_name)
    server_ops.systemctl_user(["daemon-reload"])
    server_ops.systemctl_user(["enable", "--now", service_name])
    click.echo(f"started: {service_name}")
    click.echo(f"service: {service_file}")


@server_group.command(name="stop")
@click.option("--service-name", default=server_ops.DEFAULT_SERVICE_NAME, show_default=True)
def stop(service_name: str) -> None:
    """Stop the user systemd service."""
    server_ops.systemctl_user(["stop", service_name])
    click.echo(f"stopped: {service_name}")


@server_group.command(name="restart")
@click.option("--service-name", default=server_ops.DEFAULT_SERVICE_NAME, show_default=True)
def restart(service_name: str) -> None:
    """Restart the user systemd service."""
    server_ops.systemctl_user(["restart", service_name])
    click.echo(f"restarted: {service_name}")


@server_group.command(name="status")
@click.option("--service-name", default=server_ops.DEFAULT_SERVICE_NAME, show_default=True)
def status(service_name: str) -> None:
    """Show the user systemd service status."""
    result = server_ops.systemctl_user(["--no-pager", "--full", "status", service_name], check=False)
    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.stderr:
        click.echo(result.stderr.rstrip(), err=True)
    raise SystemExit(result.returncode)


@server_group.command(name="logs")
@click.option("--service-name", default=server_ops.DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--follow", "follow", is_flag=True)
@click.option("--lines", default=100, show_default=True)
def logs(service_name: str, follow: bool, lines: int) -> None:
    """Show service logs."""
    result = server_ops.journalctl_user(service_name, follow=follow, lines=lines)
    raise SystemExit(result.returncode)


@server_group.command(name="version")
@click.option("--binary", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--url", default=None, help="Gitea base URL. Defaults to saved config.")
@click.option("--json-output", is_flag=True)
def version(binary: Path | None, url: str | None, json_output: bool) -> None:
    """Show Gitea binary or server version."""
    if url:
        payload = GiteaClient(url=url).version()
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))
        return
    if binary:
        server_ops.run_gitea(binary, ["--version"])
        return
    config = load_config()
    try:
        payload = GiteaClient(url=config.url, token=config.token).version()
        click.echo(json.dumps(payload, indent=2) if json_output else payload.get("version", payload))
    except GiteaAPIError:
        server_ops.run_gitea(server_ops.find_binary(), ["--version"])


@server_group.command(name="health")
@click.option("--url", default=None, help="Gitea base URL. Defaults to saved config.")
@click.option("--json-output", is_flag=True)
def health(url: str | None, json_output: bool) -> None:
    """Check whether the Gitea API is reachable."""
    try:
        payload = GiteaClient(url=url).version()
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    result = {"ok": True, "url": (url or load_config().url).rstrip("/"), "version": payload.get("version")}
    click.echo(json.dumps(result, indent=2) if json_output else f"ok: {result['url']} ({result['version']})")

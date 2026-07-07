from __future__ import annotations

import hashlib
import json
import lzma
import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts
from chattea.commands.actions_shared import list_payload_items
from chattea.config import load_config

RUNNER_RELEASE_API = "https://gitea.com/api/v1/repos/gitea/act_runner/releases/latest"
RUNNER_SERVICE = "chattea-runner.service"


def runner_root(root: Path | None = None) -> Path:
    config = load_config()
    return (root or (config.home or Path.home() / ".chatarch" / "chattea") / "runner").expanduser()


def runner_binary(root: Path | None = None) -> Path:
    return runner_root(root) / "bin" / "gitea-runner"


def runner_config(root: Path | None = None) -> Path:
    return runner_root(root) / "config" / "config.yaml"


def detect_runner_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise click.ClickException(f"Unsupported runner architecture: {platform.machine()}")


def _latest_runner_release() -> tuple[str, dict[str, str]]:
    with urllib.request.urlopen(RUNNER_RELEASE_API, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = str(payload.get("tag_name") or "").lstrip("v")
    if not tag:
        raise click.ClickException("Could not resolve latest Gitea runner release")
    assets = {asset["name"]: asset["browser_download_url"] for asset in payload.get("assets", []) if asset.get("name") and asset.get("browser_download_url")}
    return tag, assets


def install_runner(root: Path | None = None, *, version: str = "latest", force: bool = False, arch: str | None = None, binary_path: Path | None = None) -> Path:
    target = runner_binary(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if binary_path:
        shutil.copy2(binary_path.expanduser(), target)
        target.chmod(0o755)
        return target
    if target.exists() and not force:
        return target
    resolved_arch = arch or detect_runner_arch()
    tag, assets = _latest_runner_release() if version in {"", "latest"} else (version.lstrip("v"), {})
    if not assets:
        release_url = f"https://gitea.com/api/v1/repos/gitea/act_runner/releases/tags/v{tag}"
        with urllib.request.urlopen(release_url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assets = {asset["name"]: asset["browser_download_url"] for asset in payload.get("assets", []) if asset.get("name") and asset.get("browser_download_url")}
    asset = f"gitea-runner-{tag}-linux-{resolved_arch}.xz"
    checksum_asset = f"{asset}.sha256"
    if asset not in assets or checksum_asset not in assets:
        raise click.ClickException(f"Runner release v{tag} does not contain {asset} and checksum")
    temp_xz = target.with_suffix(".download.xz")
    urllib.request.urlretrieve(assets[asset], temp_xz)
    expected = urllib.request.urlopen(assets[checksum_asset], timeout=30).read().decode("utf-8").split()[0]
    actual = hashlib.sha256(temp_xz.read_bytes()).hexdigest()
    if expected != actual:
        temp_xz.unlink(missing_ok=True)
        raise click.ClickException(f"Checksum mismatch for {asset}")
    target.write_bytes(lzma.decompress(temp_xz.read_bytes()))
    temp_xz.unlink(missing_ok=True)
    target.chmod(0o755)
    return target


def ensure_runner_config(root: Path | None = None, *, force: bool = False, labels: str = "ubuntu-latest:host") -> Path:
    config_path = runner_config(root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not force:
        return config_path
    label_lines = "\n".join(f"    - {json.dumps(label.strip())}" for label in labels.split(",") if label.strip())
    config_path.write_text(
        f"""log:
  level: info

runner:
  file: .runner
  capacity: 1
  timeout: 3h
  insecure: false
  fetch_timeout: 5s
  fetch_interval: 2s
  labels:
{label_lines or '    - "ubuntu-latest:host"'}

cache:
  enabled: false

host:
  workdir_parent: {runner_root(root) / 'work'}
""",
        encoding="utf-8",
    )
    return config_path


def create_runner_token(scope: str, repo: str | None = None, org: str | None = None) -> dict[str, Any]:
    owner = name = None
    if repo:
        owner, name = repo_parts(repo)
    return client().create_runner_registration_token(scope, owner=owner, repo=name, org=org)


def list_registered_runners(scope: str, repo: str | None = None, org: str | None = None):
    owner = name = None
    if repo:
        owner, name = repo_parts(repo)
    return client().list_runners(scope, owner=owner, repo=name, org=org)


def view_registered_runner(runner_id: int, scope: str, repo: str | None = None, org: str | None = None):
    owner = name = None
    if repo:
        owner, name = repo_parts(repo)
    return client().get_runner(runner_id, scope, owner=owner, repo=name, org=org)


def edit_registered_runner(runner_id: int, scope: str, repo: str | None = None, org: str | None = None, disabled: bool | None = None):
    owner = name = None
    if repo:
        owner, name = repo_parts(repo)
    return client().edit_runner(runner_id, scope, owner=owner, repo=name, org=org, disabled=disabled)


def delete_registered_runner(runner_id: int, scope: str, repo: str | None = None, org: str | None = None):
    owner = name = None
    if repo:
        owner, name = repo_parts(repo)
    return client().delete_runner(runner_id, scope, owner=owner, repo=name, org=org)


def _token_value(payload: dict[str, Any]) -> str:
    for key in ("token", "registration_token"):
        value = payload.get(key)
        if value:
            return str(value)
    raise click.ClickException("Runner registration token response did not include a token")


def register_runner(root: Path | None = None, *, scope: str = "repo", repo: str | None = None, org: str | None = None, name: str = "chattea-runner", labels: str = "ubuntu-latest:host") -> Path:
    root_path = runner_root(root)
    root_path.mkdir(parents=True, exist_ok=True)
    binary = install_runner(root_path)
    config_path = ensure_runner_config(root_path, force=True, labels=labels)
    token = _token_value(create_runner_token(scope, repo=repo, org=org))
    base_url = load_config().url
    subprocess.run(
        [str(binary), "register", "--no-interactive", "--instance", base_url, "--token", token, "--name", name, "--labels", labels, "-c", str(config_path)],
        cwd=root_path,
        check=True,
    )
    return root_path / ".runner"


def runner_service_path() -> Path:
    return Path("~/.config/systemd/user").expanduser() / RUNNER_SERVICE


def write_runner_service(root: Path | None = None) -> Path:
    root_path = runner_root(root)
    path = runner_service_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""[Unit]
Description=ChatTea managed Gitea Actions runner
After=network.target chattea-gitea.service

[Service]
Type=simple
WorkingDirectory={root_path}
ExecStart={runner_binary(root_path)} daemon -c {runner_config(root_path)}
Restart=always
RestartSec=5s
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""
    path.write_text(content, encoding="utf-8")
    return path


def start_runner_service(root: Path | None = None) -> Path:
    service = write_runner_service(root)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", RUNNER_SERVICE], check=True)
    return service


def stop_runner_service() -> None:
    subprocess.run(["systemctl", "--user", "stop", RUNNER_SERVICE], check=False)


def runner_service_status() -> subprocess.CompletedProcess[str]:
    return subprocess.run(["systemctl", "--user", "--no-pager", "--full", "status", RUNNER_SERVICE], capture_output=True, text=True, check=False)


def runner_service_logs(lines: int = 100) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["journalctl", "--user", "-u", RUNNER_SERVICE, "-n", str(lines), "--no-pager"], capture_output=True, text=True, check=False)


@click.group(name="runner")
def runner_group() -> None:
    """Manage Gitea Actions runners."""


def _scope_options(fn):
    fn = click.option("--org", default=None, help="Organization for org scope.")(fn)
    fn = click.option("--repo", default=None, help="Repository in OWNER/NAME format for repo scope.")(fn)
    fn = click.option("--scope", type=click.Choice(["repo", "org", "user", "admin"]), default="repo", show_default=True)(fn)
    return fn


@runner_group.command(name="token")
@_scope_options
def token_command(scope: str, repo: str | None, org: str | None) -> None:
    render_json(create_runner_token(scope, repo=repo, org=org))


@runner_group.command(name="list")
@_scope_options
@click.option("--json-output", is_flag=True)
def list_command(scope: str, repo: str | None, org: str | None, json_output: bool) -> None:
    payload = list_registered_runners(scope, repo=repo, org=org)
    if json_output:
        render_json(payload)
        return
    render_items(list_payload_items(payload), "id", "name", "status", "active")


@runner_group.command(name="view")
@_scope_options
@click.argument("runner_id", type=int)
def view_command(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    render_json(view_registered_runner(runner_id, scope, repo=repo, org=org))


@runner_group.command(name="edit")
@_scope_options
@click.argument("runner_id", type=int)
@click.option("--disabled/--enabled", default=None, help="Set runner disabled flag.")
def edit_command(scope: str, repo: str | None, org: str | None, runner_id: int, disabled: bool | None) -> None:
    render_json(edit_registered_runner(runner_id, scope, repo=repo, org=org, disabled=disabled))


@runner_group.command(name="delete")
@_scope_options
@click.argument("runner_id", type=int)
def delete_command(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    delete_registered_runner(runner_id, scope, repo=repo, org=org)
    click.echo(f"deleted: {runner_id}")


@runner_group.group(name="setup")
def setup_group() -> None:
    """Install, register, and manage a local runner process."""


@setup_group.command(name="install")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--version", default="latest", show_default=True)
@click.option("--force", is_flag=True)
@click.option("--binary", "binary_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Copy an existing runner binary.")
def setup_install(root: Path | None, version: str, force: bool, binary_path: Path | None) -> None:
    path = install_runner(root, version=version, force=force, binary_path=binary_path)
    ensure_runner_config(root, force=force)
    click.echo(f"installed: {path}")


@setup_group.command(name="register")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None)
@_scope_options
@click.option("--name", default="chattea-runner", show_default=True)
@click.option("--labels", default="ubuntu-latest:host", show_default=True)
def setup_register(root: Path | None, scope: str, repo: str | None, org: str | None, name: str, labels: str) -> None:
    path = register_runner(root, scope=scope, repo=repo, org=org, name=name, labels=labels)
    click.echo(f"registered: {path}")


@setup_group.command(name="start")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None)
def setup_start(root: Path | None) -> None:
    path = start_runner_service(root)
    click.echo(f"started: {RUNNER_SERVICE}")
    click.echo(f"service: {path}")


@setup_group.command(name="stop")
def setup_stop() -> None:
    stop_runner_service()
    click.echo(f"stopped: {RUNNER_SERVICE}")


@setup_group.command(name="status")
def setup_status() -> None:
    result = runner_service_status()
    click.echo((result.stdout or result.stderr).rstrip())
    raise SystemExit(result.returncode)


@setup_group.command(name="logs")
@click.option("--lines", default=100, show_default=True)
def setup_logs(lines: int) -> None:
    result = runner_service_logs(lines=lines)
    click.echo((result.stdout or result.stderr).rstrip())
    raise SystemExit(result.returncode)


@setup_group.command(name="doctor")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None)
def setup_doctor(root: Path | None) -> None:
    root_path = runner_root(root)
    checks = {
        "root": root_path.exists(),
        "binary": runner_binary(root_path).exists(),
        "config": runner_config(root_path).exists(),
        "registration": (root_path / ".runner").exists(),
    }
    render_json({"root": str(root_path), "checks": checks})

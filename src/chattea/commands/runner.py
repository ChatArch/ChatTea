from __future__ import annotations

import hashlib
import json
import lzma
import os
import platform
import re
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
RUNNER_SERVICE_PREFIX = "chattea-runner"
DEFAULT_RUNNER_NAME = "default"
DEFAULT_RUNNER_LABEL = "ubuntu-latest"
DEFAULT_RUNNER_BACKEND = "host"
RUNNER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def runner_home() -> Path:
    config = load_config()
    return (config.home or Path.home() / ".chatarch" / "chattea").expanduser()


def runner_root(root: Path | None = None) -> Path:
    return (root or runner_home() / "runner").expanduser()


def runner_instances_root(base: Path | None = None) -> Path:
    return (base or runner_home() / "runners").expanduser()


def validate_runner_name(name: str) -> str:
    value = name.strip()
    if not RUNNER_NAME_PATTERN.match(value):
        raise click.ClickException("Runner name must use letters, numbers, dots, underscores, or dashes, and must start with a letter or number.")
    return value


def runner_instance_root(name: str, *, root: Path | None = None, base: Path | None = None) -> Path:
    if root is not None:
        return root.expanduser()
    return runner_instances_root(base) / validate_runner_name(name)


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


def _split_labels(labels: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if labels is None:
        return []
    if isinstance(labels, str):
        return [part.strip() for part in labels.split(",") if part.strip()]
    return [str(part).strip() for part in labels if str(part).strip()]


def normalize_runner_labels(labels: str | list[str] | tuple[str, ...] | None = None, *, backend: str = DEFAULT_RUNNER_BACKEND) -> list[str]:
    values = _split_labels(labels) or [DEFAULT_RUNNER_LABEL]
    normalized: list[str] = []
    for label in values:
        normalized.append(label if ":" in label else f"{label}:{backend}")
    return normalized


def labels_for_register(labels: str | list[str] | tuple[str, ...] | None = None, *, backend: str = DEFAULT_RUNNER_BACKEND) -> str:
    return ",".join(normalize_runner_labels(labels, backend=backend))


def labels_for_runs_on(labels: list[str]) -> list[str]:
    return [label.split(":", 1)[0] for label in labels]


def _config_value(value: str | Path) -> str:
    return json.dumps(str(value))


def ensure_runner_config(
    root: Path | None = None,
    *,
    force: bool = False,
    labels: str | list[str] | tuple[str, ...] = f"{DEFAULT_RUNNER_LABEL}:{DEFAULT_RUNNER_BACKEND}",
    backend: str = DEFAULT_RUNNER_BACKEND,
    capacity: int = 1,
    workdir: Path | None = None,
) -> Path:
    root_path = runner_root(root)
    config_path = runner_config(root_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not force:
        return config_path
    if capacity < 1:
        raise click.ClickException("Runner capacity must be at least 1.")
    label_values = normalize_runner_labels(labels, backend=backend)
    label_lines = "\n".join(f"    - {json.dumps(label)}" for label in label_values)
    workdir_path = (workdir or root_path / "work").expanduser()
    host_block = ""
    if any(label.endswith(":host") for label in label_values):
        host_block = f"""
host:
  workdir_parent: {_config_value(workdir_path)}
"""
    config_path.write_text(
        f"""log:
  level: info

runner:
  file: .runner
  capacity: {capacity}
  timeout: 3h
  insecure: false
  fetch_timeout: 5s
  fetch_interval: 2s
  labels:
{label_lines}

cache:
  enabled: false
{host_block}""",
        encoding="utf-8",
    )
    return config_path


def read_runner_config_summary(root: Path | None = None) -> dict[str, Any]:
    root_path = runner_root(root)
    path = runner_config(root_path)
    summary: dict[str, Any] = {"capacity": None, "labels": [], "workdir": None, "backend": None}
    if not path.exists():
        return summary
    text = path.read_text(encoding="utf-8")
    capacity_match = re.search(r"(?m)^\s*capacity:\s*(\d+)\s*$", text)
    if capacity_match:
        summary["capacity"] = int(capacity_match.group(1))
    workdir_match = re.search(r"(?m)^\s*workdir_parent:\s*(.+?)\s*$", text)
    if workdir_match:
        raw = workdir_match.group(1).strip()
        try:
            summary["workdir"] = json.loads(raw)
        except json.JSONDecodeError:
            summary["workdir"] = raw.strip('"\'')
    labels: list[str] = []
    in_labels = False
    for line in text.splitlines():
        if re.match(r"^\s*labels:\s*$", line):
            in_labels = True
            continue
        if in_labels:
            match = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if match:
                raw_label = match.group(1).strip()
                try:
                    labels.append(str(json.loads(raw_label)))
                except json.JSONDecodeError:
                    labels.append(raw_label.strip('"\''))
                continue
            if line.strip() and not line.startswith(" "):
                in_labels = False
    summary["labels"] = labels
    for label in labels:
        if ":" in label:
            summary["backend"] = label.rsplit(":", 1)[1]
            break
    return summary


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


def register_runner(
    root: Path | None = None,
    *,
    scope: str = "repo",
    repo: str | None = None,
    org: str | None = None,
    name: str = "chattea-runner",
    labels: str = f"{DEFAULT_RUNNER_LABEL}:{DEFAULT_RUNNER_BACKEND}",
    backend: str = DEFAULT_RUNNER_BACKEND,
    capacity: int = 1,
    workdir: Path | None = None,
    version: str = "latest",
    binary_path: Path | None = None,
) -> Path:
    root_path = runner_root(root)
    root_path.mkdir(parents=True, exist_ok=True)
    label_string = labels_for_register(labels, backend=backend)
    binary = install_runner(root_path, version=version, binary_path=binary_path)
    config_path = ensure_runner_config(root_path, force=True, labels=label_string, backend=backend, capacity=capacity, workdir=workdir)
    token = _token_value(create_runner_token(scope, repo=repo, org=org))
    base_url = load_config().url
    subprocess.run(
        [str(binary), "register", "--no-interactive", "--instance", base_url, "--token", token, "--name", name, "--labels", label_string, "-c", str(config_path)],
        cwd=root_path,
        check=True,
    )
    return root_path / ".runner"


def runner_service_name(name: str) -> str:
    return f"{RUNNER_SERVICE_PREFIX}@{validate_runner_name(name)}.service"


def runner_service_path(name: str) -> Path:
    return Path("~/.config/systemd/user").expanduser() / runner_service_name(name)


def write_runner_service(root: Path | None = None, *, name: str) -> Path:
    root_path = runner_root(root)
    service_name = runner_service_name(name)
    path = runner_service_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""[Unit]
Description=ChatTea managed Gitea Actions runner {name}
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


def start_runner_service(root: Path | None = None, *, name: str) -> Path:
    service = write_runner_service(root, name=name)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", runner_service_name(name)], check=True)
    return service


def stop_runner_service(name: str) -> None:
    subprocess.run(["systemctl", "--user", "stop", runner_service_name(name)], check=False)


def disable_runner_service(name: str) -> None:
    service_name = runner_service_name(name)
    subprocess.run(["systemctl", "--user", "disable", "--now", service_name], check=False)
    wants_link = Path("~/.config/systemd/user/default.target.wants").expanduser() / service_name
    wants_link.unlink(missing_ok=True)
    runner_service_path(name).unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "reset-failed", service_name], check=False)


def restart_runner_service(root: Path | None = None, *, name: str) -> Path:
    service = write_runner_service(root, name=name)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "restart", runner_service_name(name)], check=True)
    return service


def runner_service_status(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["systemctl", "--user", "--no-pager", "--full", "status", runner_service_name(name)], capture_output=True, text=True, check=False)


def runner_service_logs(lines: int = 100, *, name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["journalctl", "--user", "-u", runner_service_name(name), "-n", str(lines), "--no-pager"], capture_output=True, text=True, check=False)


def create_local_runner(
    name: str,
    *,
    root: Path | None = None,
    base: Path | None = None,
    labels: str = DEFAULT_RUNNER_LABEL,
    backend: str = DEFAULT_RUNNER_BACKEND,
    capacity: int = 1,
    workdir: Path | None = None,
    force: bool = False,
    install: bool = False,
    version: str = "latest",
    binary_path: Path | None = None,
) -> dict[str, Any]:
    name = validate_runner_name(name)
    root_path = runner_instance_root(name, root=root, base=base)
    root_path.mkdir(parents=True, exist_ok=True)
    ensure_runner_config(root_path, force=force, labels=labels, backend=backend, capacity=capacity, workdir=workdir)
    if install or binary_path:
        install_runner(root_path, version=version, force=force, binary_path=binary_path)
    return local_runner_summary(name, root_path)


def register_local_runner(
    name: str,
    *,
    root: Path | None = None,
    base: Path | None = None,
    scope: str = "repo",
    repo: str | None = None,
    org: str | None = None,
    labels: str = DEFAULT_RUNNER_LABEL,
    backend: str = DEFAULT_RUNNER_BACKEND,
    capacity: int = 1,
    workdir: Path | None = None,
    version: str = "latest",
    binary_path: Path | None = None,
) -> dict[str, Any]:
    name = validate_runner_name(name)
    root_path = runner_instance_root(name, root=root, base=base)
    register_runner(root_path, scope=scope, repo=repo, org=org, name=name, labels=labels, backend=backend, capacity=capacity, workdir=workdir, version=version, binary_path=binary_path)
    return local_runner_summary(name, root_path)


def local_runner_summary(name: str, root: Path) -> dict[str, Any]:
    config_summary = read_runner_config_summary(root)
    service_name = runner_service_name(name)
    return {
        "name": name,
        "root": str(root),
        "binary": str(runner_binary(root)),
        "binary_exists": runner_binary(root).exists(),
        "config": str(runner_config(root)),
        "config_exists": runner_config(root).exists(),
        "registration_exists": (root / ".runner").exists(),
        "workdir": config_summary.get("workdir") or str(root / "work"),
        "workdir_exists": Path(config_summary.get("workdir") or root / "work").exists(),
        "labels": config_summary.get("labels") or [],
        "runs_on": labels_for_runs_on(config_summary.get("labels") or []),
        "backend": config_summary.get("backend"),
        "capacity": config_summary.get("capacity"),
        "service": service_name,
        "service_file": str(runner_service_path(name)),
        "service_file_exists": runner_service_path(name).exists(),
    }


def iter_local_runners(base: Path | None = None) -> list[dict[str, Any]]:
    root = runner_instances_root(base)
    if not root.exists():
        return []
    runners: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not RUNNER_NAME_PATTERN.match(path.name):
            continue
        if runner_config(path).exists() or (path / ".runner").exists() or runner_binary(path).exists():
            runners.append(local_runner_summary(path.name, path))
    return runners


def remove_local_runner(name: str, *, root: Path | None = None, base: Path | None = None, yes: bool = False) -> Path:
    name = validate_runner_name(name)
    root_path = runner_instance_root(name, root=root, base=base)
    if not yes:
        click.confirm(f"Remove local runner {name} at {root_path}?", abort=True)
    disable_runner_service(name)
    if root_path.exists():
        shutil.rmtree(root_path)
    return root_path


def pool_runner_name(pool: str, index: int) -> str:
    return f"{validate_runner_name(pool)}-{index}"


def pool_runners(pool: str, *, base: Path | None = None) -> list[dict[str, Any]]:
    prefix = f"{validate_runner_name(pool)}-"
    return [runner for runner in iter_local_runners(base) if runner["name"].startswith(prefix)]


def extract_runner_labels(payload: Any) -> list[str]:
    labels: set[str] = set()
    for runner in list_payload_items(payload):
        raw = runner.get("labels") or runner.get("label") or []
        if isinstance(raw, str):
            values = [item.strip() for item in raw.split(",") if item.strip()]
        elif isinstance(raw, list):
            values = []
            for item in raw:
                if isinstance(item, dict):
                    value = item.get("name") or item.get("label") or item.get("value")
                else:
                    value = str(item)
                if value:
                    values.append(str(value))
        else:
            values = []
        for value in values:
            labels.add(value.split(":", 1)[0])
    return sorted(labels)


def parse_workflow_runs_on(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    values: list[str] = []
    for match in re.finditer(r"(?m)^\s*runs-on:\s*(.+?)\s*$", text):
        raw = match.group(1).strip().strip('"\'')
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw.strip("[]")
            values.extend(part.strip().strip('"\'') for part in raw.split(",") if part.strip())
        elif raw:
            values.append(raw)
    return values


@click.group(name="runner")
def runner_group() -> None:
    """Manage Gitea Actions runners."""


def _scope_options(fn):
    fn = click.option("--org", default=None, help="Organization for org scope.")(fn)
    fn = click.option("--repo", default=None, help="Repository in OWNER/NAME format for repo scope.")(fn)
    fn = click.option("--scope", type=click.Choice(["repo", "org", "user", "admin"]), default="repo", show_default=True)(fn)
    return fn


def _local_root_options(fn):
    fn = click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None, help="Exact runner root. Overrides name-based root.")(fn)
    fn = click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None, help="Parent directory for managed runner instances.")(fn)
    return fn


def _runner_config_options(fn):
    fn = click.option("--workdir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Host backend workdir parent.")(fn)
    fn = click.option("--capacity", default=1, show_default=True, type=click.IntRange(1))(fn)
    fn = click.option("--backend", type=click.Choice(["host", "docker"]), default=DEFAULT_RUNNER_BACKEND, show_default=True)(fn)
    fn = click.option("--label", "labels", default=DEFAULT_RUNNER_LABEL, show_default=True, help="Runner label without backend suffix, or comma-separated labels.")(fn)
    return fn


def _install_options(fn):
    fn = click.option("--binary", "binary_path", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Copy an existing runner binary.")(fn)
    fn = click.option("--version", default="latest", show_default=True)(fn)
    return fn


@runner_group.group(name="registry")
def registry_group() -> None:
    """Manage runner records stored in Gitea."""


@registry_group.command(name="token")
@_scope_options
def registry_token(scope: str, repo: str | None, org: str | None) -> None:
    render_json(create_runner_token(scope, repo=repo, org=org))


@registry_group.command(name="list")
@_scope_options
@click.option("--json-output", is_flag=True)
def registry_list(scope: str, repo: str | None, org: str | None, json_output: bool) -> None:
    payload = list_registered_runners(scope, repo=repo, org=org)
    if json_output:
        render_json(payload)
        return
    render_items(list_payload_items(payload), "id", "name", "status", "active")


@registry_group.command(name="view")
@_scope_options
@click.argument("runner_id", type=int)
def registry_view(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    render_json(view_registered_runner(runner_id, scope, repo=repo, org=org))


@registry_group.command(name="enable")
@_scope_options
@click.argument("runner_id", type=int)
def registry_enable(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    render_json(edit_registered_runner(runner_id, scope, repo=repo, org=org, disabled=False))


@registry_group.command(name="disable")
@_scope_options
@click.argument("runner_id", type=int)
def registry_disable(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    render_json(edit_registered_runner(runner_id, scope, repo=repo, org=org, disabled=True))


@registry_group.command(name="delete")
@_scope_options
@click.argument("runner_id", type=int)
def registry_delete(scope: str, repo: str | None, org: str | None, runner_id: int) -> None:
    delete_registered_runner(runner_id, scope, repo=repo, org=org)
    click.echo(f"deleted: {runner_id}")


@runner_group.group(name="local")
def local_group() -> None:
    """Manage local runner instances."""


@local_group.command(name="install")
@click.argument("name", required=False, default=DEFAULT_RUNNER_NAME)
@_local_root_options
@_install_options
@click.option("--force", is_flag=True)
def local_install(name: str, root: Path | None, base: Path | None, version: str, binary_path: Path | None, force: bool) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    path = install_runner(root_path, version=version, force=force, binary_path=binary_path)
    click.echo(f"installed: {path}")


@local_group.command(name="create")
@click.argument("name")
@_local_root_options
@_runner_config_options
@_install_options
@click.option("--install/--no-install", default=False, show_default=True, help="Also install/copy gitea-runner binary.")
@click.option("--force", is_flag=True)
@click.option("--json-output", is_flag=True)
def local_create(
    name: str,
    root: Path | None,
    base: Path | None,
    labels: str,
    backend: str,
    capacity: int,
    workdir: Path | None,
    version: str,
    binary_path: Path | None,
    install: bool,
    force: bool,
    json_output: bool,
) -> None:
    payload = create_local_runner(name, root=root, base=base, labels=labels, backend=backend, capacity=capacity, workdir=workdir, force=force, install=install, version=version, binary_path=binary_path)
    if json_output:
        render_json(payload)
        return
    click.echo(f"created: {payload['name']}")
    click.echo(f"root: {payload['root']}")


@local_group.command(name="register")
@click.argument("name")
@_local_root_options
@_scope_options
@_runner_config_options
@_install_options
@click.option("--json-output", is_flag=True)
def local_register(
    name: str,
    root: Path | None,
    base: Path | None,
    scope: str,
    repo: str | None,
    org: str | None,
    labels: str,
    backend: str,
    capacity: int,
    workdir: Path | None,
    version: str,
    binary_path: Path | None,
    json_output: bool,
) -> None:
    payload = register_local_runner(name, root=root, base=base, scope=scope, repo=repo, org=org, labels=labels, backend=backend, capacity=capacity, workdir=workdir, version=version, binary_path=binary_path)
    if json_output:
        render_json(payload)
        return
    click.echo(f"registered: {payload['name']}")
    click.echo(f"root: {payload['root']}")


@local_group.command(name="list")
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--json-output", is_flag=True)
def local_list(base: Path | None, json_output: bool) -> None:
    payload = iter_local_runners(base)
    if json_output:
        render_json(payload)
        return
    render_items(payload, "name", "service", "config_exists", "registration_exists", "capacity", "runs_on")


@local_group.command(name="view")
@click.argument("name")
@_local_root_options
@click.option("--json-output", is_flag=True)
def local_view(name: str, root: Path | None, base: Path | None, json_output: bool) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    payload = local_runner_summary(validate_runner_name(name), root_path)
    if json_output:
        render_json(payload)
        return
    render_items([payload], "name", "root", "service", "labels", "capacity", "workdir")


@local_group.command(name="start")
@click.argument("name")
@_local_root_options
def local_start(name: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    service = start_runner_service(root_path, name=name)
    click.echo(f"started: {runner_service_name(name)}")
    click.echo(f"service: {service}")


@local_group.command(name="stop")
@click.argument("name")
def local_stop(name: str) -> None:
    stop_runner_service(name)
    click.echo(f"stopped: {runner_service_name(name)}")


@local_group.command(name="restart")
@click.argument("name")
@_local_root_options
def local_restart(name: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    service = restart_runner_service(root_path, name=name)
    click.echo(f"restarted: {runner_service_name(name)}")
    click.echo(f"service: {service}")


@local_group.command(name="status")
@click.argument("name")
def local_status(name: str) -> None:
    result = runner_service_status(name)
    click.echo((result.stdout or result.stderr).rstrip())
    raise SystemExit(result.returncode)


@local_group.command(name="logs")
@click.argument("name")
@click.option("--lines", default=100, show_default=True)
def local_logs(name: str, lines: int) -> None:
    result = runner_service_logs(lines=lines, name=name)
    click.echo((result.stdout or result.stderr).rstrip())
    raise SystemExit(result.returncode)


@local_group.command(name="doctor")
@click.argument("name")
@_local_root_options
def local_doctor(name: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    payload = local_runner_summary(validate_runner_name(name), root_path)
    payload["checks"] = {
        "root": Path(payload["root"]).exists(),
        "binary": payload["binary_exists"],
        "config": payload["config_exists"],
        "registration": payload["registration_exists"],
        "workdir": payload["workdir_exists"],
    }
    render_json(payload)


@local_group.command(name="remove")
@click.argument("name")
@_local_root_options
@click.option("--yes", is_flag=True, help="Do not prompt before removing local files.")
def local_remove(name: str, root: Path | None, base: Path | None, yes: bool) -> None:
    removed = remove_local_runner(name, root=root, base=base, yes=yes)
    click.echo(f"removed: {removed}")


@local_group.group(name="config")
def local_config_group() -> None:
    """Inspect or rewrite local runner config."""


@local_config_group.command(name="show")
@click.argument("name")
@_local_root_options
def local_config_show(name: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    render_json(read_runner_config_summary(root_path))


@local_config_group.command(name="set-labels")
@click.argument("name")
@click.option("--label", "labels", required=True, help="Comma-separated labels without backend suffix.")
@click.option("--backend", type=click.Choice(["host", "docker"]), default=DEFAULT_RUNNER_BACKEND, show_default=True)
@_local_root_options
def local_config_set_labels(name: str, labels: str, backend: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    current = read_runner_config_summary(root_path)
    ensure_runner_config(root_path, force=True, labels=labels, backend=backend, capacity=current.get("capacity") or 1, workdir=Path(current["workdir"]) if current.get("workdir") else None)
    click.echo(f"updated labels: {name}")


@local_config_group.command(name="set-capacity")
@click.argument("name")
@click.option("--capacity", required=True, type=click.IntRange(1))
@_local_root_options
def local_config_set_capacity(name: str, capacity: int, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    current = read_runner_config_summary(root_path)
    labels = ",".join(current.get("labels") or [f"{DEFAULT_RUNNER_LABEL}:{DEFAULT_RUNNER_BACKEND}"])
    ensure_runner_config(root_path, force=True, labels=labels, backend=current.get("backend") or DEFAULT_RUNNER_BACKEND, capacity=capacity, workdir=Path(current["workdir"]) if current.get("workdir") else None)
    click.echo(f"updated capacity: {name}")


@local_config_group.command(name="set-workdir")
@click.argument("name")
@click.option("--workdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@_local_root_options
def local_config_set_workdir(name: str, workdir: Path, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    current = read_runner_config_summary(root_path)
    labels = ",".join(current.get("labels") or [f"{DEFAULT_RUNNER_LABEL}:{DEFAULT_RUNNER_BACKEND}"])
    ensure_runner_config(root_path, force=True, labels=labels, backend=current.get("backend") or DEFAULT_RUNNER_BACKEND, capacity=current.get("capacity") or 1, workdir=workdir)
    click.echo(f"updated workdir: {name}")


@local_config_group.command(name="set-backend")
@click.argument("name")
@click.option("--backend", required=True, type=click.Choice(["host", "docker"]))
@_local_root_options
def local_config_set_backend(name: str, backend: str, root: Path | None, base: Path | None) -> None:
    root_path = runner_instance_root(name, root=root, base=base)
    current = read_runner_config_summary(root_path)
    runs_on = current.get("runs_on") or labels_for_runs_on(current.get("labels") or [])
    labels = ",".join(runs_on or [DEFAULT_RUNNER_LABEL])
    ensure_runner_config(root_path, force=True, labels=labels, backend=backend, capacity=current.get("capacity") or 1, workdir=Path(current["workdir"]) if current.get("workdir") else None)
    click.echo(f"updated backend: {name}")


@runner_group.group(name="pool")
def pool_group() -> None:
    """Manage a named group of local runners."""


@pool_group.command(name="create")
@click.argument("pool")
@click.option("--count", default=2, show_default=True, type=click.IntRange(1))
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
@_runner_config_options
@_install_options
@_scope_options
@click.option("--register/--no-register", default=False, show_default=True)
@click.option("--install/--no-install", default=False, show_default=True)
@click.option("--json-output", is_flag=True)
def pool_create(
    pool: str,
    count: int,
    base: Path | None,
    labels: str,
    backend: str,
    capacity: int,
    workdir: Path | None,
    version: str,
    binary_path: Path | None,
    scope: str,
    repo: str | None,
    org: str | None,
    register: bool,
    install: bool,
    json_output: bool,
) -> None:
    payload = []
    for index in range(1, count + 1):
        name = pool_runner_name(pool, index)
        runner_workdir = None if workdir is None else workdir / name
        if register:
            item = register_local_runner(name, base=base, scope=scope, repo=repo, org=org, labels=labels, backend=backend, capacity=capacity, workdir=runner_workdir, version=version, binary_path=binary_path)
        else:
            item = create_local_runner(name, base=base, labels=labels, backend=backend, capacity=capacity, workdir=runner_workdir, install=install, version=version, binary_path=binary_path)
        payload.append(item)
    if json_output:
        render_json({"pool": pool, "runners": payload})
        return
    render_items(payload, "name", "service", "config_exists", "registration_exists", "capacity", "runs_on")


@pool_group.command(name="start")
@click.argument("pool")
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
def pool_start(pool: str, base: Path | None) -> None:
    payload = pool_runners(pool, base=base)
    for runner in payload:
        start_runner_service(Path(runner["root"]), name=runner["name"])
    click.echo(f"started: {len(payload)} runner(s)")


@pool_group.command(name="stop")
@click.argument("pool")
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
def pool_stop(pool: str, base: Path | None) -> None:
    payload = pool_runners(pool, base=base)
    for runner in payload:
        stop_runner_service(runner["name"])
    click.echo(f"stopped: {len(payload)} runner(s)")


@pool_group.command(name="status")
@click.argument("pool")
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--json-output", is_flag=True)
def pool_status(pool: str, base: Path | None, json_output: bool) -> None:
    payload = pool_runners(pool, base=base)
    if json_output:
        render_json({"pool": pool, "runners": payload})
        return
    render_items(payload, "name", "service", "config_exists", "registration_exists", "capacity", "runs_on")


@pool_group.command(name="remove")
@click.argument("pool")
@click.option("--base", type=click.Path(file_okay=False, path_type=Path), default=None)
@click.option("--yes", is_flag=True)
def pool_remove(pool: str, base: Path | None, yes: bool) -> None:
    payload = pool_runners(pool, base=base)
    for runner in payload:
        remove_local_runner(runner["name"], base=base, yes=yes)
    click.echo(f"removed: {len(payload)} runner(s)")


@runner_group.group(name="workflow")
def workflow_group() -> None:
    """Inspect workflow runs-on labels against registered runners."""


@workflow_group.command(name="labels")
@_scope_options
@click.option("--json-output", is_flag=True)
def workflow_labels(scope: str, repo: str | None, org: str | None, json_output: bool) -> None:
    labels = extract_runner_labels(list_registered_runners(scope, repo=repo, org=org))
    if json_output:
        render_json({"labels": labels})
        return
    for label in labels:
        click.echo(label)


@workflow_group.command(name="example")
@click.option("--label", default=DEFAULT_RUNNER_LABEL, show_default=True)
def workflow_example(label: str) -> None:
    click.echo(
        f"""jobs:
  example:
    runs-on: {label}
    steps:
      - run: echo ok
""".rstrip()
    )


@workflow_group.command(name="check")
@click.argument("workflow", type=click.Path(dir_okay=False, path_type=Path))
@_scope_options
@click.option("--offline", is_flag=True, help="Only parse workflow runs-on values; do not query Gitea.")
@click.option("--json-output", is_flag=True)
def workflow_check(workflow: Path, scope: str, repo: str | None, org: str | None, offline: bool, json_output: bool) -> None:
    runs_on = parse_workflow_runs_on(workflow)
    available: list[str] = [] if offline else extract_runner_labels(list_registered_runners(scope, repo=repo, org=org))
    missing = [] if offline else [label for label in runs_on if label not in available]
    payload = {"workflow": str(workflow), "runs_on": runs_on, "available": available, "missing": missing, "offline": offline}
    if json_output:
        render_json(payload)
        return
    render_json(payload)
    if missing:
        raise SystemExit(1)

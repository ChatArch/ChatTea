from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import click

from chattea.config import load_config, mask_token
from chattea.credentials import configure_token as configure_credentials
from chattea.commands.token import parse_scopes


def _required_path(value: Path | None, name: str) -> Path:
    if value is None:
        raise click.ClickException(f"{name} is not configured.")
    return value.expanduser()


def _gitea_admin_user_base(binary: Path, config_path: Path, work_path: Path) -> list[str]:
    return [str(binary.expanduser()), "--config", str(config_path.expanduser()), "--work-path", str(work_path.expanduser()), "admin", "user"]


def _safe_process_detail(exc: subprocess.CalledProcessError, *secrets: str | None) -> str:
    detail = exc.stderr or exc.stdout or str(exc)
    for secret in secrets:
        if secret:
            detail = detail.replace(secret, "[REDACTED]")
    return detail.strip()


def _resolve_local_paths(
    *,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
) -> tuple[Path, Path, Path]:
    config = load_config()
    return (
        binary or _required_path(config.gitea_binary, "CHATTEA_BINARY"),
        config_path or _required_path(config.gitea_config, "CHATTEA_CONFIG"),
        work_path or _required_path(config.gitea_work_path, "CHATTEA_WORK_PATH"),
    )


def _run_admin_user(
    args: list[str],
    *,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
    secrets: tuple[str | None, ...] = (),
) -> str:
    target_binary, target_config, target_work = _resolve_local_paths(binary=binary, config_path=config_path, work_path=work_path)
    command = [*_gitea_admin_user_base(target_binary, target_config, target_work), *args]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(_safe_process_detail(exc, *secrets)) from exc
    return result.stdout.strip()


def extract_created_token(output: str) -> str | None:
    """Extract the one-time token printed by Gitea admin CLI output."""
    for line in output.splitlines():
        match = re.search(r"Access token was successfully created\.\.\.\s*(\S+)", line)
        if match:
            return match.group(1)
    stripped = output.strip()
    if stripped and "\n" not in stripped and " " not in stripped:
        return stripped
    return None


def create_bot_user_local(
    username: str,
    email: str,
    *,
    restricted: bool = True,
    token_name: str | None = None,
    scopes: list[str] | None = None,
    full_name: str | None = None,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
) -> dict[str, Any]:
    """Create a local Gitea bot user through the managed Gitea admin CLI."""
    args = ["create", "--username", username, "--email", email, "--user-type", "bot"]
    if restricted:
        args.append("--restricted")
    if full_name:
        args.extend(["--fullname", full_name])
    if token_name:
        args.extend(["--access-token", "--access-token-name", token_name, "--access-token-scopes", ",".join(scopes or ["all"])])
    output = _run_admin_user(args, binary=binary, config_path=config_path, work_path=work_path)
    token = extract_created_token(output) if token_name else None
    return {"username": username, "email": email, "restricted": restricted, "token_name": token_name, "token": token}


def create_bot_token_local(
    username: str,
    *,
    token_name: str,
    scopes: list[str] | None = None,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
) -> dict[str, Any]:
    """Generate a scoped token for an existing local bot/user through Gitea admin CLI."""
    output = _run_admin_user(
        [
            "generate-access-token",
            "--username",
            username,
            "--token-name",
            token_name,
            "--scopes",
            ",".join(scopes or ["all"]),
            "--raw",
        ],
        binary=binary,
        config_path=config_path,
        work_path=work_path,
    )
    token = extract_created_token(output)
    if not token:
        raise click.ClickException("Gitea admin CLI did not return a token.")
    return {"username": username, "token_name": token_name, "scopes": scopes or ["all"], "token": token}


def delete_bot_user_local(
    username: str,
    *,
    purge: bool = False,
    binary: Path | None = None,
    config_path: Path | None = None,
    work_path: Path | None = None,
) -> dict[str, Any]:
    """Delete a local Gitea bot/user through the managed Gitea admin CLI."""
    args = ["delete", "--username", username]
    if purge:
        args.append("--purge")
    _run_admin_user(args, binary=binary, config_path=config_path, work_path=work_path)
    return {"username": username, "deleted": True, "purge": purge}


def local_bot_plan() -> dict[str, Any]:
    """Inspect whether the configured local Gitea binary exposes bot primitives."""
    binary, config_path, work_path = _resolve_local_paths()
    plan: dict[str, Any] = {
        "backend": "local",
        "binary_exists": binary.exists(),
        "config_exists": config_path.exists(),
        "work_path_exists": work_path.exists(),
        "supports_bot_create": False,
        "supports_token_generate": False,
        "supports_user_delete": False,
    }
    probes = {
        "supports_bot_create": ["create", "--help"],
        "supports_token_generate": ["generate-access-token", "--help"],
        "supports_user_delete": ["delete", "--help"],
    }
    for key, args in probes.items():
        try:
            output = _run_admin_user(args)
        except click.ClickException:
            continue
        if key == "supports_bot_create":
            plan[key] = "--user-type" in output and "bot" in output
        elif key == "supports_token_generate":
            plan[key] = "generate-access-token" in output or "--raw" in output
        else:
            plan[key] = "delete" in output and "--username" in output
    return plan


def _safe_payload(payload: dict[str, Any], *, show_token: bool = False) -> dict[str, Any]:
    safe = dict(payload)
    if not show_token and safe.get("token"):
        safe["token"] = mask_token(str(safe["token"]))
    return safe


def _render_payload(payload: dict[str, Any], *, show_token: bool = False, json_output: bool = False) -> None:
    safe = _safe_payload(payload, show_token=show_token)
    if json_output:
        click.echo(json.dumps(safe, ensure_ascii=False, indent=2, default=str))
        return
    for key, value in safe.items():
        if value is not None:
            click.echo(f"{key}: {value}")


@click.group(name="bot")
def bot_group() -> None:
    """Manage local Gitea bot and service-account users."""


@bot_group.command(name="plan")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def bot_plan(json_output: bool) -> None:
    """Show local bot backend capability detected from the configured Gitea binary."""
    payload = local_bot_plan()
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo("backend: local")
    click.echo(f"binary_exists: {payload['binary_exists']}")
    click.echo(f"config_exists: {payload['config_exists']}")
    click.echo(f"work_path_exists: {payload['work_path_exists']}")
    click.echo(f"supports_bot_create: {payload['supports_bot_create']}")
    click.echo(f"supports_token_generate: {payload['supports_token_generate']}")
    click.echo(f"supports_user_delete: {payload['supports_user_delete']}")


@bot_group.command(name="create")
@click.option("--username", required=True, help="Bot username.")
@click.option("--email", required=True, help="Bot email address.")
@click.option("--restricted/--unrestricted", default=True, show_default=True, help="Create a restricted bot account by default.")
@click.option("--fullname", default=None, help="Bot display name.")
@click.option("--token-name", default=None, help="Also create an initial access token with this name.")
@click.option("--scope", "scopes", multiple=True, help="Token scope. May be repeated or comma-separated. Defaults to all when --token-name is set.")
@click.option("--show-token-once", is_flag=True, help="Print the raw token once. Default output is masked.")
@click.option("--save-as-current", is_flag=True, help="Save the generated token as the current ChatTea token.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def bot_create(
    username: str,
    email: str,
    restricted: bool,
    fullname: str | None,
    token_name: str | None,
    scopes: tuple[str, ...],
    show_token_once: bool,
    save_as_current: bool,
    json_output: bool,
) -> None:
    """Create a local Gitea bot user through the managed Gitea admin CLI."""
    payload = create_bot_user_local(username, email, restricted=restricted, token_name=token_name, scopes=parse_scopes(scopes), full_name=fullname)
    if save_as_current:
        if not payload.get("token"):
            raise click.ClickException("--save-as-current requires --token-name so a token is generated.")
        configured = configure_credentials(load_config().url, str(payload["token"]))
        payload["configured"] = {"base_url": configured.get("base_url"), "git_key": configured.get("git_key")}
    _render_payload(payload, show_token=show_token_once, json_output=json_output)


@bot_group.command(name="delete")
@click.argument("username")
@click.option("--purge", is_flag=True, help="Purge the user and owned data. Use only for disposable practice accounts.")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def bot_delete(username: str, purge: bool, yes: bool, json_output: bool) -> None:
    """Delete a local bot/user through the managed Gitea admin CLI."""
    if not yes:
        click.confirm(f"Delete local Gitea user {username!r}?", abort=True)
    payload = delete_bot_user_local(username, purge=purge)
    _render_payload(payload, json_output=json_output)


@bot_group.group(name="token")
def bot_token_group() -> None:
    """Manage local bot access tokens."""


@bot_token_group.command(name="create")
@click.argument("username")
@click.option("--token-name", default="default", show_default=True, help="Access token name.")
@click.option("--scope", "scopes", multiple=True, help="Token scope. May be repeated or comma-separated. Defaults to all.")
@click.option("--show-token-once", is_flag=True, help="Print the raw token once. Default output is masked.")
@click.option("--save-as-current", is_flag=True, help="Save the generated token as the current ChatTea token.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def bot_token_create(username: str, token_name: str, scopes: tuple[str, ...], show_token_once: bool, save_as_current: bool, json_output: bool) -> None:
    """Generate a scoped token for an existing local bot/user."""
    payload = create_bot_token_local(username, token_name=token_name, scopes=parse_scopes(scopes))
    if save_as_current:
        configured = configure_credentials(load_config().url, str(payload["token"]))
        payload["configured"] = {"base_url": configured.get("base_url"), "git_key": configured.get("git_key")}
    _render_payload(payload, show_token=show_token_once, json_output=json_output)

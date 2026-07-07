from __future__ import annotations

import json
import os
from typing import Any

import click

from chattea.api import GiteaAPIError, GiteaClient
from chattea.config import DEFAULT_BASE_URL, mask_token
from chattea.credentials import configure_token as configure_credentials

DEFAULT_TOKEN_NAME = "default"
DEFAULT_TOKEN_SCOPES = ("all",)
TOKEN_IF_EXISTS_CHOICES = ("error", "rotate")


def parse_scopes(scopes: tuple[str, ...] | list[str] | str | None) -> list[str]:
    if scopes is None:
        return list(DEFAULT_TOKEN_SCOPES)
    if isinstance(scopes, str):
        raw_items = [scopes]
    else:
        raw_items = list(scopes)
    parsed: list[str] = []
    for item in raw_items:
        parsed.extend(part.strip() for part in str(item).split(","))
    return [part for part in parsed if part] or list(DEFAULT_TOKEN_SCOPES)


def password_from_env(password_env: str) -> str:
    if not password_env:
        raise click.ClickException("--password-env is required so the password is not passed in argv.")
    value = os.getenv(password_env)
    if not value:
        raise click.ClickException(f"Environment variable {password_env} is not set or is empty.")
    return value


def list_access_tokens(username: str, password: str, *, base_url: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List Gitea access tokens through BasicAuth."""
    return GiteaClient(url=base_url, token="").list_access_tokens(username, password, limit=limit)


def create_access_token(username: str, password: str, *, name: str = DEFAULT_TOKEN_NAME, scopes: list[str] | None = None, base_url: str | None = None) -> dict[str, Any]:
    """Create a Gitea access token through BasicAuth."""
    return GiteaClient(url=base_url, token="").create_access_token(username, password, name=name, scopes=scopes or list(DEFAULT_TOKEN_SCOPES))


def delete_access_token(username: str, password: str, token_id_or_name: str, *, base_url: str | None = None) -> Any:
    """Delete a Gitea access token through BasicAuth."""
    return GiteaClient(url=base_url, token="").delete_access_token(username, password, token_id_or_name)


def token_name_exists_error(exc: GiteaAPIError) -> bool:
    """Return whether a Gitea token create error looks like a duplicate token name."""
    message = str(exc).lower()
    return exc.status_code in {400, 409, 422} and "token" in message and ("exist" in message or "already" in message)


def bootstrap_access_token(
    username: str,
    password: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    name: str = DEFAULT_TOKEN_NAME,
    scopes: list[str] | None = None,
    if_exists: str = "rotate",
) -> dict[str, Any]:
    """Create a token and immediately configure ChatTea credentials."""
    if if_exists not in TOKEN_IF_EXISTS_CHOICES:
        raise click.ClickException(f"Unsupported --if-exists value: {if_exists}")
    try:
        payload = create_access_token(username, password, name=name, scopes=scopes, base_url=base_url)
        token_action = "created"
    except GiteaAPIError as exc:
        if if_exists != "rotate" or not token_name_exists_error(exc):
            raise click.ClickException(str(exc)) from exc
        delete_access_token(username, password, name, base_url=base_url)
        payload = create_access_token(username, password, name=name, scopes=scopes, base_url=base_url)
        token_action = "rotated"
    token = payload.get("token") or payload.get("sha1")
    if not token:
        raise click.ClickException("Gitea did not return an access token.")
    configured = configure_credentials(base_url, str(token))
    return {"token": payload, "configured": configured, "token_action": token_action}


def _render_json(payload: Any) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _render_token_create(payload: dict[str, Any], *, show_token: bool = False) -> None:
    token = payload.get("token") or payload.get("sha1")
    click.echo(f"token: {token if show_token else mask_token(str(token) if token else None)}")
    if payload.get("name"):
        click.echo(f"name: {payload['name']}")
    if payload.get("id"):
        click.echo(f"id: {payload['id']}")
    if payload.get("scopes"):
        click.echo(f"scopes: {','.join(payload['scopes'])}")


@click.group(name="token")
def token_group() -> None:
    """Create and manage Gitea access tokens."""


@token_group.command(name="create")
@click.option("--base-url", default=None, help="Gitea website/API base URL.")
@click.option("--username", required=True, help="Gitea username.")
@click.option("--password-env", required=True, help="Environment variable containing the Gitea password.")
@click.option("--name", "token_name", default=DEFAULT_TOKEN_NAME, show_default=True, help="Access token name.")
@click.option("--scope", "scopes", multiple=True, help="Access token scope. May be repeated or comma-separated. Defaults to all.")
@click.option("--show-token", is_flag=True, help="Print the raw token once. Default output is masked.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def token_create(base_url: str | None, username: str, password_env: str, token_name: str, scopes: tuple[str, ...], show_token: bool, json_output: bool) -> None:
    """Create a Gitea access token using username/password BasicAuth."""
    payload = create_access_token(username, password_from_env(password_env), name=token_name, scopes=parse_scopes(scopes), base_url=base_url)
    if json_output:
        safe_payload = dict(payload)
        if not show_token:
            for key in ("token", "sha1"):
                if safe_payload.get(key):
                    safe_payload[key] = mask_token(str(safe_payload[key]))
        _render_json(safe_payload)
        return
    _render_token_create(payload, show_token=show_token)


@token_group.command(name="list")
@click.option("--base-url", default=None, help="Gitea website/API base URL.")
@click.option("--username", required=True, help="Gitea username.")
@click.option("--password-env", required=True, help="Environment variable containing the Gitea password.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option("--json-output", is_flag=True, help="Output JSON.")
def token_list(base_url: str | None, username: str, password_env: str, limit: int, json_output: bool) -> None:
    """List Gitea access tokens using username/password BasicAuth."""
    payload = list_access_tokens(username, password_from_env(password_env), base_url=base_url, limit=limit)
    if json_output:
        _render_json(payload)
        return
    for item in payload:
        click.echo(f"{item.get('id', '')}\t{item.get('name', '')}\t{','.join(item.get('scopes') or [])}\t{item.get('token_last_eight', '')}")


@token_group.command(name="delete")
@click.option("--base-url", default=None, help="Gitea website/API base URL.")
@click.option("--username", required=True, help="Gitea username.")
@click.option("--password-env", required=True, help="Environment variable containing the Gitea password.")
@click.argument("token_id_or_name")
def token_delete(base_url: str | None, username: str, password_env: str, token_id_or_name: str) -> None:
    """Delete a Gitea access token by id or name."""
    delete_access_token(username, password_from_env(password_env), token_id_or_name, base_url=base_url)
    click.echo(f"deleted: {token_id_or_name}")


@token_group.command(name="bootstrap")
@click.option("--base-url", default=DEFAULT_BASE_URL, show_default=True, help="Gitea website/API base URL.")
@click.option("--username", required=True, help="Gitea username.")
@click.option("--password-env", required=True, help="Environment variable containing the Gitea password.")
@click.option("--name", "token_name", default=DEFAULT_TOKEN_NAME, show_default=True, help="Access token name.")
@click.option("--scope", "scopes", multiple=True, help="Access token scope. May be repeated or comma-separated. Defaults to all.")
@click.option("--if-exists", type=click.Choice(TOKEN_IF_EXISTS_CHOICES), default="rotate", show_default=True, help="Behavior when the named token already exists.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
def token_bootstrap(base_url: str, username: str, password_env: str, token_name: str, scopes: tuple[str, ...], if_exists: str, json_output: bool) -> None:
    """Create a token and configure ChatTea/Git credentials in one step."""
    payload = bootstrap_access_token(username, password_from_env(password_env), base_url=base_url, name=token_name, scopes=parse_scopes(scopes), if_exists=if_exists)
    if json_output:
        safe_payload = dict(payload)
        safe_payload["token"] = dict(safe_payload["token"])
        for key in ("token", "sha1"):
            if safe_payload["token"].get(key):
                safe_payload["token"][key] = mask_token(str(safe_payload["token"][key]))
        _render_json(safe_payload)
        return
    _render_token_create(payload["token"], show_token=False)
    click.echo(f"token_action: {payload['token_action']}")
    configured = payload["configured"]
    click.echo(f"configured: {str(configured['base_url']).rstrip('/')}")
    if configured.get("env_path"):
        click.echo(f"config: {configured['env_path']}")
    if configured.get("git_key"):
        click.echo(f"git_config: {configured['git_key']}")

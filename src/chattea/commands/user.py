from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, render_items, render_json
from chattea.commands.token import password_from_env


def create_user(
    username: str,
    email: str,
    password: str,
    *,
    full_name: str | None = None,
    must_change_password: bool | None = None,
    restricted: bool | None = None,
    visibility: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    return client(url, token).create_user(
        username,
        email,
        password,
        full_name=full_name,
        must_change_password=must_change_password,
        restricted=restricted,
        visibility=visibility,
    )


def delete_user(username: str, *, purge: bool | None = None, url: str | None = None, token: str | None = None) -> Any:
    return client(url, token).delete_user(username, purge=purge)


@click.group(name="user")
def user_group() -> None:
    """Admin-managed Gitea user helpers."""


@user_group.command(name="create")
@click.option("--username", required=True)
@click.option("--email", required=True)
@click.option("--password-env", required=True, help="Environment variable containing the new user's password.")
@click.option("--full-name", default=None)
@click.option("--must-change-password/--no-must-change-password", default=None)
@click.option("--restricted/--not-restricted", default=None)
@click.option("--visibility", type=click.Choice(["public", "limited", "private"]), default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def user_create(
    username: str,
    email: str,
    password_env: str,
    full_name: str | None,
    must_change_password: bool | None,
    restricted: bool | None,
    visibility: str | None,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Create a user through the Gitea admin API."""
    payload = create_user(
        username,
        email,
        password_from_env(password_env),
        full_name=full_name,
        must_change_password=must_change_password,
        restricted=restricted,
        visibility=visibility,
        url=url,
        token=token,
    )
    if json_output:
        render_json(payload)
    else:
        render_items([payload], "id", "login", "email", "visibility")


@user_group.command(name="delete")
@click.argument("username")
@click.option("--purge", is_flag=True)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def user_delete(username: str, purge: bool, yes: bool, url: str | None, token: str | None) -> None:
    """Delete a user through the Gitea admin API."""
    if not yes:
        raise click.ClickException("Refusing to delete a user without --yes.")
    delete_user(username, purge=purge or None, url=url, token=token)
    click.echo(f"deleted: {username}")

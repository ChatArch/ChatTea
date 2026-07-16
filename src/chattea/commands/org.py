from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, csv_str_list, render_items, render_json


DEFAULT_DEVELOPER_UNITS = [
    "repo.code",
    "repo.issues",
    "repo.pulls",
    "repo.releases",
    "repo.projects",
    "repo.actions",
    "repo.wiki",
]


def create_org(
    username: str,
    *,
    full_name: str | None = None,
    description: str | None = None,
    email: str | None = None,
    visibility: str | None = None,
    repo_admin_change_team_access: bool | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    return client(url, token).create_org(
        username,
        full_name=full_name,
        description=description,
        email=email,
        visibility=visibility,
        repo_admin_change_team_access=repo_admin_change_team_access,
    )


def create_team(
    org: str,
    name: str,
    *,
    description: str | None = None,
    permission: str | None = None,
    includes_all_repositories: bool | None = None,
    can_create_org_repo: bool | None = None,
    units: list[str] | None = None,
    visibility: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    return client(url, token).create_org_team(
        org,
        name,
        description=description,
        permission=permission,
        includes_all_repositories=includes_all_repositories,
        can_create_org_repo=can_create_org_repo,
        units=units,
        visibility=visibility,
    )


@click.group(name="org")
def org_group() -> None:
    """Organization and team helpers."""


@org_group.command(name="list")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def org_list(limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = client(url, token).list_orgs(limit=limit)
    render_json(items) if json_output else render_items(items, "id", "username", "full_name", "visibility")


@org_group.command(name="view")
@click.argument("org")
@click.option("--url", default=None)
@click.option("--token", default=None)
def org_view(org: str, url: str | None, token: str | None) -> None:
    render_json(client(url, token).get_org(org))


@org_group.command(name="create")
@click.argument("username")
@click.option("--full-name", default=None)
@click.option("--description", default=None)
@click.option("--email", default=None)
@click.option("--visibility", type=click.Choice(["public", "limited", "private"]), default="private", show_default=True)
@click.option("--repo-admin-change-team-access/--no-repo-admin-change-team-access", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def org_create(
    username: str,
    full_name: str | None,
    description: str | None,
    email: str | None,
    visibility: str | None,
    repo_admin_change_team_access: bool | None,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Create an organization. Defaults to private visibility."""
    payload = create_org(
        username,
        full_name=full_name,
        description=description,
        email=email,
        visibility=visibility,
        repo_admin_change_team_access=repo_admin_change_team_access,
        url=url,
        token=token,
    )
    render_json(payload) if json_output else render_items([payload], "id", "username", "full_name", "visibility")


@org_group.group(name="team")
def team_group() -> None:
    """Organization team helpers."""


@team_group.command(name="list")
@click.argument("org")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def team_list(org: str, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = client(url, token).list_org_teams(org, limit=limit)
    render_json(items) if json_output else render_items(items, "id", "name", "permission", "includes_all_repositories")


@team_group.command(name="create")
@click.argument("org")
@click.option("--name", required=True)
@click.option("--description", default=None)
@click.option("--permission", type=click.Choice(["read", "write", "admin"]), default="write", show_default=True)
@click.option("--all-repos/--selected-repos", "includes_all_repositories", default=True, show_default=True)
@click.option("--can-create-repo/--no-can-create-repo", default=True, show_default=True)
@click.option("--unit", "units", default=None, help="Comma-separated repository units. Defaults to common development units.")
@click.option("--visibility", type=click.Choice(["public", "limited", "private"]), default="private", show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def team_create(
    org: str,
    name: str,
    description: str | None,
    permission: str,
    includes_all_repositories: bool,
    can_create_repo: bool,
    units: str | None,
    visibility: str,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Create a team. Defaults to write access over all organization repositories."""
    payload = create_team(
        org,
        name,
        description=description,
        permission=permission,
        includes_all_repositories=includes_all_repositories,
        can_create_org_repo=can_create_repo,
        units=csv_str_list(units) or DEFAULT_DEVELOPER_UNITS,
        visibility=visibility,
        url=url,
        token=token,
    )
    render_json(payload) if json_output else render_items([payload], "id", "name", "permission", "includes_all_repositories")


@team_group.group(name="member")
def team_member_group() -> None:
    """Team membership helpers."""


@team_member_group.command(name="add")
@click.argument("team_id", type=int)
@click.argument("username")
@click.option("--url", default=None)
@click.option("--token", default=None)
def team_member_add(team_id: int, username: str, url: str | None, token: str | None) -> None:
    client(url, token).add_team_member(team_id, username)
    click.echo(f"added: {username} -> team {team_id}")


@team_member_group.command(name="remove")
@click.argument("team_id", type=int)
@click.argument("username")
@click.option("--url", default=None)
@click.option("--token", default=None)
def team_member_remove(team_id: int, username: str, url: str | None, token: str | None) -> None:
    client(url, token).remove_team_member(team_id, username)
    click.echo(f"removed: {username} -> team {team_id}")

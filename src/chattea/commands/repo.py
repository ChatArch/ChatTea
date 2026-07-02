from __future__ import annotations

import json
from typing import Any

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs

from chattea.api import GiteaAPIError, GiteaClient, repo_clone_url
from chattea.config import load_config
from chattea.git import clone_repo as git_clone_repo


REPO_FIELD = CommandField("repo", prompt="Repository (owner/name)", required=True)
REPO_VIEW_SCHEMA = CommandSchema(name="repo view", fields=(REPO_FIELD,))
REPO_CLONE_SCHEMA = CommandSchema(name="repo clone", fields=(REPO_FIELD,))
REPO_CREATE_SCHEMA = CommandSchema(
    name="repo create",
    fields=(CommandField("name", prompt="Repository name", required=True),),
)
REPO_MIGRATE_SCHEMA = CommandSchema(
    name="repo migrate",
    fields=(
        CommandField("clone_url", prompt="Source Git clone URL", required=True),
        CommandField("owner", prompt="Target Gitea owner or organization", required=True),
        CommandField("name", prompt="Target repository name", required=True),
    ),
)


def split_repo(value: str) -> tuple[str, str]:
    owner, sep, repo = value.partition("/")
    if sep != "/" or not owner or not repo:
        raise click.ClickException("Repository must be in owner/name form.")
    return owner, repo


def list_repositories(owner: str | None = None, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    """List repositories from the configured Gitea API."""
    return GiteaClient(url=url, token=token).list_repos(owner=owner, limit=limit)


def view_repository(repo: str, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    """Return details for one owner/name repository."""
    owner, name = split_repo(repo)
    return GiteaClient(url=url, token=token).view_repo(owner, name)


def create_repository(
    name: str,
    owner: str | None = None,
    description: str | None = None,
    public_repo: bool = False,
    default_branch: str = "main",
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Create a repository in the configured Gitea instance."""
    return GiteaClient(url=url, token=token).create_repo(
        name=name,
        owner=owner,
        private=not public_repo,
        description=description,
        default_branch=default_branch,
    )


def clone_repository(repo: str, directory: str | None = None, url: str | None = None) -> dict[str, Any]:
    """Clone a repository from the configured Gitea base URL."""
    owner, name = split_repo(repo)
    config = load_config()
    base_url = (url or config.url).rstrip("/")
    clone_url = repo_clone_url(base_url, owner, name)
    payload = git_clone_repo(clone_url, directory=directory)
    payload["repo"] = repo
    return payload


def migrate_repository(
    clone_url: str,
    owner: str,
    name: str,
    public_repo: bool = False,
    mirror: bool = False,
    auth_username: str | None = None,
    auth_password: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Create a Gitea migration from an existing Git clone URL."""
    return GiteaClient(url=url, token=token).migrate_repo(
        clone_url=clone_url,
        owner=owner,
        name=name,
        private=not public_repo,
        mirror=mirror,
        auth_username=auth_username,
        auth_password=auth_password,
    )


@click.group(name="repo")
def repo_group() -> None:
    """Repository helpers."""


@repo_group.command(name="list")
@click.option("--owner", default=None, help="Organization owner. Omit to list current user's repositories.")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def repo_list(owner: str | None, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    """List repositories."""
    try:
        payload = list_repositories(owner=owner, limit=limit, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_repo_table(payload)


@repo_group.command(name="view")
@click.argument("repo", required=False)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def repo_view(repo: str | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Show repository details."""
    values = resolve_command_inputs(
        schema=REPO_VIEW_SCHEMA,
        provided={"repo": repo},
        interactive=interactive,
        usage="Usage: chattea repo view OWNER/NAME [-i|-I]",
    )
    try:
        payload = view_repository(values["repo"], url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"Repo: {payload.get('full_name') or values['repo']}")
    click.echo(f"Private: {payload.get('private')}")
    click.echo(f"Default Branch: {payload.get('default_branch') or ''}")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


@repo_group.command(name="create")
@click.option("--owner", default=None, help="Owner or organization. Defaults to authenticated user.")
@click.option("--name", default=None, help="Repository name.")
@click.option("--description", default=None)
@click.option("--public", "public_repo", is_flag=True, help="Create a public repository. Defaults to private.")
@click.option("--default-branch", default="main", show_default=True)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def repo_create(
    owner: str | None,
    name: str | None,
    description: str | None,
    public_repo: bool,
    default_branch: str,
    url: str | None,
    token: str | None,
    json_output: bool,
    interactive: bool | None,
) -> None:
    """Create a repository."""
    values = resolve_command_inputs(
        schema=REPO_CREATE_SCHEMA,
        provided={"name": name},
        interactive=interactive,
        usage="Usage: chattea repo create --name NAME [-i|-I]",
    )
    try:
        payload = create_repository(
            name=values["name"],
            owner=owner,
            description=description,
            public_repo=public_repo,
            default_branch=default_branch,
            url=url,
            token=token,
        )
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    private = "private" if payload.get("private") else "public"
    click.echo(f"created: {payload.get('full_name') or values['name']} ({private})")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


@repo_group.command(name="clone")
@click.argument("repo", required=False)
@click.argument("directory", required=False)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--json-output", is_flag=True)
@add_interactive_option
def repo_clone(repo: str | None, directory: str | None, url: str | None, json_output: bool, interactive: bool | None) -> None:
    """Clone a Gitea repository."""
    values = resolve_command_inputs(
        schema=REPO_CLONE_SCHEMA,
        provided={"repo": repo},
        interactive=interactive,
        usage="Usage: chattea repo clone OWNER/NAME [DIRECTORY] [-i|-I]",
    )
    try:
        payload = clone_repository(values["repo"], directory=directory, url=url)
    except Exception as exc:
        raise click.ClickException(f"git clone failed for {values['repo']}: {exc}") from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"cloned: {values['repo']}")
    click.echo(f"path: {payload['path']}")


@repo_group.command(name="migrate")
@click.option("--clone-url", default=None, help="Source Git clone URL.")
@click.option("--owner", default=None, help="Target Gitea owner or organization.")
@click.option("--name", default=None, help="Target repository name.")
@click.option("--public", "public_repo", is_flag=True, help="Create a public repository. Defaults to private.")
@click.option("--mirror", is_flag=True, help="Create as mirror repository.")
@click.option("--auth-username", default=None, help="Source repository username.")
@click.option("--auth-password", default=None, help="Source repository password or token.")
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_GITEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def repo_migrate(
    clone_url: str | None,
    owner: str | None,
    name: str | None,
    public_repo: bool,
    mirror: bool,
    auth_username: str | None,
    auth_password: str | None,
    url: str | None,
    token: str | None,
    json_output: bool,
    interactive: bool | None,
) -> None:
    """Migrate an existing Git repository into Gitea."""
    values = resolve_command_inputs(
        schema=REPO_MIGRATE_SCHEMA,
        provided={"clone_url": clone_url, "owner": owner, "name": name},
        interactive=interactive,
        usage="Usage: chattea repo migrate --clone-url URL --owner OWNER --name NAME [-i|-I]",
    )
    try:
        payload = migrate_repository(
            clone_url=values["clone_url"],
            owner=values["owner"],
            name=values["name"],
            public_repo=public_repo,
            mirror=mirror,
            auth_username=auth_username,
            auth_password=auth_password,
            url=url,
            token=token,
        )
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    fallback_name = f"{values['owner']}/{values['name']}"
    click.echo(f"migrated: {payload.get('full_name') or fallback_name}")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


def _echo_repo_table(items: list[dict[str, Any]]) -> None:
    columns = [("repo", "full_name"), ("private", "private"), ("branch", "default_branch"), ("updated", "updated_at")]
    rows: list[list[str]] = []
    for item in items:
        rows.append([str(item.get(key) if item.get(key) is not None else "")[:48] for _, key in columns])
    widths = [len(label) for label, _ in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    click.echo("  ".join(label.ljust(widths[index]) for index, (label, _) in enumerate(columns)))
    click.echo("  ".join("-" * width for width in widths))
    for row in rows:
        click.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))

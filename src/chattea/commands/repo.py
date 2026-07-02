from __future__ import annotations

import json
from typing import Any

import click

from chattea.api import GiteaAPIError, GiteaClient, repo_clone_url
from chattea.config import load_config
from chattea.git import clone_repo as git_clone_repo


def split_repo(value: str) -> tuple[str, str]:
    owner, sep, repo = value.partition("/")
    if sep != "/" or not owner or not repo:
        raise click.ClickException("Repository must be in owner/name form.")
    return owner, repo


@click.group(name="repo")
def repo_group() -> None:
    """Repository helpers."""


@repo_group.command(name="list")
@click.option("--owner", default=None, help="Organization owner. Omit to list current user's repositories.")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def repo_list(owner: str | None, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    """List repositories."""
    try:
        payload = GiteaClient(url=url, token=token).list_repos(owner=owner, limit=limit)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_repo_table(payload)


@repo_group.command(name="view")
@click.argument("repo")
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def repo_view(repo: str, url: str | None, token: str | None, json_output: bool) -> None:
    """Show repository details."""
    owner, name = split_repo(repo)
    try:
        payload = GiteaClient(url=url, token=token).view_repo(owner, name)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"Repo: {payload.get('full_name') or repo}")
    click.echo(f"Private: {payload.get('private')}")
    click.echo(f"Default Branch: {payload.get('default_branch') or ''}")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


@repo_group.command(name="create")
@click.option("--owner", default=None, help="Owner or organization. Defaults to authenticated user.")
@click.option("--name", required=True, help="Repository name.")
@click.option("--description", default=None)
@click.option("--public", "public_repo", is_flag=True, help="Create a public repository. Defaults to private.")
@click.option("--default-branch", default="main", show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def repo_create(
    owner: str | None,
    name: str,
    description: str | None,
    public_repo: bool,
    default_branch: str,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Create a repository."""
    try:
        payload = GiteaClient(url=url, token=token).create_repo(
            name=name,
            owner=owner,
            private=not public_repo,
            description=description,
            default_branch=default_branch,
        )
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    private = "private" if payload.get("private") else "public"
    click.echo(f"created: {payload.get('full_name') or name} ({private})")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


@repo_group.command(name="clone")
@click.argument("repo")
@click.argument("directory", required=False)
@click.option("--url", default=None, help="Gitea base URL. Defaults to saved config.")
@click.option("--token", default=None)
@click.option("--set-token/--no-set-token", default=True, show_default=True)
@click.option("--json-output", is_flag=True)
def repo_clone(repo: str, directory: str | None, url: str | None, token: str | None, set_token: bool, json_output: bool) -> None:
    """Clone a Gitea repository."""
    owner, name = split_repo(repo)
    config = load_config()
    base_url = (url or config.url).rstrip("/")
    resolved_token = token if token is not None else config.token
    clone_url = repo_clone_url(base_url, owner, name)
    try:
        payload = git_clone_repo(clone_url, directory=directory, token=resolved_token, set_token_after=set_token)
    except Exception as exc:
        raise click.ClickException(f"git clone failed for {repo}: {exc}") from exc
    payload["repo"] = repo
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"cloned: {repo}")
    click.echo(f"path: {payload['path']}")
    click.echo(f"token: {'configured' if payload.get('token_configured') else 'not configured'}")


@repo_group.command(name="migrate")
@click.option("--clone-url", required=True, help="Source Git clone URL.")
@click.option("--owner", required=True, help="Target Gitea owner or organization.")
@click.option("--name", required=True, help="Target repository name.")
@click.option("--public", "public_repo", is_flag=True, help="Create a public repository. Defaults to private.")
@click.option("--mirror", is_flag=True, help="Create as mirror repository.")
@click.option("--auth-username", default=None, help="Source repository username.")
@click.option("--auth-password", default=None, help="Source repository password or token.")
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def repo_migrate(
    clone_url: str,
    owner: str,
    name: str,
    public_repo: bool,
    mirror: bool,
    auth_username: str | None,
    auth_password: str | None,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Migrate an existing Git repository into Gitea."""
    try:
        payload = GiteaClient(url=url, token=token).migrate_repo(
            clone_url=clone_url,
            owner=owner,
            name=name,
            private=not public_repo,
            mirror=mirror,
            auth_username=auth_username,
            auth_password=auth_password,
        )
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"migrated: {payload.get('full_name') or f'{owner}/{name}'}")
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

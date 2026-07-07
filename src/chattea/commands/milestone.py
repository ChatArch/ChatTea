from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts


def list_milestones(repo: str, *, state: str = "open", name: str | None = None, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).list_milestones(owner, repo_name, state=state, name=name, limit=limit)


def view_milestone(repo: str, milestone_id: int | str, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).get_milestone(owner, repo_name, milestone_id)


def create_milestone(repo: str, title: str, *, description: str | None = None, deadline: str | None = None, state: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).create_milestone(owner, repo_name, title, description=description, deadline=deadline, state=state)


def edit_milestone(repo: str, milestone_id: int | str, *, title: str | None = None, description: str | None = None, deadline: str | None = None, state: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).edit_milestone(owner, repo_name, milestone_id, title=title, description=description, deadline=deadline, state=state)


def close_milestone(repo: str, milestone_id: int | str, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    return edit_milestone(repo, milestone_id, state="closed", url=url, token=token)


def delete_milestone(repo: str, milestone_id: int | str, *, url: str | None = None, token: str | None = None) -> None:
    owner, repo_name = repo_parts(repo)
    client(url, token).delete_milestone(owner, repo_name, milestone_id)


@click.group(name="milestone")
def milestone_group() -> None:
    """Repository milestone helpers."""


@milestone_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.option("--state", default="open", show_default=True, type=click.Choice(["open", "closed", "all"]))
@click.option("--name", default=None)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def milestone_list(repo_name: str, state: str, name: str | None, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_milestones(repo_name, state=state, name=name, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "state", "title", "due_on")


@milestone_group.command(name="view")
@click.option("--repo", "repo_name", required=True)
@click.argument("milestone_id")
@click.option("--url", default=None)
@click.option("--token", default=None)
def milestone_view(repo_name: str, milestone_id: str, url: str | None, token: str | None) -> None:
    render_json(view_milestone(repo_name, milestone_id, url=url, token=token))


@milestone_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.option("--title", required=True)
@click.option("--description", default=None)
@click.option("--deadline", default=None, help="ISO datetime accepted by Gitea.")
@click.option("--state", default=None, type=click.Choice(["open", "closed"]))
@click.option("--url", default=None)
@click.option("--token", default=None)
def milestone_create(repo_name: str, title: str, description: str | None, deadline: str | None, state: str | None, url: str | None, token: str | None) -> None:
    payload = create_milestone(repo_name, title, description=description, deadline=deadline, state=state, url=url, token=token)
    click.echo(f"created: {payload.get('id', '')} {payload.get('title', title)}")


@milestone_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("milestone_id")
@click.option("--title", default=None)
@click.option("--description", default=None)
@click.option("--deadline", default=None)
@click.option("--state", default=None, type=click.Choice(["open", "closed"]))
@click.option("--url", default=None)
@click.option("--token", default=None)
def milestone_edit(repo_name: str, milestone_id: str, title: str | None, description: str | None, deadline: str | None, state: str | None, url: str | None, token: str | None) -> None:
    payload = edit_milestone(repo_name, milestone_id, title=title, description=description, deadline=deadline, state=state, url=url, token=token)
    click.echo(f"updated: {payload.get('id', milestone_id)}")


@milestone_group.command(name="close")
@click.option("--repo", "repo_name", required=True)
@click.argument("milestone_id")
@click.option("--url", default=None)
@click.option("--token", default=None)
def milestone_close(repo_name: str, milestone_id: str, url: str | None, token: str | None) -> None:
    close_milestone(repo_name, milestone_id, url=url, token=token)
    click.echo(f"closed: {milestone_id}")


@milestone_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("milestone_id")
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def milestone_delete(repo_name: str, milestone_id: str, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_milestone(repo_name, milestone_id, url=url, token=token)
    click.echo(f"deleted: {milestone_id}")

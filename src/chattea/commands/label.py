from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts


def list_labels(repo: str, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_labels(owner, name, limit=limit)


def view_label(repo: str, label_id: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_label(owner, name, label_id)


def create_label(repo: str, name: str, color: str, *, description: str | None = None, exclusive: bool | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).create_label(owner, repo_name, name, color, description=description, exclusive=exclusive)


def edit_label(repo: str, label_id: int, *, name: str | None = None, color: str | None = None, description: str | None = None, exclusive: bool | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).edit_label(owner, repo_name, label_id, name=name, color=color, description=description, exclusive=exclusive)


def delete_label(repo: str, label_id: int, *, url: str | None = None, token: str | None = None) -> None:
    owner, repo_name = repo_parts(repo)
    client(url, token).delete_label(owner, repo_name, label_id)


@click.group(name="label")
def label_group() -> None:
    """Repository label helpers."""


@label_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def label_list(repo_name: str, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_labels(repo_name, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "name", "color", "description")


@label_group.command(name="view")
@click.option("--repo", "repo_name", required=True)
@click.argument("label_id", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def label_view(repo_name: str, label_id: int, url: str | None, token: str | None) -> None:
    render_json(view_label(repo_name, label_id, url=url, token=token))


@label_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.option("--name", required=True)
@click.option("--color", required=True, help="Hex color without or with leading #.")
@click.option("--description", default=None)
@click.option("--exclusive/--no-exclusive", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def label_create(repo_name: str, name: str, color: str, description: str | None, exclusive: bool | None, url: str | None, token: str | None) -> None:
    payload = create_label(repo_name, name, color, description=description, exclusive=exclusive, url=url, token=token)
    click.echo(f"created: {payload.get('id', '')} {payload.get('name', name)}")


@label_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("label_id", type=int)
@click.option("--name", default=None)
@click.option("--color", default=None)
@click.option("--description", default=None)
@click.option("--exclusive/--no-exclusive", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def label_edit(repo_name: str, label_id: int, name: str | None, color: str | None, description: str | None, exclusive: bool | None, url: str | None, token: str | None) -> None:
    payload = edit_label(repo_name, label_id, name=name, color=color, description=description, exclusive=exclusive, url=url, token=token)
    click.echo(f"updated: {payload.get('id', label_id)}")


@label_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("label_id", type=int)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def label_delete(repo_name: str, label_id: int, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_label(repo_name, label_id, url=url, token=token)
    click.echo(f"deleted: {label_id}")

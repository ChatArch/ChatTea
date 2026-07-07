from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, csv_int_list, csv_str_list, render_items, render_json, repo_parts


def list_issues(repo: str, *, state: str = "open", labels: str | None = None, milestones: str | None = None, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_issues(owner, name, state=state, labels=labels, milestones=milestones, limit=limit)


def view_issue(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_issue(owner, name, index)


def create_issue(repo: str, title: str, *, body: str | None = None, labels: list[int] | None = None, milestone: int | None = None, assignees: list[str] | None = None, closed: bool | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).create_issue(owner, name, title, body, labels=labels, milestone=milestone, assignees=assignees, closed=closed)


def edit_issue(repo: str, index: int, *, title: str | None = None, body: str | None = None, state: str | None = None, labels: list[int] | None = None, milestone: int | None = None, assignees: list[str] | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).edit_issue(owner, name, index, title=title, body=body, state=state, labels=labels, milestone=milestone, assignees=assignees)


def close_issue(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    return edit_issue(repo, index, state="closed", url=url, token=token)


def reopen_issue(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    return edit_issue(repo, index, state="open", url=url, token=token)


def delete_issue(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> None:
    owner, name = repo_parts(repo)
    client(url, token).delete_issue(owner, name, index)


def list_comments(repo: str, index: int, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_issue_comments(owner, name, index, limit=limit)


def create_comment(repo: str, index: int, body: str, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).create_issue_comment(owner, name, index, body)


def edit_comment(repo: str, comment_id: int, body: str, *, index: int | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).edit_issue_comment(owner, name, comment_id, body, index=index)


def delete_comment(repo: str, comment_id: int, *, index: int | None = None, url: str | None = None, token: str | None = None) -> None:
    owner, name = repo_parts(repo)
    client(url, token).delete_issue_comment(owner, name, comment_id, index=index)


def add_labels(repo: str, index: int, labels: list[int], *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).add_issue_labels(owner, name, index, labels)


def remove_label(repo: str, index: int, label_id: int, *, url: str | None = None, token: str | None = None) -> None:
    owner, name = repo_parts(repo)
    client(url, token).remove_issue_label(owner, name, index, label_id)


def add_assignees(repo: str, index: int, assignees: list[str], *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).add_issue_assignees(owner, name, index, assignees)


def remove_assignees(repo: str, index: int, assignees: list[str], *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).remove_issue_assignees(owner, name, index, assignees)


@click.group(name="issue")
def issue_group() -> None:
    """Repository issue helpers."""


@issue_group.command(name="list")
@click.option("--repo", "repo_name", required=True, help="Repository in OWNER/NAME format.")
@click.option("--state", default="open", show_default=True, type=click.Choice(["open", "closed", "all"]))
@click.option("--label", "labels", default=None, help="Comma-separated label names.")
@click.option("--milestone", "milestones", default=None, help="Comma-separated milestone names.")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def issue_list(repo_name: str, state: str, labels: str | None, milestones: str | None, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_issues(repo_name, state=state, labels=labels, milestones=milestones, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "number", "state", "title", "user")


@issue_group.command(name="view")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_view(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    render_json(view_issue(repo_name, index, url=url, token=token))


@issue_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.option("--title", required=True)
@click.option("--body", default=None)
@click.option("--label", "labels", default=None, help="Comma-separated label IDs.")
@click.option("--milestone", type=int, default=None)
@click.option("--assignee", "assignees", default=None, help="Comma-separated usernames.")
@click.option("--closed", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_create(repo_name: str, title: str, body: str | None, labels: str | None, milestone: int | None, assignees: str | None, closed: bool, url: str | None, token: str | None) -> None:
    payload = create_issue(repo_name, title, body=body, labels=csv_int_list(labels), milestone=milestone, assignees=csv_str_list(assignees), closed=closed or None, url=url, token=token)
    click.echo(f"created: #{payload.get('number', payload.get('id', ''))} {payload.get('title', title)}")


@issue_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--title", default=None)
@click.option("--body", default=None)
@click.option("--state", type=click.Choice(["open", "closed"]), default=None)
@click.option("--label", "labels", default=None, help="Comma-separated label IDs.")
@click.option("--milestone", type=int, default=None)
@click.option("--assignee", "assignees", default=None, help="Comma-separated usernames.")
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_edit(repo_name: str, index: int, title: str | None, body: str | None, state: str | None, labels: str | None, milestone: int | None, assignees: str | None, url: str | None, token: str | None) -> None:
    payload = edit_issue(repo_name, index, title=title, body=body, state=state, labels=csv_int_list(labels), milestone=milestone, assignees=csv_str_list(assignees), url=url, token=token)
    click.echo(f"updated: #{payload.get('number', index)}")


@issue_group.command(name="close")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_close(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    close_issue(repo_name, index, url=url, token=token)
    click.echo(f"closed: #{index}")


@issue_group.command(name="reopen")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_reopen(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    reopen_issue(repo_name, index, url=url, token=token)
    click.echo(f"reopened: #{index}")


@issue_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_delete(repo_name: str, index: int, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_issue(repo_name, index, url=url, token=token)
    click.echo(f"deleted: #{index}")


@issue_group.group(name="comment")
def comment_group() -> None:
    """Issue comment helpers."""


@comment_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def comment_list(repo_name: str, index: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_comments(repo_name, index, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "body", "user")


@comment_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--body", required=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def comment_create(repo_name: str, index: int, body: str, url: str | None, token: str | None) -> None:
    payload = create_comment(repo_name, index, body, url=url, token=token)
    click.echo(f"created: {payload.get('id', '')}")


@comment_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("comment_id", type=int)
@click.option("--issue", "index", type=int, default=None)
@click.option("--body", required=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def comment_edit(repo_name: str, comment_id: int, index: int | None, body: str, url: str | None, token: str | None) -> None:
    edit_comment(repo_name, comment_id, body, index=index, url=url, token=token)
    click.echo(f"updated: {comment_id}")


@comment_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("comment_id", type=int)
@click.option("--issue", "index", type=int, default=None)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def comment_delete(repo_name: str, comment_id: int, index: int | None, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_comment(repo_name, comment_id, index=index, url=url, token=token)
    click.echo(f"deleted: {comment_id}")


@issue_group.group(name="label")
def issue_label_group() -> None:
    """Issue label assignment helpers."""


@issue_label_group.command(name="add")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.argument("label_ids")
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_label_add(repo_name: str, index: int, label_ids: str, url: str | None, token: str | None) -> None:
    add_labels(repo_name, index, csv_int_list(label_ids) or [], url=url, token=token)
    click.echo(f"labels-added: #{index}")


@issue_label_group.command(name="remove")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.argument("label_id", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def issue_label_remove(repo_name: str, index: int, label_id: int, url: str | None, token: str | None) -> None:
    remove_label(repo_name, index, label_id, url=url, token=token)
    click.echo(f"label-removed: #{index}")


@issue_group.group(name="assign")
def assign_group() -> None:
    """Issue assignee helpers."""


@assign_group.command(name="add")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.argument("assignees")
@click.option("--url", default=None)
@click.option("--token", default=None)
def assign_add(repo_name: str, index: int, assignees: str, url: str | None, token: str | None) -> None:
    add_assignees(repo_name, index, csv_str_list(assignees) or [], url=url, token=token)
    click.echo(f"assignees-added: #{index}")


@assign_group.command(name="remove")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.argument("assignees")
@click.option("--url", default=None)
@click.option("--token", default=None)
def assign_remove(repo_name: str, index: int, assignees: str, url: str | None, token: str | None) -> None:
    remove_assignees(repo_name, index, csv_str_list(assignees) or [], url=url, token=token)
    click.echo(f"assignees-removed: #{index}")

from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, csv_int_list, csv_str_list, render_items, render_json, repo_parts


def list_prs(repo: str, *, state: str = "open", limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_pulls(owner, name, state=state, limit=limit)


def view_pr(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_pull(owner, name, index)


def create_pr(repo: str, title: str, head: str, base: str, *, body: str | None = None, labels: list[int] | None = None, milestone: int | None = None, assignees: list[str] | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).create_pull(owner, name, title, head, base, body=body, labels=labels, milestone=milestone, assignees=assignees)


def edit_pr(repo: str, index: int, *, title: str | None = None, body: str | None = None, state: str | None = None, base: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).edit_pull(owner, name, index, title=title, body=body, state=state, base=base)


def close_pr(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    return edit_pr(repo, index, state="closed", url=url, token=token)


def reopen_pr(repo: str, index: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    return edit_pr(repo, index, state="open", url=url, token=token)


def merge_pr(repo: str, index: int, *, merge_style: str = "merge", title: str | None = None, message: str | None = None, delete_branch: bool | None = None, url: str | None = None, token: str | None = None) -> None:
    owner, name = repo_parts(repo)
    client(url, token).merge_pull(owner, name, index, merge_style=merge_style, title=title, message=message, delete_branch_after_merge=delete_branch)


def diff_pr(repo: str, index: int, *, patch: bool = False, url: str | None = None, token: str | None = None) -> str:
    owner, name = repo_parts(repo)
    return client(url, token).get_pull_diff(owner, name, index, diff_type="patch" if patch else "diff")


def list_commits(repo: str, index: int, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_pull_commits(owner, name, index, limit=limit)


def list_files(repo: str, index: int, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_pull_files(owner, name, index, limit=limit)


def list_reviews(repo: str, index: int, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_pull_reviews(owner, name, index, limit=limit)


def create_review(repo: str, index: int, *, body: str | None = None, event: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).create_pull_review(owner, name, index, body=body, event=event)


def submit_review(repo: str, index: int, review_id: int, *, body: str | None = None, event: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).submit_pull_review(owner, name, index, review_id, body=body, event=event)


@click.group(name="pr")
def pr_group() -> None:
    """Repository pull request helpers."""


@pr_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.option("--state", default="open", show_default=True, type=click.Choice(["open", "closed", "all"]))
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def pr_list(repo_name: str, state: str, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_prs(repo_name, state=state, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "number", "state", "title", "user")


@pr_group.command(name="view")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_view(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    render_json(view_pr(repo_name, index, url=url, token=token))


@pr_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.option("--title", required=True)
@click.option("--head", required=True)
@click.option("--base", required=True)
@click.option("--body", default=None)
@click.option("--label", "labels", default=None, help="Comma-separated label IDs.")
@click.option("--milestone", type=int, default=None)
@click.option("--assignee", "assignees", default=None, help="Comma-separated usernames.")
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_create(repo_name: str, title: str, head: str, base: str, body: str | None, labels: str | None, milestone: int | None, assignees: str | None, url: str | None, token: str | None) -> None:
    payload = create_pr(repo_name, title, head, base, body=body, labels=csv_int_list(labels), milestone=milestone, assignees=csv_str_list(assignees), url=url, token=token)
    click.echo(f"created: #{payload.get('number', payload.get('id', ''))} {payload.get('title', title)}")


@pr_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--title", default=None)
@click.option("--body", default=None)
@click.option("--state", type=click.Choice(["open", "closed"]), default=None)
@click.option("--base", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_edit(repo_name: str, index: int, title: str | None, body: str | None, state: str | None, base: str | None, url: str | None, token: str | None) -> None:
    edit_pr(repo_name, index, title=title, body=body, state=state, base=base, url=url, token=token)
    click.echo(f"updated: #{index}")


@pr_group.command(name="close")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_close(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    close_pr(repo_name, index, url=url, token=token)
    click.echo(f"closed: #{index}")


@pr_group.command(name="reopen")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_reopen(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    reopen_pr(repo_name, index, url=url, token=token)
    click.echo(f"reopened: #{index}")


@pr_group.command(name="merge")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--method", "merge_style", default="merge", show_default=True)
@click.option("--title", default=None)
@click.option("--message", default=None)
@click.option("--delete-branch", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_merge(repo_name: str, index: int, merge_style: str, title: str | None, message: str | None, delete_branch: bool, url: str | None, token: str | None) -> None:
    merge_pr(repo_name, index, merge_style=merge_style, title=title, message=message, delete_branch=delete_branch or None, url=url, token=token)
    click.echo(f"merged: #{index}")


@pr_group.command(name="diff")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_diff(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    click.echo(diff_pr(repo_name, index, url=url, token=token))


@pr_group.command(name="patch")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_patch(repo_name: str, index: int, url: str | None, token: str | None) -> None:
    click.echo(diff_pr(repo_name, index, patch=True, url=url, token=token))


@pr_group.command(name="commits")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def pr_commits(repo_name: str, index: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_commits(repo_name, index, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "sha", "message", "url")


@pr_group.command(name="files")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def pr_files(repo_name: str, index: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_files(repo_name, index, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "filename", "status", "additions", "deletions")


@pr_group.group(name="comment")
def pr_comment_group() -> None:
    """Pull request issue-comment helpers."""


@pr_comment_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def pr_comment_list(repo_name: str, index: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    owner, name = repo_parts(repo_name)
    items = client(url, token).list_issue_comments(owner, name, index, limit=limit)
    render_json(items) if json_output else render_items(items, "id", "body", "user")


@pr_comment_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--body", required=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def pr_comment_create(repo_name: str, index: int, body: str, url: str | None, token: str | None) -> None:
    owner, name = repo_parts(repo_name)
    payload = client(url, token).create_issue_comment(owner, name, index, body)
    click.echo(f"created: {payload.get('id', '')}")


@pr_group.group(name="review")
def review_group() -> None:
    """Pull request review helpers."""


@review_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def review_list(repo_name: str, index: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_reviews(repo_name, index, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "state", "user", "body")


@review_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.option("--body", default=None)
@click.option("--event", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def review_create(repo_name: str, index: int, body: str | None, event: str | None, url: str | None, token: str | None) -> None:
    payload = create_review(repo_name, index, body=body, event=event, url=url, token=token)
    click.echo(f"created: {payload.get('id', '')}")


@review_group.command(name="submit")
@click.option("--repo", "repo_name", required=True)
@click.argument("index", type=int)
@click.argument("review_id", type=int)
@click.option("--body", default=None)
@click.option("--event", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def review_submit(repo_name: str, index: int, review_id: int, body: str | None, event: str | None, url: str | None, token: str | None) -> None:
    submit_review(repo_name, index, review_id, body=body, event=event, url=url, token=token)
    click.echo(f"submitted: {review_id}")

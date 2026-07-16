from __future__ import annotations

import time
from typing import Any

import click

from chattea.commands._shared import client, csv_str_list, render_items, render_json


def list_notifications(
    *,
    all_: bool | None = None,
    status_types: list[str] | None = None,
    subject_types: list[str] | None = None,
    since: str | None = None,
    before: str | None = None,
    limit: int = 50,
    url: str | None = None,
    token: str | None = None,
) -> list[dict[str, Any]]:
    return client(url, token).list_notifications(
        all_=all_,
        status_types=status_types,
        subject_types=subject_types,
        since=since,
        before=before,
        limit=limit,
    )


@click.group(name="notification")
def notification_group() -> None:
    """User notification helpers for mention-driven workflows."""


@notification_group.command(name="list")
@click.option("--all", "all_", is_flag=True, help="Include read notifications.")
@click.option("--status", "status_types", default=None, help="Comma-separated statuses: unread,read,pinned.")
@click.option("--subject", "subject_types", default=None, help="Comma-separated subject types: issue,pull,commit,repository.")
@click.option("--since", default=None, help="Only show notifications updated after this RFC3339 timestamp.")
@click.option("--before", default=None, help="Only show notifications updated before this RFC3339 timestamp.")
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def notification_list(
    all_: bool,
    status_types: str | None,
    subject_types: str | None,
    since: str | None,
    before: str | None,
    limit: int,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """List notifications for the authenticated user/token."""
    items = list_notifications(
        all_=all_ or None,
        status_types=csv_str_list(status_types),
        subject_types=csv_str_list(subject_types),
        since=since,
        before=before,
        limit=limit,
        url=url,
        token=token,
    )
    render_json(items) if json_output else render_items(items, "id", "status", "updated_at", "subject", "repository")


@notification_group.command(name="view")
@click.argument("thread_id")
@click.option("--url", default=None)
@click.option("--token", default=None)
def notification_view(thread_id: str, url: str | None, token: str | None) -> None:
    """Show one notification thread."""
    render_json(client(url, token).get_notification_thread(thread_id))


@notification_group.command(name="mark-read")
@click.argument("thread_id")
@click.option("--status", default="read", show_default=True, type=click.Choice(["read", "unread", "pinned"]))
@click.option("--url", default=None)
@click.option("--token", default=None)
def notification_mark_read(thread_id: str, status: str, url: str | None, token: str | None) -> None:
    """Mark one notification thread read, unread, or pinned."""
    client(url, token).mark_notification_thread(thread_id, status=status)
    click.echo(f"marked: {thread_id} -> {status}")


@notification_group.command(name="poll")
@click.option("--status", "status_types", default="unread", show_default=True, help="Comma-separated statuses to poll.")
@click.option("--subject", "subject_types", default="issue,pull", show_default=True, help="Comma-separated subject types.")
@click.option("--interval", default=5, type=click.IntRange(min=1), show_default=True)
@click.option("--max-wait", default=60, type=click.IntRange(min=1), show_default=True)
@click.option("--limit", default=20, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def notification_poll(
    status_types: str,
    subject_types: str,
    interval: int,
    max_wait: int,
    limit: int,
    url: str | None,
    token: str | None,
    json_output: bool,
) -> None:
    """Poll notifications until at least one matching thread is found."""
    deadline = time.monotonic() + max_wait
    while True:
        items = list_notifications(
            status_types=csv_str_list(status_types),
            subject_types=csv_str_list(subject_types),
            limit=limit,
            url=url,
            token=token,
        )
        if items:
            render_json(items) if json_output else render_items(items, "id", "status", "updated_at", "subject", "repository")
            return
        if time.monotonic() >= deadline:
            raise click.ClickException("No matching notifications before --max-wait expired.")
        time.sleep(interval)

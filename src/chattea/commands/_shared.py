from __future__ import annotations

import json
from typing import Any

import click

from chattea.api import GiteaClient


def repo_parts(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise click.ClickException("Repository must use OWNER/NAME format.")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise click.ClickException("Repository must use OWNER/NAME format.")
    return owner, name


def client(url: str | None = None, token: str | None = None) -> GiteaClient:
    return GiteaClient(url=url, token=token)


def int_list(values: tuple[int, ...] | list[int] | None) -> list[int] | None:
    if not values:
        return None
    return [int(value) for value in values]


def csv_int_list(value: str | None) -> list[int] | None:
    if not value:
        return None
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def csv_str_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def render_json(payload: Any) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def render_items(items: list[dict[str, Any]], *fields: str) -> None:
    for item in items:
        click.echo("\t".join(str(item.get(field, "")) for field in fields))

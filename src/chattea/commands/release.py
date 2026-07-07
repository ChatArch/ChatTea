from __future__ import annotations

from typing import Any

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts


def list_releases(repo: str, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = repo_parts(repo)
    return client(url, token).list_releases(owner, name, limit=limit)


def view_release(repo: str, release_id: int, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_release(owner, name, release_id)


def latest_release(repo: str, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_latest_release(owner, name)


def release_by_tag(repo: str, tag: str, *, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = repo_parts(repo)
    return client(url, token).get_release_by_tag(owner, name, tag)


def create_release(repo: str, tag: str, *, name: str | None = None, body: str | None = None, target: str | None = None, draft: bool | None = None, prerelease: bool | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).create_release(owner, repo_name, tag, name=name, body=body, target_commitish=target, draft=draft, prerelease=prerelease)


def edit_release(repo: str, release_id: int, *, tag: str | None = None, name: str | None = None, body: str | None = None, target: str | None = None, draft: bool | None = None, prerelease: bool | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).edit_release(owner, repo_name, release_id, tag_name=tag, name=name, body=body, target_commitish=target, draft=draft, prerelease=prerelease)


def delete_release(repo: str, release_id: int, *, url: str | None = None, token: str | None = None) -> None:
    owner, repo_name = repo_parts(repo)
    client(url, token).delete_release(owner, repo_name, release_id)


def list_assets(repo: str, release_id: int, *, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, repo_name = repo_parts(repo)
    return client(url, token).list_release_assets(owner, repo_name, release_id, limit=limit)


def delete_asset(repo: str, release_id: int, asset_id: int, *, url: str | None = None, token: str | None = None) -> None:
    owner, repo_name = repo_parts(repo)
    client(url, token).delete_release_asset(owner, repo_name, release_id, asset_id)


@click.group(name="release")
def release_group() -> None:
    """Repository release helpers."""


@release_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def release_list(repo_name: str, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_releases(repo_name, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "tag_name", "name", "draft", "prerelease")


@release_group.command(name="view")
@click.option("--repo", "repo_name", required=True)
@click.argument("release_id", type=int)
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_view(repo_name: str, release_id: int, url: str | None, token: str | None) -> None:
    render_json(view_release(repo_name, release_id, url=url, token=token))


@release_group.command(name="latest")
@click.option("--repo", "repo_name", required=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_latest(repo_name: str, url: str | None, token: str | None) -> None:
    render_json(latest_release(repo_name, url=url, token=token))


@release_group.command(name="by-tag")
@click.option("--repo", "repo_name", required=True)
@click.argument("tag")
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_by_tag_command(repo_name: str, tag: str, url: str | None, token: str | None) -> None:
    render_json(release_by_tag(repo_name, tag, url=url, token=token))


@release_group.command(name="create")
@click.option("--repo", "repo_name", required=True)
@click.option("--tag", required=True)
@click.option("--name", default=None)
@click.option("--body", default=None)
@click.option("--target", default=None)
@click.option("--draft/--no-draft", default=None)
@click.option("--prerelease/--no-prerelease", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_create(repo_name: str, tag: str, name: str | None, body: str | None, target: str | None, draft: bool | None, prerelease: bool | None, url: str | None, token: str | None) -> None:
    payload = create_release(repo_name, tag, name=name, body=body, target=target, draft=draft, prerelease=prerelease, url=url, token=token)
    click.echo(f"created: {payload.get('id', '')} {payload.get('tag_name', tag)}")


@release_group.command(name="edit")
@click.option("--repo", "repo_name", required=True)
@click.argument("release_id", type=int)
@click.option("--tag", default=None)
@click.option("--name", default=None)
@click.option("--body", default=None)
@click.option("--target", default=None)
@click.option("--draft/--no-draft", default=None)
@click.option("--prerelease/--no-prerelease", default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_edit(repo_name: str, release_id: int, tag: str | None, name: str | None, body: str | None, target: str | None, draft: bool | None, prerelease: bool | None, url: str | None, token: str | None) -> None:
    edit_release(repo_name, release_id, tag=tag, name=name, body=body, target=target, draft=draft, prerelease=prerelease, url=url, token=token)
    click.echo(f"updated: {release_id}")


@release_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("release_id", type=int)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def release_delete(repo_name: str, release_id: int, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_release(repo_name, release_id, url=url, token=token)
    click.echo(f"deleted: {release_id}")


@release_group.group(name="asset")
def asset_group() -> None:
    """Release asset helpers."""


@asset_group.command(name="list")
@click.option("--repo", "repo_name", required=True)
@click.argument("release_id", type=int)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
def asset_list(repo_name: str, release_id: int, limit: int, url: str | None, token: str | None, json_output: bool) -> None:
    items = list_assets(repo_name, release_id, limit=limit, url=url, token=token)
    render_json(items) if json_output else render_items(items, "id", "name", "size", "browser_download_url")


@asset_group.command(name="delete")
@click.option("--repo", "repo_name", required=True)
@click.argument("release_id", type=int)
@click.argument("asset_id", type=int)
@click.option("--yes", is_flag=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
def asset_delete(repo_name: str, release_id: int, asset_id: int, yes: bool, url: str | None, token: str | None) -> None:
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    delete_asset(repo_name, release_id, asset_id, url=url, token=token)
    click.echo(f"deleted: {asset_id}")

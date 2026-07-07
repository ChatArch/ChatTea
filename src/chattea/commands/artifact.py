from __future__ import annotations

from pathlib import Path

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts
from chattea.commands.actions_shared import list_payload_items


def list_artifacts(repo: str, run_id: int | None = None, limit: int = 50, page: int | None = None):
    owner, name = repo_parts(repo)
    return client().list_action_artifacts(owner, name, run_id=run_id, limit=limit, page=page)


def view_artifact(repo: str, artifact_id: int):
    owner, name = repo_parts(repo)
    return client().get_action_artifact(owner, name, artifact_id)


def download_artifact(repo: str, artifact_id: int, output: Path) -> Path:
    owner, name = repo_parts(repo)
    payload = client().download_action_artifact_zip(owner, name, artifact_id)
    data = payload.encode() if isinstance(payload, str) else payload
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return output


def delete_artifact(repo: str, artifact_id: int):
    owner, name = repo_parts(repo)
    return client().delete_action_artifact(owner, name, artifact_id)


@click.group(name="artifact")
def artifact_group() -> None:
    """Inspect and download Gitea Actions artifacts."""


@artifact_group.command(name="list")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.option("--run-id", type=int, default=None, help="Limit artifacts to one run.")
@click.option("--limit", default=50, show_default=True)
@click.option("--page", default=None, type=int)
@click.option("--json-output", is_flag=True)
def list_command(repo: str, run_id: int | None, limit: int, page: int | None, json_output: bool) -> None:
    payload = list_artifacts(repo, run_id=run_id, limit=limit, page=page)
    if json_output:
        render_json(payload)
        return
    render_items(list_payload_items(payload, "artifacts"), "id", "name", "size_in_bytes", "expired")


@artifact_group.command(name="view")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("artifact_id", type=int)
def view_command(repo: str, artifact_id: int) -> None:
    render_json(view_artifact(repo, artifact_id))


@artifact_group.command(name="download")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("artifact_id", type=int)
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), required=True, help="Output zip file.")
def download_command(repo: str, artifact_id: int, output: Path) -> None:
    path = download_artifact(repo, artifact_id, output)
    click.echo(f"downloaded: {path}")


@artifact_group.command(name="delete")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("artifact_id", type=int)
def delete_command(repo: str, artifact_id: int) -> None:
    delete_artifact(repo, artifact_id)
    click.echo(f"deleted: {artifact_id}")

from __future__ import annotations

import click

from chattea.commands._shared import client, render_json, repo_parts


def view_job(repo: str, job_id: int):
    owner, name = repo_parts(repo)
    return client().get_action_job(owner, name, job_id)


def job_logs(repo: str, job_id: int) -> str:
    owner, name = repo_parts(repo)
    return client().get_action_job_logs(owner, name, job_id)


def rerun_job(repo: str, run_id: int, job_id: int):
    owner, name = repo_parts(repo)
    return client().rerun_action_job(owner, name, run_id, job_id)


@click.group(name="job")
def job_group() -> None:
    """Inspect and rerun Gitea Actions jobs."""


@job_group.command(name="view")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("job_id", type=int)
def view_command(repo: str, job_id: int) -> None:
    render_json(view_job(repo, job_id))


@job_group.command(name="logs")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("job_id", type=int)
def logs_command(repo: str, job_id: int) -> None:
    click.echo(job_logs(repo, job_id))


@job_group.command(name="rerun")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.option("--run-id", required=True, type=int, help="Parent workflow run ID.")
@click.argument("job_id", type=int)
def rerun_command(repo: str, run_id: int, job_id: int) -> None:
    rerun_job(repo, run_id, job_id)
    click.echo(f"rerun_job: {job_id}")

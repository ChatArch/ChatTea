from __future__ import annotations

import click

from chattea.commands._shared import client, render_items, render_json, repo_parts
from chattea.commands.actions_shared import list_payload_items


def list_runs(repo: str, state: str | None = None, limit: int = 50, page: int | None = None):
    owner, name = repo_parts(repo)
    return client().list_action_runs(owner, name, status=state, limit=limit, page=page)


def view_run(repo: str, run_id: int):
    owner, name = repo_parts(repo)
    return client().get_action_run(owner, name, run_id)


def list_run_jobs(repo: str, run_id: int, limit: int = 50, page: int | None = None):
    owner, name = repo_parts(repo)
    return client().list_action_run_jobs(owner, name, run_id, limit=limit, page=page)


def rerun_run(repo: str, run_id: int, failed_only: bool = False):
    owner, name = repo_parts(repo)
    if failed_only:
        return client().rerun_failed_action_run(owner, name, run_id)
    return client().rerun_action_run(owner, name, run_id)


def delete_run(repo: str, run_id: int):
    owner, name = repo_parts(repo)
    return client().delete_action_run(owner, name, run_id)


def run_logs(repo: str, run_id: int, job_id: int | None = None) -> str:
    owner, name = repo_parts(repo)
    c = client()
    if job_id is not None:
        return c.get_action_job_logs(owner, name, job_id)
    jobs_payload = c.list_action_run_jobs(owner, name, run_id)
    chunks: list[str] = []
    for job in list_payload_items(jobs_payload, "jobs"):
        jid = job.get("id")
        if jid is None:
            continue
        title = job.get("name") or job.get("title") or jid
        chunks.append(f"===== job {jid}: {title} =====")
        chunks.append(str(c.get_action_job_logs(owner, name, int(jid))))
    return "\n".join(chunks)


@click.group(name="run")
def run_group() -> None:
    """Inspect and control Gitea Actions workflow runs."""


@run_group.command(name="list")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.option("--state", default=None, help="Optional run status filter.")
@click.option("--limit", default=50, show_default=True)
@click.option("--page", default=None, type=int)
@click.option("--json-output", is_flag=True)
def list_command(repo: str, state: str | None, limit: int, page: int | None, json_output: bool) -> None:
    payload = list_runs(repo, state=state, limit=limit, page=page)
    if json_output:
        render_json(payload)
        return
    render_items(list_payload_items(payload), "id", "status", "conclusion", "event", "display_title")


@run_group.command(name="view")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
def view_command(repo: str, run_id: int) -> None:
    render_json(view_run(repo, run_id))


@run_group.command(name="jobs")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
@click.option("--json-output", is_flag=True)
def jobs_command(repo: str, run_id: int, json_output: bool) -> None:
    payload = list_run_jobs(repo, run_id)
    if json_output:
        render_json(payload)
        return
    render_items(list_payload_items(payload, "jobs"), "id", "status", "conclusion", "name")


@run_group.command(name="logs")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
@click.option("--job-id", type=int, default=None, help="Fetch one job log instead of all jobs in the run.")
def logs_command(repo: str, run_id: int, job_id: int | None) -> None:
    click.echo(run_logs(repo, run_id, job_id=job_id))


@run_group.command(name="rerun")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
def rerun_command(repo: str, run_id: int) -> None:
    rerun_run(repo, run_id)
    click.echo(f"rerun: {run_id}")


@run_group.command(name="rerun-failed")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
def rerun_failed_command(repo: str, run_id: int) -> None:
    rerun_run(repo, run_id, failed_only=True)
    click.echo(f"rerun_failed: {run_id}")


@run_group.command(name="delete")
@click.option("--repo", required=True, help="Repository in OWNER/NAME format.")
@click.argument("run_id", type=int)
def delete_command(repo: str, run_id: int) -> None:
    delete_run(repo, run_id)
    click.echo(f"deleted: {run_id}")

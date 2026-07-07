from __future__ import annotations

import json
from typing import Any

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs

from chattea.api import GiteaAPIError, GiteaClient
from chattea.commands.repo import split_repo

REPO_FIELD = CommandField("repo", prompt="Repository (owner/name)", required=True)
PROJECT_CREATE_SCHEMA = CommandSchema(
    name="project create",
    fields=(REPO_FIELD, CommandField("title", prompt="Project title", required=True)),
)
PROJECT_REPO_SCHEMA = CommandSchema(name="project", fields=(REPO_FIELD,))
COLUMN_CREATE_SCHEMA = CommandSchema(
    name="project column create",
    fields=(REPO_FIELD, CommandField("title", prompt="Column title", required=True)),
)


def _client(url: str | None = None, token: str | None = None) -> GiteaClient:
    return GiteaClient(url=url, token=token)


def _echo_json_or_project(payload: dict[str, Any] | None, *, json_output: bool, fallback: str = "project") -> None:
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not payload:
        click.echo(f"{fallback}: ok")
        return
    title = payload.get("title") or payload.get("name") or ""
    ident = payload.get("id") or ""
    click.echo(f"{fallback}: {ident} {title}".rstrip())
    if payload.get("state"):
        click.echo(f"state: {payload['state']}")
    elif "is_closed" in payload:
        click.echo(f"closed: {payload['is_closed']}")
    if payload.get("type"):
        click.echo(f"type: {payload['type']}")


def _echo_table(items: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    rows = [[str(item.get(key) if item.get(key) is not None else "")[:48] for _, key in columns] for item in items]
    widths = [len(label) for label, _ in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    click.echo("  ".join(label.ljust(widths[index]) for index, (label, _) in enumerate(columns)))
    click.echo("  ".join("-" * width for width in widths))
    for row in rows:
        click.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _repo_parts(repo: str) -> tuple[str, str]:
    return split_repo(repo)


def list_projects(repo: str, state: str = "open", limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = _repo_parts(repo)
    return _client(url, token).list_repo_projects(owner, name, state=state, limit=limit)


def view_project(repo: str, project_id: int, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = _repo_parts(repo)
    return _client(url, token).get_repo_project(owner, name, project_id)


def create_project(
    repo: str,
    title: str,
    description: str | None = None,
    card_type: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    owner, name = _repo_parts(repo)
    return _client(url, token).create_repo_project(owner, name, title, description=description, card_type=card_type)


def edit_project(
    repo: str,
    project_id: int,
    title: str | None = None,
    description: str | None = None,
    state: str | None = None,
    card_type: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    owner, name = _repo_parts(repo)
    return _client(url, token).edit_repo_project(owner, name, project_id, title=title, description=description, state=state, card_type=card_type)


def delete_project(repo: str, project_id: int, url: str | None = None, token: str | None = None) -> None:
    owner, name = _repo_parts(repo)
    _client(url, token).delete_repo_project(owner, name, project_id)


def list_columns(repo: str, project_id: int, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = _repo_parts(repo)
    return _client(url, token).list_project_columns(owner, name, project_id, limit=limit)


def create_column(repo: str, project_id: int, title: str, color: str | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any]:
    owner, name = _repo_parts(repo)
    return _client(url, token).create_project_column(owner, name, project_id, title, color=color)


def edit_column(
    repo: str,
    project_id: int,
    column_id: int,
    title: str | None = None,
    color: str | None = None,
    sorting: int | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    owner, name = _repo_parts(repo)
    return _client(url, token).edit_project_column(owner, name, project_id, column_id, title=title, color=color, sorting=sorting)


def delete_column(repo: str, project_id: int, column_id: int, url: str | None = None, token: str | None = None) -> None:
    owner, name = _repo_parts(repo)
    _client(url, token).delete_project_column(owner, name, project_id, column_id)


def list_column_issues(repo: str, project_id: int, column_id: int, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    owner, name = _repo_parts(repo)
    return _client(url, token).list_project_column_issues(owner, name, project_id, column_id, limit=limit)


def list_cards(repo: str, project_id: int, column_id: int, limit: int = 50, url: str | None = None, token: str | None = None) -> list[dict[str, Any]]:
    """List issue/PR cards in a project column."""
    return list_column_issues(repo, project_id, column_id, limit=limit, url=url, token=token)


def add_issue(repo: str, project_id: int, column_id: int, issue_id: int, url: str | None = None, token: str | None = None) -> dict[str, Any] | None:
    owner, name = _repo_parts(repo)
    return _client(url, token).add_issue_to_project_column(owner, name, project_id, column_id, issue_id)


def add_card(repo: str, project_id: int, column_id: int, issue_id: int, url: str | None = None, token: str | None = None) -> dict[str, Any] | None:
    """Add an issue/PR card to a project column."""
    return add_issue(repo, project_id, column_id, issue_id, url=url, token=token)


def remove_issue(repo: str, project_id: int, column_id: int, issue_id: int, url: str | None = None, token: str | None = None) -> None:
    owner, name = _repo_parts(repo)
    _client(url, token).remove_issue_from_project_column(owner, name, project_id, column_id, issue_id)


def remove_card(repo: str, project_id: int, column_id: int, issue_id: int, url: str | None = None, token: str | None = None) -> None:
    """Remove an issue/PR card from a project column."""
    remove_issue(repo, project_id, column_id, issue_id, url=url, token=token)


def move_issue(repo: str, project_id: int, issue_id: int, column_id: int, sorting: int | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any] | None:
    owner, name = _repo_parts(repo)
    return _client(url, token).move_project_issue(owner, name, project_id, issue_id, column_id, sorting=sorting)


def move_card(repo: str, project_id: int, issue_id: int, column_id: int, sorting: int | None = None, url: str | None = None, token: str | None = None) -> dict[str, Any] | None:
    """Move an issue/PR card to another project column."""
    return move_issue(repo, project_id, issue_id, column_id, sorting=sorting, url=url, token=token)


@click.group(name="project")
def project_group() -> None:
    """Repository-scoped Gitea project board helpers."""


@project_group.command(name="list")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.option("--state", type=click.Choice(["open", "closed", "all"]), default="open", show_default=True)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def project_list(repo: str | None, state: str, limit: int, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """List repository projects."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project list --repo OWNER/NAME [-i|-I]")
    try:
        payload = list_projects(values["repo"], state=state, limit=limit, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_table(payload, [("id", "id"), ("title", "title"), ("state", "state"), ("open", "num_open_issues"), ("closed", "num_closed_issues")])


@project_group.command(name="view")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def project_view(repo: str | None, project_id: int | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Show a repository project."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project view --repo OWNER/NAME PROJECT_ID [-i|-I]")
    if project_id is None:
        raise click.ClickException("project_id is required")
    try:
        payload = view_project(values["repo"], project_id, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_json_or_project(payload, json_output=json_output)


@project_group.command(name="create")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.option("--title", default=None, help="Project title.")
@click.option("--description", default=None)
@click.option("--card-type", type=click.Choice(["text_only", "images_and_text"]), default=None)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def project_create(repo: str | None, title: str | None, description: str | None, card_type: str | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Create a repository project."""
    values = resolve_command_inputs(schema=PROJECT_CREATE_SCHEMA, provided={"repo": repo, "title": title}, interactive=interactive, usage="Usage: chattea project create --repo OWNER/NAME --title TITLE [-i|-I]")
    try:
        payload = create_project(values["repo"], values["title"], description=description, card_type=card_type, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_json_or_project(payload, json_output=json_output)


@project_group.command(name="edit")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.option("--title", default=None)
@click.option("--description", default=None)
@click.option("--state", type=click.Choice(["open", "closed"]), default=None)
@click.option("--card-type", type=click.Choice(["text_only", "images_and_text"]), default=None)
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def project_edit(repo: str | None, project_id: int | None, title: str | None, description: str | None, state: str | None, card_type: str | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Edit a repository project."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project edit --repo OWNER/NAME PROJECT_ID [-i|-I]")
    if project_id is None:
        raise click.ClickException("project_id is required")
    try:
        payload = edit_project(values["repo"], project_id, title=title, description=description, state=state, card_type=card_type, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_json_or_project(payload, json_output=json_output)


@project_group.command(name="delete")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.option("--yes", is_flag=True, help="Confirm project deletion.")
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None)
@add_interactive_option
def project_delete(repo: str | None, project_id: int | None, yes: bool, url: str | None, token: str | None, interactive: bool | None) -> None:
    """Delete a repository project."""
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project delete --repo OWNER/NAME PROJECT_ID --yes [-i|-I]")
    if project_id is None:
        raise click.ClickException("project_id is required")
    try:
        delete_project(values["repo"], project_id, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"deleted: project {project_id}")


@project_group.group(name="column")
def column_group() -> None:
    """Project column helpers."""


@column_group.command(name="list")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def column_list(repo: str | None, project_id: int | None, limit: int, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """List project columns."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project column list --repo OWNER/NAME PROJECT_ID [-i|-I]")
    if project_id is None:
        raise click.ClickException("project_id is required")
    try:
        payload = list_columns(values["repo"], project_id, limit=limit, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_table(payload, [("id", "id"), ("title", "title"), ("sorting", "sorting"), ("color", "color"), ("issues", "num_issues")])


@column_group.command(name="create")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.option("--title", default=None, help="Column title.")
@click.option("--color", default=None, help="Column color, e.g. #FF0000.")
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def column_create(repo: str | None, project_id: int | None, title: str | None, color: str | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Create a project column."""
    values = resolve_command_inputs(schema=COLUMN_CREATE_SCHEMA, provided={"repo": repo, "title": title}, interactive=interactive, usage="Usage: chattea project column create --repo OWNER/NAME PROJECT_ID --title TITLE [-i|-I]")
    if project_id is None:
        raise click.ClickException("project_id is required")
    try:
        payload = create_column(values["repo"], project_id, values["title"], color=color, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_json_or_project(payload, json_output=json_output, fallback="column")


@column_group.command(name="edit")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("column_id", type=int, required=False)
@click.option("--title", default=None)
@click.option("--color", default=None, help="Column color, e.g. #FF0000.")
@click.option("--sorting", type=int, default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def column_edit(repo: str | None, project_id: int | None, column_id: int | None, title: str | None, color: str | None, sorting: int | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Edit a project column."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project column edit --repo OWNER/NAME PROJECT_ID COLUMN_ID [-i|-I]")
    if project_id is None or column_id is None:
        raise click.ClickException("project_id and column_id are required")
    try:
        payload = edit_column(values["repo"], project_id, column_id, title=title, color=color, sorting=sorting, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    _echo_json_or_project(payload, json_output=json_output, fallback="column")


@column_group.command(name="delete")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("column_id", type=int, required=False)
@click.option("--yes", is_flag=True, help="Confirm column deletion.")
@click.option("--url", default=None)
@click.option("--token", default=None)
@add_interactive_option
def column_delete(repo: str | None, project_id: int | None, column_id: int | None, yes: bool, url: str | None, token: str | None, interactive: bool | None) -> None:
    """Delete a project column."""
    if not yes:
        raise click.ClickException("Refusing to delete without --yes.")
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project column delete --repo OWNER/NAME PROJECT_ID COLUMN_ID --yes [-i|-I]")
    if project_id is None or column_id is None:
        raise click.ClickException("project_id and column_id are required")
    try:
        delete_column(values["repo"], project_id, column_id, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"deleted: column {column_id}")


@project_group.group(name="card")
def card_group() -> None:
    """Project issue/PR card helpers."""


@card_group.command(name="list")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("column_id", type=int, required=False)
@click.option("--limit", default=50, show_default=True)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def issue_list(repo: str | None, project_id: int | None, column_id: int | None, limit: int, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """List issue/PR cards in a project column."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project issue list --repo OWNER/NAME PROJECT_ID COLUMN_ID [-i|-I]")
    if project_id is None or column_id is None:
        raise click.ClickException("project_id and column_id are required")
    try:
        payload = list_column_issues(values["repo"], project_id, column_id, limit=limit, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_table(payload, [("id", "id"), ("number", "number"), ("title", "title"), ("state", "state")])


@card_group.command(name="add")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("column_id", type=int, required=False)
@click.argument("issue_id", type=int, required=False)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def issue_add(repo: str | None, project_id: int | None, column_id: int | None, issue_id: int | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Add an issue/PR card to a project column."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project issue add --repo OWNER/NAME PROJECT_ID COLUMN_ID ISSUE_ID [-i|-I]")
    if project_id is None or column_id is None or issue_id is None:
        raise click.ClickException("project_id, column_id and issue_id are required")
    try:
        payload = add_issue(values["repo"], project_id, column_id, issue_id, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"added: issue {issue_id} to column {column_id}")


@card_group.command(name="remove")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("column_id", type=int, required=False)
@click.argument("issue_id", type=int, required=False)
@click.option("--yes", is_flag=True, help="Confirm removing the issue/PR card from the column.")
@click.option("--url", default=None)
@click.option("--token", default=None)
@add_interactive_option
def issue_remove(repo: str | None, project_id: int | None, column_id: int | None, issue_id: int | None, yes: bool, url: str | None, token: str | None, interactive: bool | None) -> None:
    """Remove an issue/PR card from a project column."""
    if not yes:
        raise click.ClickException("Refusing to remove without --yes.")
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project issue remove --repo OWNER/NAME PROJECT_ID COLUMN_ID ISSUE_ID --yes [-i|-I]")
    if project_id is None or column_id is None or issue_id is None:
        raise click.ClickException("project_id, column_id and issue_id are required")
    try:
        remove_issue(values["repo"], project_id, column_id, issue_id, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"removed: issue {issue_id} from column {column_id}")


@card_group.command(name="move")
@click.option("--repo", default=None, help="Repository in owner/name form.")
@click.argument("project_id", type=int, required=False)
@click.argument("issue_id", type=int, required=False)
@click.option("--column", "column_id", type=int, default=None, help="Target column ID.")
@click.option("--sorting", type=int, default=None)
@click.option("--url", default=None)
@click.option("--token", default=None)
@click.option("--json-output", is_flag=True)
@add_interactive_option
def issue_move(repo: str | None, project_id: int | None, issue_id: int | None, column_id: int | None, sorting: int | None, url: str | None, token: str | None, json_output: bool, interactive: bool | None) -> None:
    """Move an issue/PR card to another project column."""
    values = resolve_command_inputs(schema=PROJECT_REPO_SCHEMA, provided={"repo": repo}, interactive=interactive, usage="Usage: chattea project issue move --repo OWNER/NAME PROJECT_ID ISSUE_ID --column COLUMN_ID [-i|-I]")
    if project_id is None or issue_id is None or column_id is None:
        raise click.ClickException("project_id, issue_id and --column are required")
    try:
        payload = move_issue(values["repo"], project_id, issue_id, column_id, sorting=sorting, url=url, token=token)
    except GiteaAPIError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"moved: issue {issue_id} to column {column_id}")


project_group.add_command(card_group, name="issue")

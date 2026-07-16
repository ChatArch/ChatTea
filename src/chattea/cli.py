"""CLI entrypoint for chattea."""

from __future__ import annotations

import click
from chatstyle import add_interactive_option

from chattea import __version__
from chattea.commands.api import api_command
from chattea.commands.artifact import artifact_group
from chattea.commands.auth import auth_group, render_token_config, resolve_login_values
from chattea.commands.bot import bot_group
from chattea.commands.issue import issue_group
from chattea.commands.job import job_group
from chattea.commands.label import label_group
from chattea.commands.milestone import milestone_group
from chattea.commands.pr import pr_group
from chattea.commands.project import project_group
from chattea.commands.release import release_group
from chattea.commands.repo import repo_group
from chattea.commands.runner import runner_group
from chattea.commands.run import run_group
from chattea.commands.server import server_group
from chattea.commands.token import token_group


@click.group()
@click.version_option(__version__, prog_name="chattea")
def main() -> None:
    """chattea command line interface."""


@main.command(name="set-token")
@click.option("--base-url", "base_url", default=None, help="Gitea website/API base URL.")
@click.option("--url", "legacy_url", default=None, help="Deprecated alias for --base-url.")
@click.option("--token", default=None, help="Gitea API token.")
@add_interactive_option
def set_token(base_url: str | None, legacy_url: str | None, token: str | None, interactive: bool | None) -> None:
    """Configure Gitea API and repo-local git credentials."""
    values = resolve_login_values(base_url, legacy_url, token, interactive)
    for line in render_token_config(values["base_url"], values["token"]):
        click.echo(line)


main.add_command(server_group)
main.add_command(repo_group)
main.add_command(issue_group)
main.add_command(label_group)
main.add_command(milestone_group)
main.add_command(pr_group)
main.add_command(release_group)
main.add_command(runner_group)
main.add_command(run_group)
main.add_command(job_group)
main.add_command(artifact_group)
main.add_command(project_group)
main.add_command(auth_group)
main.add_command(token_group)
main.add_command(bot_group)
main.add_command(api_command)


if __name__ == "__main__":
    main()

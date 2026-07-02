"""CLI entrypoint for chattea."""

from __future__ import annotations

import click
from chatstyle import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    resolve_command_inputs,
)

from chattea import __version__
from chattea.commands.repo import repo_group
from chattea.commands.server import server_group
from chattea.config import DEFAULT_BASE_URL, mask_token, set_token as save_token

TOKEN_SCHEMA = CommandSchema(
    name="set-token",
    fields=(
        CommandField("base_url", prompt="Gitea base URL", required=True, default=DEFAULT_BASE_URL, prompt_if_missing=True),
        CommandField("token", prompt="Gitea API token", required=True, sensitive=True),
    ),
)


def configure_token(base_url: str, token: str):
    """Store the default Gitea base URL and API token in ChatEnv."""
    return save_token(base_url, token)


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
    """Configure the default Gitea base URL and API token."""
    provided_base_url = base_url or legacy_url
    if interactive is not True and not provided_base_url:
        provided_base_url = DEFAULT_BASE_URL
    values = resolve_command_inputs(
        schema=TOKEN_SCHEMA,
        provided={"base_url": provided_base_url, "token": token},
        interactive=interactive,
        usage="Usage: chattea set-token --base-url URL --token TOKEN [-i|-I]",
    )
    path = configure_token(values["base_url"], values["token"])
    click.echo(f"configured: {values['base_url'].rstrip('/')}")
    click.echo(f"token: {mask_token(values['token'])}")
    click.echo(f"config: {path}")


main.add_command(server_group)
main.add_command(repo_group)


if __name__ == "__main__":
    main()

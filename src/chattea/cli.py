"""CLI entrypoint for chattea."""

from __future__ import annotations

import click
from chatstyle import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    render_success,
    resolve_command_inputs,
)

from chattea import __version__
from chattea.commands.repo import repo_group
from chattea.commands.server import server_group
from chattea.config import mask_token, set_token as save_token


HELLO_SCHEMA = CommandSchema(
    name="hello",
    fields=(CommandField("name", prompt="name", required=True),),
)

TOKEN_SCHEMA = CommandSchema(
    name="set-token",
    fields=(
        CommandField("url", prompt="Gitea base URL", required=True),
        CommandField("token", prompt="Gitea API token", required=True),
    ),
)


@click.group()
@click.version_option(__version__, prog_name="chattea")
def main() -> None:
    """chattea command line interface."""


@main.command()
@click.argument("name", required=False)
@add_interactive_option
def hello(name: str | None, interactive: bool | None) -> None:
    """Print a greeting with ChatStyle-backed input resolution."""

    values = resolve_command_inputs(
        schema=HELLO_SCHEMA,
        provided={"name": name},
        interactive=interactive,
        usage="Usage: chattea hello [NAME]",
    )
    render_success(f"Hello, {values['name']}!")


@main.command(name="set-token")
@click.option("--url", default="http://127.0.0.1:3000", show_default=True, help="Gitea base URL.")
@click.option("--token", default=None, help="Gitea API token.")
@add_interactive_option
def set_token(url: str, token: str | None, interactive: bool | None) -> None:
    """Configure the default Gitea URL and API token."""
    values = resolve_command_inputs(
        schema=TOKEN_SCHEMA,
        provided={"url": url, "token": token},
        interactive=interactive,
        usage="Usage: chattea set-token --url URL --token TOKEN [-i|-I]",
    )
    path = save_token(values["url"], values["token"])
    click.echo(f"configured: {values['url'].rstrip('/')}")
    click.echo(f"token: {mask_token(values['token'])}")
    click.echo(f"config: {path}")


main.add_command(server_group)
main.add_command(repo_group)


if __name__ == "__main__":
    main()

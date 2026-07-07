from __future__ import annotations

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs

from chattea.config import DEFAULT_BASE_URL, load_config, mask_token
from chattea.credentials import configure_token as configure_credentials

TOKEN_SCHEMA = CommandSchema(
    name="auth login",
    fields=(
        CommandField("base_url", prompt="Gitea base URL", required=True, default=DEFAULT_BASE_URL, prompt_if_missing=True),
        CommandField("token", prompt="Gitea API token", required=True, sensitive=True),
    ),
)


def configure_token(base_url: str, token: str, *, repo: str | None = None) -> dict[str, object]:
    """Configure ChatTea API and git transport credentials."""
    return configure_credentials(base_url, token, repo=repo)


def render_token_config(base_url: str, token: str) -> list[str]:
    """Return non-sensitive status lines for a token configuration update."""
    result = configure_token(base_url, token)
    lines = [f"configured: {str(result['base_url']).rstrip('/')}", f"token: {mask_token(token)}"]
    if result.get("env_path"):
        lines.append(f"config: {result['env_path']}")
    if result.get("git_key"):
        lines.append(f"git_config: {result['git_key']}")
    else:
        lines.append("git_config: not configured (run inside a Gitea git repository to configure repo-local git auth)")
    return lines


def resolve_login_values(base_url: str | None, legacy_url: str | None, token: str | None, interactive: bool | None) -> dict[str, str]:
    """Resolve login inputs consistently for auth login and set-token."""
    provided_base_url = base_url or legacy_url
    if interactive is not True and not provided_base_url:
        provided_base_url = DEFAULT_BASE_URL
    return resolve_command_inputs(
        schema=TOKEN_SCHEMA,
        provided={"base_url": provided_base_url, "token": token},
        interactive=interactive,
        usage="Usage: chattea auth login --base-url URL --token TOKEN [-i|-I]",
    )


@click.group(name="auth")
def auth_group() -> None:
    """Configure and inspect ChatTea authentication."""


@auth_group.command(name="login")
@click.option("--base-url", "base_url", default=None, help="Gitea website/API base URL.")
@click.option("--url", "legacy_url", default=None, help="Deprecated alias for --base-url.")
@click.option("--token", default=None, help="Gitea API token.")
@add_interactive_option
def auth_login(base_url: str | None, legacy_url: str | None, token: str | None, interactive: bool | None) -> None:
    """Configure Gitea API and repo-local git credentials."""
    values = resolve_login_values(base_url, legacy_url, token, interactive)
    for line in render_token_config(values["base_url"], values["token"]):
        click.echo(line)


@auth_group.command(name="status")
def auth_status() -> None:
    """Show the configured Gitea base URL and whether a token exists."""
    config = load_config()
    click.echo(f"base_url: {config.url.rstrip('/')}")
    click.echo(f"token: {mask_token(config.token) if config.token else '<not configured>'}")


@auth_group.command(name="token")
def auth_token() -> None:
    """Show the masked configured token for quick verification."""
    config = load_config()
    click.echo(mask_token(config.token) if config.token else "<not configured>")

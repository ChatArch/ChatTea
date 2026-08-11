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
from chattea.commands.notification import notification_group
from chattea.commands.org import org_group
from chattea.commands.pr import pr_group
from chattea.commands.project import project_group
from chattea.commands.release import release_group
from chattea.commands.repo import repo_group
from chattea.commands.runner import runner_group
from chattea.commands.run import run_group
from chattea.commands.server import server_group
from chattea.commands.token import token_group
from chattea.commands.user import user_group


def _format_metavar(name: str) -> str:
    return name.replace("_", "-").upper()


def _format_argument(param: click.Argument) -> str:
    metavar = _format_metavar(param.name or "arg")
    if param.nargs == -1:
        value = f"<{metavar}>..."
    else:
        value = f"<{metavar}>"
    if not param.required:
        return f"[{value}]"
    return value


def _format_option(param: click.Option) -> str:
    primary = next((opt for opt in param.opts if opt.startswith("--")), param.opts[0] if param.opts else param.name)
    if param.secondary_opts:
        secondary = next((opt for opt in param.secondary_opts if opt.startswith("--")), param.secondary_opts[0])
        return f"[{primary}/{secondary}]"
    if param.is_flag or param.flag_value is not None:
        return f"[{primary}]"
    metavar = param.metavar or _format_metavar(param.name or "value")
    return f"[{primary} <{metavar}>]"


def _format_command_signature(command: click.Command) -> str:
    arguments: list[str] = []
    options: list[str] = []
    for param in command.params:
        if getattr(param, "hidden", False):
            continue
        if isinstance(param, click.Argument):
            arguments.append(_format_argument(param))
        elif isinstance(param, click.Option):
            options.append(_format_option(param))
    return " ".join(arguments + options)


def _command_purpose(command: click.Command) -> str:
    text = command.short_help or command.help or ""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "No description.")
    return first_line.rstrip(".") + "."


def _visible_children(command: click.Command) -> list[tuple[str, click.Command]]:
    children = getattr(command, "commands", {})
    return [(name, child) for name, child in children.items() if not getattr(child, "hidden", False)]


def render_cli_tree(command: click.Command, root_name: str = "chattea") -> str:
    """Render the registered Click command tree."""

    lines = [f"{root_name}  # {_command_purpose(command)}"]
    synthetic = [
        ("--help", "Show this help message."),
        ("--version", "Show the installed package version."),
        ("--tree", "Print the registered command tree."),
    ]
    nodes: list[tuple[str, str | click.Command]] = [(name, purpose) for name, purpose in synthetic]
    nodes.extend((name, child) for name, child in _visible_children(command))

    def walk(items: list[tuple[str, str | click.Command]] | list[tuple[str, click.Command]], prefix: str = "") -> None:
        for index, (name, value) in enumerate(items):
            is_last = index == len(items) - 1
            branch = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")
            if isinstance(value, str):
                lines.append(f"{prefix}{branch}{name}  # {value}")
                continue
            signature = _format_command_signature(value)
            label = f"{name} {signature}".strip()
            lines.append(f"{prefix}{branch}{label}  # {_command_purpose(value)}")
            children = _visible_children(value)
            if children:
                walk(children, child_prefix)

    walk(nodes)
    return "\n".join(lines)


def _print_tree(ctx: click.Context, _param: click.Option, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(render_cli_tree(ctx.command))
    ctx.exit()


@click.group(name="chattea", context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="chattea")
@click.option("--tree", is_flag=True, is_eager=True, expose_value=False, callback=_print_tree, help="Print the registered command tree.")
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
main.add_command(user_group)
main.add_command(org_group)
main.add_command(notification_group)
main.add_command(bot_group)
main.add_command(api_command)


if __name__ == "__main__":
    main()

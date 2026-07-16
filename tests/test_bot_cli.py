from pathlib import Path
import json
import subprocess

from click.testing import CliRunner

from chattea.cli import main
from chattea.commands import bot as bot_commands
from chattea.commands.bot import create_bot_token_local, create_bot_user_local, delete_bot_user_local, extract_created_token


class DummyCompleted:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.stderr = ""


def test_extract_created_token_from_create_output():
    output = "New user 'release-bot' has been successfully created!\nAccess token was successfully created... abcdef1234567890\n"
    assert extract_created_token(output) == "abcdef1234567890"


def test_create_bot_user_local_builds_admin_cli(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, check, capture_output, text):
        calls.append(command)
        return DummyCompleted("New user 'release-bot' has been successfully created!\nAccess token was successfully created... tok_1234567890\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    payload = create_bot_user_local(
        "release-bot",
        "release-bot@example.invalid",
        restricted=True,
        token_name="release-token",
        scopes=["write:repository", "write:issue"],
        binary=tmp_path / "gitea",
        config_path=tmp_path / "app.ini",
        work_path=tmp_path / "work",
    )

    command = calls[0]
    assert command[:6] == [str(tmp_path / "gitea"), "--config", str(tmp_path / "app.ini"), "--work-path", str(tmp_path / "work"), "admin"]
    assert command[6:] == [
        "user",
        "create",
        "--username",
        "release-bot",
        "--email",
        "release-bot@example.invalid",
        "--user-type",
        "bot",
        "--restricted",
        "--access-token",
        "--access-token-name",
        "release-token",
        "--access-token-scopes",
        "write:repository,write:issue",
    ]
    assert payload["token"] == "tok_1234567890"


def test_create_bot_token_local_uses_generate_access_token(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, check, capture_output, text):
        calls.append(command)
        return DummyCompleted("tok_abcdef")

    monkeypatch.setattr(subprocess, "run", fake_run)
    payload = create_bot_token_local(
        "release-bot",
        token_name="release-token",
        scopes=["write:repository"],
        binary=tmp_path / "gitea",
        config_path=tmp_path / "app.ini",
        work_path=tmp_path / "work",
    )

    assert calls[0][6:] == [
        "user",
        "generate-access-token",
        "--username",
        "release-bot",
        "--token-name",
        "release-token",
        "--scopes",
        "write:repository",
        "--raw",
    ]
    assert payload["token"] == "tok_abcdef"


def test_delete_bot_user_local_builds_delete_command(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, check, capture_output, text):
        calls.append(command)
        return DummyCompleted("")

    monkeypatch.setattr(subprocess, "run", fake_run)
    payload = delete_bot_user_local(
        "release-bot",
        purge=True,
        binary=tmp_path / "gitea",
        config_path=tmp_path / "app.ini",
        work_path=tmp_path / "work",
    )

    assert calls[0][6:] == ["user", "delete", "--username", "release-bot", "--purge"]
    assert payload == {"username": "release-bot", "deleted": True, "purge": True}


def test_bot_subcommands_are_registered():
    runner = CliRunner()
    for args in [["bot", "--help"], ["bot", "plan", "--help"], ["bot", "create", "--help"], ["bot", "token", "--help"], ["bot", "token", "create", "--help"]]:
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output


def test_bot_create_cli_masks_token(monkeypatch):
    def fake_create(*args, **kwargs):
        return {"username": "release-bot", "email": "release@example.invalid", "restricted": True, "token_name": "release-token", "token": "tok_1234567890"}

    monkeypatch.setattr(bot_commands, "create_bot_user_local", fake_create)
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["bot", "create", "--username", "release-bot", "--email", "release@example.invalid", "--token-name", "release-token", "--json-output"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["token"] != "tok_1234567890"
    assert payload["token"].startswith("tok_")


def test_bot_token_create_cli_show_token(monkeypatch):
    def fake_create(*args, **kwargs):
        return {"username": "release-bot", "token_name": "release-token", "scopes": ["all"], "token": "tok_1234567890"}

    monkeypatch.setattr(bot_commands, "create_bot_token_local", fake_create)
    runner = CliRunner()
    result = runner.invoke(main, ["bot", "token", "create", "release-bot", "--token-name", "release-token", "--show-token-once", "--json-output"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["token"] == "tok_1234567890"

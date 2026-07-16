from pathlib import Path
import json

from click.testing import CliRunner

from chattea.cli import main
from chattea.commands.runner import (
    create_local_runner,
    labels_for_register,
    parse_workflow_runs_on,
    read_runner_config_summary,
    runner_service_name,
)


def test_runner_labels_default_to_backend_suffix():
    assert labels_for_register("lean-native", backend="host") == "lean-native:host"
    assert labels_for_register("lean-native:host", backend="docker") == "lean-native:host"
    assert labels_for_register("lean-a,lean-b", backend="host") == "lean-a:host,lean-b:host"


def test_create_local_runner_writes_host_config(tmp_path):
    root = tmp_path / "runner-a"
    payload = create_local_runner("runner-a", root=root, labels="lean-native", backend="host", capacity=2)

    assert payload["name"] == "runner-a"
    assert payload["service"] == "chattea-runner@runner-a.service"
    summary = read_runner_config_summary(root)
    assert summary["capacity"] == 2
    assert summary["labels"] == ["lean-native:host"]
    assert summary["backend"] == "host"
    assert summary["workdir"] == str(root / "work")


def test_runner_service_name_keeps_default_compatibility():
    assert runner_service_name() == "chattea-runner.service"
    assert runner_service_name("lean-a") == "chattea-runner@lean-a.service"


def test_runner_local_create_cli_outputs_json(tmp_path):
    runner = CliRunner()
    root = tmp_path / "runner-b"
    result = runner.invoke(
        main,
        [
            "runner",
            "local",
            "create",
            "runner-b",
            "--root",
            str(root),
            "--label",
            "lean-b",
            "--backend",
            "host",
            "--capacity",
            "1",
            "--json-output",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["name"] == "runner-b"
    assert payload["labels"] == ["lean-b:host"]
    assert Path(payload["config"]).exists()


def test_runner_subgroups_are_registered():
    runner = CliRunner()
    for args in [
        ["runner", "registry", "--help"],
        ["runner", "local", "--help"],
        ["runner", "local", "config", "--help"],
        ["runner", "pool", "--help"],
        ["runner", "workflow", "--help"],
        ["runner", "setup", "--help"],
    ]:
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output


def test_parse_workflow_runs_on_values(tmp_path):
    workflow = tmp_path / "flow.yml"
    workflow.write_text(
        """
name: practice
jobs:
  a:
    runs-on: lean-a
  b:
    runs-on: [lean-b, extra]
""".strip(),
        encoding="utf-8",
    )

    assert parse_workflow_runs_on(workflow) == ["lean-a", "lean-b", "extra"]

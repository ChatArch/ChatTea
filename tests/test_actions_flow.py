from chattea.api import GiteaClient
from chattea.commands.runner import create_runner_token, list_registered_runners
from chattea.commands.run import list_runs, view_run
from click.testing import CliRunner
from chattea.cli import main


def test_actions_api_methods_use_gitea_routes(monkeypatch):
    calls = []
    client = GiteaClient(url="http://gitea.local", token="token")

    def fake_request(method, path, data=None, params=None, extra_headers=None):
        calls.append((method, path, data, params))
        return {"method": method, "path": path}

    def fake_request_raw(method, path, data=None, params=None, extra_headers=None, accept="application/json"):
        calls.append((method, path, data, params, accept))
        return b"zip"

    monkeypatch.setattr(client, "request", fake_request)
    monkeypatch.setattr(client, "request_raw", fake_request_raw)

    client.list_action_runs("owner", "repo", limit=10)
    client.get_action_run("owner", "repo", 1)
    client.rerun_action_run("owner", "repo", 1)
    client.rerun_failed_action_run("owner", "repo", 1)
    client.delete_action_run("owner", "repo", 1)
    client.list_action_run_jobs("owner", "repo", 1)
    client.get_action_job("owner", "repo", 2)
    client.get_action_job_logs("owner", "repo", 2)
    client.rerun_action_job("owner", "repo", 1, 2)
    client.list_action_artifacts("owner", "repo", run_id=1)
    client.list_action_artifacts("owner", "repo")
    client.get_action_artifact("owner", "repo", 3)
    client.download_action_artifact_zip("owner", "repo", 3)
    client.delete_action_artifact("owner", "repo", 3)
    client.create_runner_registration_token("repo", owner="owner", repo="repo")
    client.list_runners("repo", owner="owner", repo="repo")
    client.get_runner(4, "repo", owner="owner", repo="repo")
    client.edit_runner(4, "repo", owner="owner", repo="repo", disabled=True)
    client.delete_runner(4, "repo", owner="owner", repo="repo")

    assert ("GET", "/repos/owner/repo/actions/runs", None, {"limit": 10}) in calls
    assert ("GET", "/repos/owner/repo/actions/runs/1", None, None) in calls
    assert ("POST", "/repos/owner/repo/actions/runs/1/rerun", None, None) in calls
    assert ("POST", "/repos/owner/repo/actions/runs/1/rerun-failed-jobs", None, None) in calls
    assert ("DELETE", "/repos/owner/repo/actions/runs/1", None, None) in calls
    assert ("GET", "/repos/owner/repo/actions/runs/1/jobs", None, {"limit": 50}) in calls
    assert ("GET", "/repos/owner/repo/actions/jobs/2", None, None) in calls
    assert ("GET", "/repos/owner/repo/actions/jobs/2/logs", None, None) in calls
    assert ("POST", "/repos/owner/repo/actions/runs/1/jobs/2/rerun", None, None) in calls
    assert ("GET", "/repos/owner/repo/actions/runs/1/artifacts", None, {"limit": 50}) in calls
    assert ("GET", "/repos/owner/repo/actions/artifacts", None, {"limit": 50}) in calls
    assert ("GET", "/repos/owner/repo/actions/artifacts/3", None, None) in calls
    assert ("GET", "/repos/owner/repo/actions/artifacts/3/zip", None, None, "application/zip") in calls
    assert ("DELETE", "/repos/owner/repo/actions/artifacts/3", None, None) in calls
    assert ("POST", "/repos/owner/repo/actions/runners/registration-token", None, None) in calls
    assert ("GET", "/repos/owner/repo/actions/runners", None, {"limit": 50}) in calls
    assert ("GET", "/repos/owner/repo/actions/runners/4", None, None) in calls
    assert ("PATCH", "/repos/owner/repo/actions/runners/4", {"disabled": True}, None) in calls
    assert ("DELETE", "/repos/owner/repo/actions/runners/4", None, None) in calls


def test_actions_cli_groups_are_registered():
    runner = CliRunner()
    for command in ["runner", "run", "job", "artifact"]:
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0, result.output


def test_actions_command_functions_call_client(monkeypatch):
    calls = []

    class FakeClient:
        def list_action_runs(self, owner, repo, status=None, limit=50, page=None):
            calls.append(("runs", owner, repo, status, limit, page))
            return []

        def get_action_run(self, owner, repo, run_id):
            calls.append(("run", owner, repo, run_id))
            return {"id": run_id}

        def create_runner_registration_token(self, scope, owner=None, repo=None, org=None):
            calls.append(("runner-token", scope, owner, repo, org))
            return {"token": "runner-token"}

        def list_runners(self, scope, owner=None, repo=None, org=None, limit=50, page=None):
            calls.append(("runners", scope, owner, repo, org, limit, page))
            return []

    monkeypatch.setattr("chattea.commands.run.client", lambda: FakeClient())
    monkeypatch.setattr("chattea.commands.runner.client", lambda: FakeClient())

    list_runs("owner/repo", state="success", limit=5)
    view_run("owner/repo", 1)
    create_runner_token("repo", repo="owner/repo")
    list_registered_runners("repo", repo="owner/repo")

    assert calls == [
        ("runs", "owner", "repo", "success", 5, None),
        ("run", "owner", "repo", 1),
        ("runner-token", "repo", "owner", "repo", None),
        ("runners", "repo", "owner", "repo", None, 50, None),
    ]

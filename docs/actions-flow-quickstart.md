# Actions / Flow Quick Start

This page documents the first ChatTea Actions/Flow surface. It focuses on the acceptance loop that matters for day-to-day automation: register a runner, trigger a workflow through a pull request, inspect the run/job, and read logs.

## CLI Surface

```text
chattea runner
├── token
├── list
├── view
├── edit
├── delete
└── setup
    ├── install
    ├── register
    ├── start
    ├── stop
    ├── status
    ├── logs
    └── doctor

chattea run
├── list
├── view
├── jobs
├── logs
├── rerun
├── rerun-failed
└── delete

chattea job
├── view
├── logs
└── rerun

chattea artifact
├── list
├── view
├── download
└── delete
```

## REST API Mapping

```text
chattea runner token       -> POST /repos/{owner}/{repo}/actions/runners/registration-token
chattea runner list        -> GET /repos/{owner}/{repo}/actions/runners
chattea runner view        -> GET /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner edit        -> PATCH /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner delete      -> DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}

chattea run list           -> GET /repos/{owner}/{repo}/actions/runs
chattea run view           -> GET /repos/{owner}/{repo}/actions/runs/{run}
chattea run jobs           -> GET /repos/{owner}/{repo}/actions/runs/{run}/jobs
chattea run logs           -> composed helper over run jobs + job logs
chattea run rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun
chattea run rerun-failed   -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun-failed-jobs
chattea run delete         -> DELETE /repos/{owner}/{repo}/actions/runs/{run}

chattea job view           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}
chattea job logs           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs
chattea job rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job_id}/rerun

chattea artifact list      -> GET /repos/{owner}/{repo}/actions/artifacts
chattea artifact download  -> GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip
chattea artifact delete    -> DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}
```

`runner setup` commands are local system helpers. They install or locate `gitea-runner`, write local runner config under the ChatTea runtime directory, register the runner with a Gitea registration token, and manage the user systemd service.

## Runner Setup

Enable Actions on a ChatTea-managed development server before running workflows:

```bash
chattea server config set --section actions --key ENABLED --value true -I
chattea server restart
chattea server health
```

Install and register a repository-scoped runner:

```bash
chattea runner setup install --force
chattea runner setup register --scope repo --repo gitea_admin/demo --name chattea-runner-demo --labels ubuntu-latest:host
chattea runner setup start
chattea runner list --scope repo --repo gitea_admin/demo
```

The default runner runtime is derived from `CHATTEA_HOME` and stays under lowercase ChatTea runtime paths:

```text
~/.chatarch/chattea/runner/bin/gitea-runner
~/.chatarch/chattea/runner/config/config.yaml
~/.chatarch/chattea/runner/work
```

The default label uses the host backend:

```text
ubuntu-latest:host
```

This avoids requiring Docker for the first development smoke.

## PR Trigger Smoke

A minimal workflow can live in `.gitea/workflows/pr-smoke.yml`:

```yaml
name: ChatTea PR Smoke
on:
  pull_request:
  push:
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - name: Print context
        run: |
          echo "chattea actions smoke"
          echo "event=$GITHUB_EVENT_NAME"
          echo "repo=$GITHUB_REPOSITORY"
      - name: Verify shell
        run: |
          pwd
          echo "ok" > smoke-result.txt
          cat smoke-result.txt
```

After pushing a feature branch and opening a PR, inspect the run:

```bash
chattea run list --repo gitea_admin/demo
chattea run view --repo gitea_admin/demo 6
chattea run jobs --repo gitea_admin/demo 6
chattea job logs --repo gitea_admin/demo 6
```

## Verified Local Smoke

On the development server, a real smoke verified:

```text
repo: gitea_admin/actions-pr-smoke-20260708025144
runner: chattea-runner-actions-pr-smoke-20260708025144
pull_request run: 6
job: 6
result: success
log marker: chattea actions smoke
```

One practical note: creating a PR immediately after pushing a new branch can race with branch visibility. A short retry before PR creation makes the same `head=feature/pr-smoke` payload succeed.

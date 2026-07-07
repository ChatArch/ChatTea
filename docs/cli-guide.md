# ChatTea CLI Guide

This guide is the practical CLI map for the current ChatTea Gitea surface. It covers the implemented command tree, the REST API or local helper behind each major group, and real examples from a local ChatTea-managed Gitea server.

## Current CLI Tree

```text
chattea
├── set-token                 # ChatTea/Git token bootstrap helper
├── server                    # local ChatArch Gitea lifecycle
│   ├── config                # app.ini path/show/get/set helpers
│   ├── install               # install ChatArch internal Gitea binary
│   ├── init                  # initialize managed Gitea app.ini/work path
│   ├── bootstrap             # install + init + admin + token bootstrap
│   ├── serve                 # foreground web process
│   ├── start/stop/restart    # user systemd service lifecycle
│   ├── status/logs           # user systemd inspection
│   ├── version               # local Gitea binary version
│   └── health                # REST: GET /api/v1/version
├── repo                      # repository REST API + git clone helper
│   ├── list/view/create
│   ├── clone                 # local git helper
│   └── migrate
├── issue                     # REST: /repos/{owner}/{repo}/issues
│   ├── list/view/create/edit/close/reopen/delete
│   ├── comment list/create/edit/delete
│   ├── label add/remove
│   └── assign add/remove
├── label                     # REST: /repos/{owner}/{repo}/labels
│   └── list/view/create/edit/delete
├── milestone                 # REST: /repos/{owner}/{repo}/milestones
│   └── list/view/create/edit/close/delete
├── pr                        # REST: /repos/{owner}/{repo}/pulls
│   ├── list/view/create/edit/close/reopen/merge
│   ├── diff/patch/commits/files
│   ├── comment list/create
│   └── review list/create/submit
├── release                   # REST: /repos/{owner}/{repo}/releases
│   ├── list/view/latest/by-tag/create/edit/delete
│   └── asset list/delete
├── project                   # Gitea repository-scoped Project board
│   ├── list/view/create/edit/delete
│   ├── column list/create/edit/delete
│   ├── card list/add/remove/move
│   └── issue list/add/remove/move   # compatibility alias for card
├── runner                    # Gitea Actions runner API + local setup
│   ├── token/list/view/edit/delete  # REST: /actions/runners
│   └── setup install/register/start/stop/status/logs/doctor
├── run                       # REST: /repos/{owner}/{repo}/actions/runs
│   └── list/view/jobs/logs/rerun/rerun-failed/delete
├── job                       # REST: /repos/{owner}/{repo}/actions/jobs
│   └── view/logs/rerun
├── artifact                  # REST: /repos/{owner}/{repo}/actions/artifacts
│   └── list/view/download/delete
├── auth                      # auth/login/status/token convenience surface
├── token                     # Gitea access token create/list/delete/bootstrap
└── api                       # raw Gitea API passthrough
```

## Implementation Contract

ChatTea commands are thin Click wrappers. Each substantial command calls an importable Python function or a `GiteaClient` method.

Examples:

```python
from chattea.api import GiteaClient
from chattea.commands.repo import create_repository
from chattea.commands.issue import create_issue
from chattea.commands.project import add_card
from chattea.commands.runner import register_runner
from chattea.commands.run import list_runs
from chattea.commands.job import job_logs

client = GiteaClient()
repo = create_repository(name="demo", owner="gitea_admin")
issue = create_issue("gitea_admin/demo", title="Document CLI")
add_card("gitea_admin/demo", project_id=1, column_id=1, issue_id=issue["id"])
register_runner(scope="repo", repo="gitea_admin/demo", name="chattea-runner-demo")
runs = list_runs("gitea_admin/demo")
logs = job_logs("gitea_admin/demo", job_id=6)
```

## Server And Token Flow

A local development server starts from ChatEnv and Gitea server lifecycle commands:

```bash
chattea server bootstrap -I
chattea server health
chattea token bootstrap --username gitea_admin --password-env GITEA_ADMIN_PASSWORD --scope all
```

When Actions are needed, enable them in Gitea `app.ini` and restart the managed service:

```bash
chattea server config set --section actions --key ENABLED --value true -I
chattea server restart
chattea server health
```

`server config set` edits `app.ini`; this is runtime configuration and requires restart to be reliable. By contrast, issue/PR/project/run/job/runner REST API commands operate against live Gitea state and do not require restarting Gitea.

## Repo, Issue, And Project Example

The following flow was run against a local ChatTea-managed Gitea server. It creates a repo, adds issue metadata, creates a repository-scoped Project board, then adds an issue as a Project card.

Gitea Web issue page:

![Gitea issue page](assets/cli-guide/gitea-issue-page.png)

Gitea Web Project board page:

![Gitea Project board](assets/cli-guide/gitea-project-board.png)

CLI transcript for the same flow:

![Repo, Issue, and Project board CLI flow](assets/cli-guide/repo-issue-project.svg)

Important Gitea Project detail: `project card add` maps to Gitea's Project card API and expects the issue database `id`, not the issue number shown as `#1`. Use `chattea issue view --repo OWNER/REPO 1` and read the `id` field.

Core route mapping:

```text
chattea issue create       -> POST /repos/{owner}/{repo}/issues
chattea issue view         -> GET /repos/{owner}/{repo}/issues/{index}
chattea project create     -> POST /repos/{owner}/{repo}/projects
chattea project column     -> /repos/{owner}/{repo}/projects/{project_id}/columns
chattea project card add   -> POST /repos/{owner}/{repo}/projects/{project_id}/columns/{column_id}/issues/{issue_id}
```

## Pull Request Example

A PR is a repository REST API operation. The screenshot below is the Gitea Web pull request page created by `chattea pr create`.

![Gitea pull request page](assets/cli-guide/gitea-pull-request.png)

CLI commands:

```bash
chattea pr create \
  --repo gitea_admin/demo \
  --title "Trigger Actions smoke" \
  --head feature/pr-smoke \
  --base main \
  --body "Created by ChatTea smoke"

chattea pr list --repo gitea_admin/demo --state all
chattea pr view --repo gitea_admin/demo 1
chattea pr diff --repo gitea_admin/demo 1
chattea pr files --repo gitea_admin/demo 1
```

Route mapping:

```text
chattea pr create      -> POST /repos/{owner}/{repo}/pulls
chattea pr list/view   -> GET /repos/{owner}/{repo}/pulls
chattea pr diff/patch  -> GET /repos/{owner}/{repo}/pulls/{index}.diff/.patch
chattea pr merge       -> POST /repos/{owner}/{repo}/pulls/{index}/merge
```

Practical note: immediately creating a PR after pushing a new branch can race with Gitea branch visibility. Retry the same `head=feature/pr-smoke` payload after a short delay if Gitea returns `404` right after push.

## Runner And Actions Flow

Runner support has two layers:

1. Gitea REST API layer:
   - registration token
   - runner list/view/edit/delete
   - repo/org/user/admin scopes
2. Local setup layer:
   - install `gitea-runner`
   - write runner config
   - register runner with a Gitea token
   - manage `chattea-runner.service`

The first implementation defaults to a host runner label:

```text
ubuntu-latest:host
```

This keeps the development smoke independent of Docker image pulls.

The Actions run and job pages below show the workflow that was picked up by the registered runner and completed successfully.

![Gitea Actions run page](assets/cli-guide/gitea-actions-run.png)

![Gitea Actions job log page](assets/cli-guide/gitea-actions-job-log.png)

CLI transcript for runner setup and maintenance:

![Runner setup and maintenance CLI flow](assets/cli-guide/runner-lifecycle.svg)

Route and helper mapping:

```text
chattea runner token       -> POST /repos/{owner}/{repo}/actions/runners/registration-token
chattea runner list        -> GET /repos/{owner}/{repo}/actions/runners
chattea runner edit        -> PATCH /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner delete      -> DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner setup *     -> local helper around ~/.chatarch/chattea/runner and user systemd
```

`runner edit` uses Gitea's `disabled` field. The CLI exposes it as `--disabled` and `--enabled`.

## Run, Job, And Log Example

After a PR triggers a workflow, the operational surface is `run` and `job`. The Gitea run and job pages are shown in the Runner section above; the CLI transcript below shows the same state through ChatTea commands.

![PR-triggered Actions run, job, and logs CLI transcript](assets/cli-guide/actions-run-job-log.svg)

Route mapping:

```text
chattea run list           -> GET /repos/{owner}/{repo}/actions/runs
chattea run view           -> GET /repos/{owner}/{repo}/actions/runs/{run}
chattea run jobs           -> GET /repos/{owner}/{repo}/actions/runs/{run}/jobs
chattea run logs           -> composed helper over run jobs + job logs
chattea run rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun
chattea run rerun-failed   -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun-failed-jobs
chattea job view           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}
chattea job logs           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs
chattea job rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job_id}/rerun
```

Verified local smoke:

```text
repo: gitea_admin/web-docs-smoke-20260708033919
runner: chattea-runner-web-docs-smoke-20260708033919
pull_request run: 9
job: 9
result: success
log marker: chattea web screenshot smoke
```

## Artifact Commands

Artifacts are available after workflows upload artifacts. The CLI wraps the repo Actions artifact API:

```bash
chattea artifact list --repo gitea_admin/demo
chattea artifact list --repo gitea_admin/demo --run-id 6
chattea artifact view --repo gitea_admin/demo 10
chattea artifact download --repo gitea_admin/demo 10 --output artifact.zip
chattea artifact delete --repo gitea_admin/demo 10
```

Route mapping:

```text
chattea artifact list      -> GET /repos/{owner}/{repo}/actions/artifacts
chattea artifact view      -> GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}
chattea artifact download  -> GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip
chattea artifact delete    -> DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}
```

## What Is Still Intentionally Not First-Class

The following can still be accessed with `chattea api`, but is not part of the first polished CLI surface:

```text
chattea workflow list/view/dispatch/enable/disable
chattea secret list/set/delete
chattea variable list/view/create/edit/delete
```

Workflow definitions live in git as `.gitea/workflows/*.yml` files. For the first end-to-end flow, pushing workflow files plus runner/run/job/log commands gives the best validation signal.

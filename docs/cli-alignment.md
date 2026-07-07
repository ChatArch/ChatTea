# ChatTea CLI Alignment Plan

This document defines ChatTea's evidence-bound CLI direction for ChatArch Gitea.

The goal is not to clone GitHub CLI. ChatTea is a Gitea CLI and local Gitea operator tool. Command names may follow familiar GitHub/Gitea resource concepts when they match Gitea's real API, but every command must be backed by a real Gitea REST route or by an explicitly designed ChatTea local capability.

## Evidence Policy

A command may enter the official CLI tree only when at least one of these is true:

1. A Gitea REST route exists in `core/gitea/routers/api/v1/**` Swagger annotations.
2. The command is a ChatTea local capability with a concrete implementation contract, such as `set-token`, `server`, or `repo clone`.

Do not add placeholder commands. Do not add a command only because GitHub CLI has it. If Gitea does not support the capability, keep it out of the tree until there is a real local design or a real Gitea route.

## Implementation Contract

Every CLI command must be a thin adapter over importable Python code.

For each public command, implementation must include:

1. A reusable Python function or method that can be called without invoking the CLI.
2. A CLI wrapper that only parses options, resolves interactive input, calls the Python function, and renders output.
3. A test for the reusable Python function or API method.
4. A CLI smoke/behavior test for command registration, argument parsing, output, and failure mode.
5. Documentation that maps the command to either a Gitea REST route or a ChatTea local function.

The CLI must not be the only stable integration surface. Python integrations, MCP tools, and future gateway adapters should call Python functions directly instead of shelling out to `chattea ...`.

Preferred shape:

```text
src/chattea/
├── api.py or api/<domain>.py          # Gitea REST client methods; no Click rendering.
├── credentials.py                     # set-token, token resolution, repo-local git credential helpers.
├── server.py                          # local Gitea install/service/config primitives.
└── commands/
    ├── token.py                       # Click command group + thin wrappers around token functions.
    ├── repo.py                        # Click command group + thin wrappers around repo functions.
    ├── issue.py                       # Click command group + thin wrappers around issue functions.
    ├── pr.py                          # Click command group + thin wrappers around pull request functions.
    ├── project.py                     # Click command group + thin wrappers around project/card functions.
    └── ...
```

This layout should follow the CLI tree when practical. It can stay flexible when a shared lower-level class or helper is clearer, but domain logic must remain importable and decoupled from Click.

## Token And Credential Contract

`set-token` is not a simple clone of `auth login` and not just a dotenv writer.

`set-token` is ChatTea's credential foundation:

- Configure token access for the current repository/Gitea remote so git transport can pull and push without repeatedly asking for a token.
- Save or update the ChatTea/ChatEnv token profile when appropriate.
- Provide the token source used by API commands such as `repo`, `issue`, `pr`, `project`, `release`, and Actions commands.
- Keep raw tokens out of normal command output.

Token resolution for API commands is centralized and consistent:

1. Explicit CLI token argument, when provided.
2. Repo-local git credential/config derived from the current Gitea remote, when available.
3. ChatTea ChatEnv profile token.
4. Clean failure if the command requires authentication and no token is available.

Token creation is separate from token configuration:

- `token create` uses Gitea BasicAuth against `POST /users/{username}/tokens` to create an access token.
- `token bootstrap` creates an access token and immediately calls the same credential configuration path as `set-token`.
- `set-token` configures an already-created token for ChatTea and git transport.

## Confirmed Current ChatTea CLI

This is the currently implemented surface on the working branch. It is not the complete target.

```text
chattea
├── set-token                         # `chattea.commands.auth.configure_token` -> ChatEnv + repo-local git extraHeader credential.
├── api                               # Raw Gitea API passthrough via `chattea.commands.api.call_api`.
├── auth                              # Auxiliary status/login namespace; uses the same credential backend as set-token.
│   ├── login                         # Configure Gitea API + repo-local git credentials.
│   ├── status                        # Show configured base URL and masked token state.
│   └── token                         # Show masked configured token.
├── token                             # Gitea access token lifecycle through BasicAuth.
│   ├── create                        # POST /users/{username}/tokens -> `create_access_token`.
│   ├── list                          # GET /users/{username}/tokens -> `list_access_tokens`.
│   ├── delete                        # DELETE /users/{username}/tokens/{token} -> `delete_access_token`.
│   └── bootstrap                     # create token + configure ChatTea/Git credentials.
├── server                            # Local/internal Gitea lifecycle management.
│   ├── install                       # `chattea.commands.server.install_gitea` -> `chattea.server.install_binary`.
│   ├── init                          # `chattea.commands.server.init_gitea_server`.
│   ├── bootstrap                     # local install/init/admin/token/credential workflow via `bootstrap_gitea_server`.
│   ├── serve                         # `chattea.commands.server.serve_gitea`.
│   ├── start                         # `chattea.commands.server.start_gitea_service`.
│   ├── stop                          # `chattea.commands.server.stop_gitea_service`.
│   ├── restart                       # `chattea.commands.server.restart_gitea_service`.
│   ├── status                        # `chattea.commands.server.status_gitea_service`.
│   ├── logs                          # `chattea.commands.server.logs_gitea_service`.
│   ├── version                       # `chattea.commands.server.gitea_version`.
│   ├── health                        # `chattea.commands.server.check_gitea_health`.
│   └── config                        # Local app.ini helpers.
│       ├── path                      # `resolve_gitea_config_path`.
│       ├── show                      # `read_gitea_config`.
│       ├── get                       # `get_gitea_config_value`.
│       └── set                       # `set_gitea_config_value`.
├── repo                              # Repository operations.
│   ├── list                          # Gitea API-backed `list_repositories`.
│   ├── view                          # Gitea API-backed `view_repository`.
│   ├── create                        # Gitea API-backed `create_repository`.
│   ├── clone                         # Local git helper `clone_repository`.
│   └── migrate                       # Gitea API-backed `migrate_repository`.
├── issue                             # Repository issue operations; backed by /repos/{owner}/{repo}/issues.
│   ├── list                          # GET /repos/{owner}/{repo}/issues.
│   ├── view                          # GET /repos/{owner}/{repo}/issues/{index}.
│   ├── create                        # POST /repos/{owner}/{repo}/issues.
│   ├── edit                          # PATCH /repos/{owner}/{repo}/issues/{index}.
│   ├── close                         # PATCH issue state=closed.
│   ├── reopen                        # PATCH issue state=open.
│   ├── delete                        # DELETE /repos/{owner}/{repo}/issues/{index}.
│   ├── comment                       # Issue comment API.
│   ├── label                         # Issue label assignment API.
│   └── assign                        # Issue assignee API.
├── label                             # Repository labels.
│   ├── list                          # GET /repos/{owner}/{repo}/labels.
│   ├── view                          # GET /repos/{owner}/{repo}/labels/{id}.
│   ├── create                        # POST /repos/{owner}/{repo}/labels.
│   ├── edit                          # PATCH /repos/{owner}/{repo}/labels/{id}.
│   └── delete                        # DELETE /repos/{owner}/{repo}/labels/{id}.
├── milestone                         # Repository milestones.
│   ├── list                          # GET /repos/{owner}/{repo}/milestones.
│   ├── view                          # GET /repos/{owner}/{repo}/milestones/{id}.
│   ├── create                        # POST /repos/{owner}/{repo}/milestones.
│   ├── edit                          # PATCH /repos/{owner}/{repo}/milestones/{id}.
│   ├── close                         # PATCH milestone state=closed.
│   └── delete                        # DELETE /repos/{owner}/{repo}/milestones/{id}.
├── pr                                # Pull request operations; no local checkout helper in this tree.
│   ├── list                          # GET /repos/{owner}/{repo}/pulls.
│   ├── view                          # GET /repos/{owner}/{repo}/pulls/{index}.
│   ├── create                        # POST /repos/{owner}/{repo}/pulls.
│   ├── edit                          # PATCH /repos/{owner}/{repo}/pulls/{index}.
│   ├── close                         # PATCH PR state=closed.
│   ├── reopen                        # PATCH PR state=open.
│   ├── merge                         # POST /repos/{owner}/{repo}/pulls/{index}/merge.
│   ├── diff                          # GET /repos/{owner}/{repo}/pulls/{index}.diff.
│   ├── patch                         # GET /repos/{owner}/{repo}/pulls/{index}.patch.
│   ├── commits                       # GET /repos/{owner}/{repo}/pulls/{index}/commits.
│   ├── files                         # GET /repos/{owner}/{repo}/pulls/{index}/files.
│   ├── comment                       # PR issue-comment helpers through issue comment routes.
│   └── review                        # PR review list/create/submit routes.
├── release                           # Repository releases.
│   ├── list                          # GET /repos/{owner}/{repo}/releases.
│   ├── view                          # GET /repos/{owner}/{repo}/releases/{id}.
│   ├── latest                        # GET /repos/{owner}/{repo}/releases/latest.
│   ├── by-tag                        # GET /repos/{owner}/{repo}/releases/tags/{tag}.
│   ├── create                        # POST /repos/{owner}/{repo}/releases.
│   ├── edit                          # PATCH /repos/{owner}/{repo}/releases/{id}.
│   ├── delete                        # DELETE /repos/{owner}/{repo}/releases/{id}.
│   └── asset                         # Release asset list/delete; upload awaits multipart client support.
└── project                           # Repository-scoped Gitea Project board, not GitHub Projects v2.
    ├── list                          # GET /repos/{owner}/{repo}/projects.
    ├── view                          # GET /repos/{owner}/{repo}/projects/{id}.
    ├── create                        # POST /repos/{owner}/{repo}/projects.
    ├── edit                          # PATCH /repos/{owner}/{repo}/projects/{id}.
    ├── delete                        # DELETE /repos/{owner}/{repo}/projects/{id}.
    ├── column                        # Repository Project column API.
    │   ├── list                      # GET /repos/{owner}/{repo}/projects/{id}/columns.
    │   ├── create                    # POST /repos/{owner}/{repo}/projects/{id}/columns.
    │   ├── edit                      # PATCH /repos/{owner}/{repo}/projects/{id}/columns/{column_id}.
    │   └── delete                    # DELETE /repos/{owner}/{repo}/projects/{id}/columns/{column_id}.
    └── card                          # Project card API; REST path calls these `issues`.
        ├── list                      # GET /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues.
        ├── add                       # POST /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues/{issue_id}.
        ├── remove                    # DELETE /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues/{issue_id}.
        └── move                      # POST /repos/{owner}/{repo}/projects/{id}/issues/{issue_id}/move.
```

Compatibility aliases such as `project issue` may exist for transition, but they are not the official target surface. New docs and automation should use `project card`.

## Confirmed API Domains For Full Implementation

The following domains are confirmed from Gitea Swagger annotations in `core/gitea/routers/api/v1/**` and can be implemented as real commands. Each command added under these domains must still follow the implementation contract above.

- `user`: admin user creation/edit/delete routes under `/admin/users`; used for managed local bootstrap.
- `token`: `/users/{username}/tokens` list/create/delete; create requires BasicAuth or reverse proxy auth.
- `issue`: `/repos/{owner}/{repo}/issues`, comments, labels, reactions, pin/lock, dependencies, attachments, time tracking.
- `label`: `/repos/{owner}/{repo}/labels` and optional org label routes.
- `milestone`: `/repos/{owner}/{repo}/milestones`.
- `pr`: `/repos/{owner}/{repo}/pulls`, diff/patch, files, commits, merge, update, reviews, requested reviewers.
- `release`: `/repos/{owner}/{repo}/releases` and release assets.
- `runner` / `run` / `job` / `artifact`: Gitea Actions MVP surface for runner registration/lifecycle and PR-triggered run/job/log/artifact inspection. API-backed commands map to `/repos/{owner}/{repo}/actions/...`; `runner setup` commands are local system helpers that install/register/start a `gitea-runner` process.
- `project`: repository-scoped `/repos/{owner}/{repo}/projects` only; not GitHub Projects v2.
- `workflow`: `/repos/{owner}/{repo}/actions/workflows`.
- `run`: `/repos/{owner}/{repo}/actions/runs`.
- `job`: `/repos/{owner}/{repo}/actions/jobs`.
- `artifact`: `/repos/{owner}/{repo}/actions/artifacts`.
- `runner`: repo/org/user/admin scoped `/actions/runners` routes.
- `secret`: repo/org/user scoped `/actions/secrets` routes, noting user scope lacks a list route in the observed annotations.
- `variable`: repo/org/user scoped `/actions/variables` routes.
- `status`: `/repos/{owner}/{repo}/statuses/{sha}` and combined status routes.

## Bootstrap Direction

Initial configuration should be implemented as real workflow composition, not a placeholder command.

- `server bootstrap` or top-level `bootstrap` is a local managed-Gitea flow: install, init, start, create default user, generate/create token, run set-token, and verify `/user`.
- `token bootstrap` is the remote/existing-Gitea flow: BasicAuth create token, run set-token, and verify `/user`.
- Passwords should be read from prompt or `--password-env`; raw passwords should not be stored in ChatEnv or printed.
- Generated access tokens should be saved through the credential path, then masked in normal output.

## Non-Goals

- Do not claim full GitHub API or GitHub CLI compatibility.
- Do not model Gitea repository Project boards as GitHub Projects v2.
- Do not add `checkout` to the formal REST-backed tree. If needed later, design it explicitly as a local git helper with its own evidence and tests.
- Do not add runner lifecycle commands such as `runner install/start/stop/logs` until there is a real local runner lifecycle design.
- Do not put business logic only in Click command bodies.
- Do not make repository/project/issue/runner IDs ChatEnv fields; they are request parameters.

## Test And CI Contract

Each implemented domain should have these gates:

1. Unit tests for API path, method, payload, token resolution, and error handling.
2. Direct Python function tests for non-trivial command behavior.
3. CLI smoke tests for help, success, and expected failures.
4. Integration smoke where feasible against a local ChatArch Gitea instance, using task-local state and temporary repos/projects/issues.
5. `pytest`, package build, `twine check`, `mkdocs build --strict`, and `git diff --check` before PR readiness.

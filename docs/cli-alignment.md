# ChatTea CLI Alignment Plan

This document defines the target direction for ChatTea's CLI shape. The goal is not to clone GitHub CLI exactly. The goal is to keep GitHub/Gitea resource concepts familiar while preserving ChatTea-specific self-hosted Gitea operations.

## Evidence sources

The target tree is based on these sources:

- Current ChatTea CLI registry in `src/chattea/cli.py` and `src/chattea/commands/*`.
- Current Gitea API routes and Swagger annotations under `../gitea/routers/api/v1/**`.
- Current ChatArch Gitea release assets used by CI: `https://github.com/ChatArch/gitea/releases/download/v1.0.0/gitea-1.0.0-linux-amd64.xz`.
- GitHub/GH CLI resource model: `repo`, `issue`, `pr`, `release`, workflow/run concepts. This is a naming/UX reference, not a rule to copy commands without Gitea support.

## Product target

ChatTea should be a Gitea CLI with a GitHub-familiar resource model plus ChatTea-specific server management.

1. Keep familiar resource names where Gitea and GitHub overlap: `repo`, `issue`, `pr`, `release`, `workflow`, `run`, `job`, `artifact`, `label`, `milestone`, `status`.
2. Keep ChatTea-specific commands where GitHub CLI has no equivalent: `set-token` and `server`.
3. Keep CLI commands as thin adapters over importable Python functions. Every command should have a callable function behind it so other ChatArch tools do not need to shell out.
4. Do not describe Gitea repository Project boards as GitHub Projects v2. Gitea Project cards should be modeled as `project card`, not as top-level issues.
5. Default Gitea installation must use ChatArch internal Gitea releases, resolving latest when no version is provided.

## First alignment PR scope

This PR is the foundation step, not a full SDK implementation.

- Add `auth` while retaining `set-token` as a ChatTea custom quick command.
- Add `api` for raw Gitea API calls while long-tail routes are not yet wrapped.
- Add `project card` as the primary Project board card command group.
- Keep `project issue` as a compatibility alias for existing users.
- Change `server install` to default to latest ChatArch internal Gitea instead of requiring a community Gitea version.
- Document the target CLI tree and phased API implementation plan.

## Current customization on top of the standard model

ChatTea deliberately keeps these non-GitHub-CLI commands:

- `set-token`: quick ChatTea command to write `CHATTEA_BASE_URL` and `CHATTEA_TOKEN` into ChatEnv. This stays even though `auth login` also exists.
- `server`: self-hosted Gitea lifecycle management. GitHub CLI talks to GitHub SaaS and does not install GitHub; ChatTea manages local/internal Gitea.

`set-token` is intentionally not the same as ChatGH `set-token`. ChatGH `set-token` configures GitHub HTTPS credentials for the current Git repository, and can optionally save the token into ChatGH env config. ChatTea `set-token` configures the Gitea website/API base URL and API token in ChatEnv; it does not configure git transport credentials.

## Target CLI tree with notes

Entries marked "target" are planned CLI surface for later phases. They are not implemented by this PR unless they appear in the current tree in `docs/interface-tree.md`. Before implementing any target command, verify the backing Gitea API route or mark it explicitly as a local helper.

```text
chattea
├── set-token                         # ChatTea custom shortcut: configure base URL and token in ChatEnv.
├── auth                              # GitHub-familiar auth namespace; wraps the same token configuration backend.
│   ├── login                         # Configure Gitea base URL and API token.
│   ├── status                        # Show configured endpoint and masked token state.
│   ├── token                         # Show masked token for quick verification.
│   └── logout                        # Target: clear active ChatTea token/profile values.
├── api                               # Raw Gitea API passthrough for routes not yet wrapped.
├── repo                              # Repository operations; aligns with GitHub/Gitea repo concepts.
│   ├── list
│   ├── view
│   ├── create
│   ├── clone
│   ├── fork                          # Target: create a fork through Gitea repo fork API.
│   ├── delete                        # Target: delete a repository; destructive, requires confirmation.
│   ├── migrate                       # Gitea-specific migration from an existing Git URL.
│   └── transfer                      # Target: transfer repository owner through Gitea repo transfer API.
├── issue                             # Top-level Issue API, independent from Project cards.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── comment
│   ├── lock
│   ├── unlock
│   ├── pin
│   └── unpin
├── label                             # Issue/repo label management.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   └── delete
├── milestone                         # Issue milestone management.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   └── delete
├── pr                                # Pull request operations; Gitea path is /repos/{owner}/{repo}/pulls.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── merge
│   ├── diff                          # Gitea API-backed: fetch the PR diff for review without opening a browser.
│   ├── patch                         # Gitea API-backed: fetch patch-form PR diff.
│   ├── checkout                      # Local git helper, not a Gitea API route: fetch and check out the PR branch.
│   ├── files                         # List files changed by the PR.
│   ├── commits                       # List commits included in the PR.
│   └── review                        # Review lifecycle and requested reviewer operations.
│       ├── list
│       ├── view
│       ├── create
│       ├── submit
│       ├── dismiss
│       └── request
├── release                           # Release and release asset operations.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── delete
│   ├── upload                        # Upload a release asset.
│   └── download                      # Download a release asset.
├── project                           # Gitea repository-scoped Project board, not GitHub Projects v2.
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── delete
│   ├── column                        # Project board columns.
│   │   ├── list
│   │   ├── create
│   │   ├── edit
│   │   └── delete
│   └── card                          # Issue/PR cards inside a Project column.
│       ├── list
│       ├── add
│       ├── remove
│       └── move
├── workflow                          # Gitea Actions workflow definitions.
│   ├── list
│   ├── view
│   ├── enable
│   ├── disable
│   ├── run                           # Dispatch a workflow.
│   └── runs                          # List runs for one workflow.
├── run                               # Workflow run instances.
│   ├── list
│   ├── view
│   ├── jobs                          # List jobs in a run.
│   ├── logs                          # Convenience helper over job logs when possible.
│   ├── rerun                         # Rerun the whole workflow run.
│   ├── rerun-failed                  # Rerun failed jobs in the workflow run.
│   ├── delete                        # Delete a workflow run when supported by Gitea.
│   └── artifacts                     # List artifacts produced by a run.
├── job                               # Actions job operations.
│   ├── view
│   ├── logs                          # Download job logs.
│   └── rerun                         # Rerun one job.
├── artifact                          # Actions artifact operations.
│   ├── list
│   ├── view
│   ├── download
│   └── delete
├── runner                            # Actions runner API plus local runner lifecycle helpers.
│   ├── list                          # Supports repo/org/user/admin scope flags.
│   ├── view
│   ├── token                         # Create a registration token for a scope.
│   ├── edit
│   ├── delete
│   ├── install                       # Target local helper: install runner binary, not a Gitea REST route.
│   ├── register                      # Target local helper: register local runner using a registration token.
│   ├── start
│   ├── stop
│   ├── status
│   └── logs
├── secret                            # Actions secrets; supports repo/org/user scope flags.
│   ├── list
│   ├── set
│   └── delete
├── variable                          # Actions variables; supports repo/org/user scope flags.
│   ├── list
│   ├── view
│   ├── set
│   └── delete
├── status                            # Commit status API.
│   ├── list
│   ├── view
│   └── create
└── server                            # ChatTea custom local/internal Gitea service management.
    ├── install                       # Defaults to latest ChatArch internal Gitea release.
    ├── init
    ├── serve
    ├── start
    ├── stop
    ├── restart
    ├── status
    ├── logs
    ├── version
    ├── health
    └── config
        ├── path
        ├── show
        ├── get
        └── set
```

## Gitea Actions and runner model

Gitea Actions should not be collapsed into one command because the API has distinct concepts:

- `workflow`: the workflow definition in a repository.
- `run`: one workflow execution.
- `job`: one job inside a run.
- `artifact`: a file bundle produced by a run/job.
- `runner`: the machine/agent that executes jobs.
- `secret` and `variable`: scoped runtime configuration.

Runner APIs exist at multiple scopes: repository, organization, user, and admin. The CLI should avoid four duplicated trees and instead use scope options, for example:

```text
chattea runner list --repo OWNER/REPO
chattea runner list --org ORG
chattea runner list --user
chattea runner list --admin
chattea runner token --repo OWNER/REPO
```

## Implementation phases

### Phase 1: shape and foundation

- `auth` namespace.
- `api` passthrough.
- `project card` primary alias.
- `server install` defaults to ChatArch internal latest.
- Target tree documentation and tests.

### Phase 2: issue-oriented API

- `issue list/view/create/edit/close/reopen/comment`.
- `label list/view/create/edit/delete`.
- `milestone list/view/create/edit/close/delete`.

### Phase 3: PR-oriented API

- `pr list/view/create/edit/merge/diff/patch/files/commits`.
- `pr review list/view/create/submit/dismiss/request`.
- `pr checkout` as a local git helper.

### Phase 4: release/status/actions API

- `release` and release assets.
- `status` for commit statuses.
- `workflow`, `run`, `job`, `artifact`.
- `runner`, `secret`, `variable` with scope options.

## Non-goals

- Do not claim full GitHub API compatibility.
- Do not model Gitea Project boards as GitHub Projects v2.
- Do not put business logic only in Click command bodies.
- Do not make repository/project/issue/runner IDs ChatEnv fields; they are request parameters.

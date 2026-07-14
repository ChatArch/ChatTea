# ChatTea Interface Tree

ChatTea follows a GitHub-familiar resource model for Gitea APIs, plus ChatTea-specific commands for self-hosted/internal Gitea service management.

## Current CLI Surface

```text
chattea
├── set-token
├── api
├── auth
│   ├── login
│   ├── status
│   └── token
├── token
│   ├── create
│   ├── list
│   ├── delete
│   └── bootstrap
├── server
│   ├── install
│   ├── init
│   ├── bootstrap
│   ├── serve
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   ├── logs
│   ├── version
│   ├── health
│   └── config
│       ├── path
│       ├── show
│       ├── get
│       └── set
├── repo
│   ├── list
│   ├── view
│   ├── create
│   ├── clone
│   └── migrate
├── issue
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── delete
│   ├── comment
│   │   ├── list
│   │   ├── create
│   │   ├── edit
│   │   └── delete
│   ├── label
│   │   ├── add
│   │   └── remove
│   └── assign
│       ├── add
│       └── remove
├── label
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   └── delete
├── milestone
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   └── delete
├── pr
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── merge
│   ├── diff
│   ├── patch
│   ├── commits
│   ├── files
│   ├── comment
│   │   ├── list
│   │   └── create
│   └── review
│       ├── list
│       ├── create
│       └── submit
├── release
│   ├── list
│   ├── view
│   ├── latest
│   ├── by-tag
│   ├── create
│   ├── edit
│   ├── delete
│   └── asset
│       ├── list
│       └── delete
├── project
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── delete
│   ├── column
│   │   ├── list
│   │   ├── create
│   │   ├── edit
│   │   └── delete
│   ├── card
│   │   ├── list
│   │   ├── add
│   │   ├── remove
│   │   └── move
│   └── issue
│       ├── list
│       ├── add
│       ├── remove
│       └── move
├── runner
│   ├── token
│   ├── list
│   ├── view
│   ├── edit
│   ├── delete
│   └── setup
│       ├── install
│       ├── register
│       ├── start
│       ├── stop
│       ├── status
│       ├── logs
│       └── doctor
├── run
│   ├── list
│   ├── view
│   ├── jobs
│   ├── logs
│   ├── rerun
│   ├── rerun-failed
│   └── delete
├── job
│   ├── view
│   ├── logs
│   └── rerun
└── artifact
    ├── list
    ├── view
    ├── download
    └── delete
```

`project issue` is a compatibility alias for `project card`. Use `project card` in new docs and automation.

## Target CLI Direction

See `docs/cli-alignment.md` for the annotated target tree. The current implemented surface already covers the core Gitea resource groups:

- `repo`
- `issue`
- `label`
- `milestone`
- `pr`
- `release`
- `project`
- `runner`
- `run`
- `job`
- `artifact`

Future API work should grow only when there is a real Gitea route or a concrete local implementation contract. Candidate future groups include:

- `workflow`
- `secret`
- `variable`
- `status`

ChatTea-specific custom commands stay:

- `set-token`: configure an existing Gitea token in ChatEnv and repo-local git config.
- `server`: internal/self-hosted Gitea install, app.ini, process, and health management.

## Responsibilities

- `set-token`: store the default Gitea base URL and API token in the ChatEnv `ChatTea` active profile.
- `token create/list/delete/bootstrap`: create/list/delete Gitea access tokens via BasicAuth; bootstrap creates or rotates the managed token and then configures ChatTea/Git credentials.
- `auth login/status/token`: auxiliary namespace over the same credential state.
- `api`: raw Gitea API passthrough for routes not yet wrapped by first-class commands.
- `server install`: install latest ChatArch internal Gitea by default; `--version` can pin a release.
- `server init`: create a minimal `app.ini` for a local SQLite-backed Gitea instance; listen address and HTTP port are CLI init parameters, not Env fields.
- `server serve`: run Gitea in the foreground for debugging or one-off sessions.
- `server start/stop/restart/status/logs`: manage the fixed user-level systemd service `chattea-gitea.service`.
- `server version/health`: inspect the local binary or configured Gitea HTTP endpoint.
- `server config path/show/get/set`: inspect or update the managed Gitea `app.ini`, independent from ChatEnv.
- `repo list/view/create`: cover basic repository inventory and creation via Gitea API.
- `repo clone`: clone from the configured Gitea instance without configuring Git auth headers.
- `repo migrate`: create a Gitea migration from an existing Git clone URL.
- `issue list/view/create/edit/close/reopen/delete`: manage repository issues through `/repos/{owner}/{repo}/issues` routes.
- `issue comment list/create/edit/delete`: manage issue comments through issue comment routes; PR comments reuse the same Gitea issue-comment model.
- `issue label add/remove` and `issue assign add/remove`: manage issue labels and assignees through repo-scoped issue routes.
- `label list/view/create/edit/delete`: manage repository labels through `/repos/{owner}/{repo}/labels` routes.
- `milestone list/view/create/edit/close/delete`: manage repository milestones through `/repos/{owner}/{repo}/milestones` routes.
- `pr list/view/create/edit/close/reopen/merge/diff/patch/commits/files`: manage pull requests through `/repos/{owner}/{repo}/pulls` routes. `pr checkout` is intentionally not part of this surface.
- `pr review list/create/submit`: manage pull request reviews through `/repos/{owner}/{repo}/pulls/{index}/reviews` routes.
- `release list/view/latest/by-tag/create/edit/delete`: manage repository releases through `/repos/{owner}/{repo}/releases` routes.
- `release asset list/delete`: inspect and delete release assets. Multipart asset upload is left out until the HTTP client grows upload support.
- `project list/view/create/edit/delete`: manage repository-scoped Gitea Projects.
- `project column list/create/edit/delete`: manage columns in a repository Project board.
- `project card list/add/remove/move`: manage issue/PR cards in Project columns.
- `runner token/list/view/edit/delete`: manage Gitea Actions runners through repo/org/user/admin runner APIs.
- `runner setup install/register/start/stop/status/logs/doctor`: install and operate the local `gitea-runner` service for development and self-hosted runners.
- `run list/view/jobs/logs/rerun/rerun-failed/delete`: inspect and control Gitea Actions workflow runs.
- `job view/logs/rerun`: inspect job metadata, fetch logs, and rerun a job through its parent run.
- `artifact list/view/download/delete`: inspect, download, and delete Actions artifacts.

## CLI to Python Function Mapping

Every CLI command has an importable Python function behind it so integrations do not need to shell out.

```text
chattea set-token             -> chattea.commands.auth.configure_token
chattea auth login            -> chattea.commands.auth.configure_token
chattea auth status           -> chattea.config.load_config
chattea auth token            -> chattea.config.load_config
chattea api                   -> chattea.commands.api.call_api
chattea token create          -> chattea.commands.token.create_access_token
chattea token list            -> chattea.commands.token.list_access_tokens
chattea token delete          -> chattea.commands.token.delete_access_token
chattea token bootstrap       -> chattea.commands.token.bootstrap_access_token
chattea server install        -> chattea.commands.server.install_gitea
chattea server bootstrap      -> chattea.commands.server.bootstrap_gitea_server
chattea server init           -> chattea.commands.server.init_gitea_server
chattea server serve          -> chattea.commands.server.serve_gitea
chattea server start          -> chattea.commands.server.start_gitea_service
chattea server stop           -> chattea.commands.server.stop_gitea_service
chattea server restart        -> chattea.commands.server.restart_gitea_service
chattea server status         -> chattea.commands.server.status_gitea_service
chattea server logs           -> chattea.commands.server.logs_gitea_service
chattea server version        -> chattea.commands.server.gitea_version
chattea server health         -> chattea.commands.server.check_gitea_health
chattea server config path    -> chattea.commands.server.resolve_gitea_config_path
chattea server config show    -> chattea.commands.server.read_gitea_config
chattea server config get     -> chattea.commands.server.get_gitea_config_value
chattea server config set     -> chattea.commands.server.set_gitea_config_value
chattea repo list             -> chattea.commands.repo.list_repositories
chattea repo view             -> chattea.commands.repo.view_repository
chattea repo create           -> chattea.commands.repo.create_repository
chattea repo clone            -> chattea.commands.repo.clone_repository
chattea repo migrate          -> chattea.commands.repo.migrate_repository
chattea issue list            -> chattea.commands.issue.list_issues
chattea issue view            -> chattea.commands.issue.view_issue
chattea issue create          -> chattea.commands.issue.create_issue
chattea issue edit            -> chattea.commands.issue.edit_issue
chattea issue close           -> chattea.commands.issue.close_issue
chattea issue reopen          -> chattea.commands.issue.reopen_issue
chattea issue delete          -> chattea.commands.issue.delete_issue
chattea issue comment list    -> chattea.commands.issue.list_comments
chattea issue comment create  -> chattea.commands.issue.create_comment
chattea issue comment edit    -> chattea.commands.issue.edit_comment
chattea issue comment delete  -> chattea.commands.issue.delete_comment
chattea issue label add       -> chattea.commands.issue.add_labels
chattea issue label remove    -> chattea.commands.issue.remove_label
chattea issue assign add      -> chattea.commands.issue.add_assignees
chattea issue assign remove   -> chattea.commands.issue.remove_assignees
chattea label list            -> chattea.commands.label.list_labels
chattea label view            -> chattea.commands.label.view_label
chattea label create          -> chattea.commands.label.create_label
chattea label edit            -> chattea.commands.label.edit_label
chattea label delete          -> chattea.commands.label.delete_label
chattea milestone list        -> chattea.commands.milestone.list_milestones
chattea milestone view        -> chattea.commands.milestone.view_milestone
chattea milestone create      -> chattea.commands.milestone.create_milestone
chattea milestone edit        -> chattea.commands.milestone.edit_milestone
chattea milestone close       -> chattea.commands.milestone.close_milestone
chattea milestone delete      -> chattea.commands.milestone.delete_milestone
chattea pr list               -> chattea.commands.pr.list_prs
chattea pr view               -> chattea.commands.pr.view_pr
chattea pr create             -> chattea.commands.pr.create_pr
chattea pr edit               -> chattea.commands.pr.edit_pr
chattea pr close              -> chattea.commands.pr.close_pr
chattea pr reopen             -> chattea.commands.pr.reopen_pr
chattea pr merge              -> chattea.commands.pr.merge_pr
chattea pr diff               -> chattea.commands.pr.diff_pr
chattea pr patch              -> chattea.commands.pr.diff_pr
chattea pr commits            -> chattea.commands.pr.list_commits
chattea pr files              -> chattea.commands.pr.list_files
chattea pr review list        -> chattea.commands.pr.list_reviews
chattea pr review create      -> chattea.commands.pr.create_review
chattea pr review submit      -> chattea.commands.pr.submit_review
chattea release list          -> chattea.commands.release.list_releases
chattea release view          -> chattea.commands.release.view_release
chattea release latest        -> chattea.commands.release.latest_release
chattea release by-tag        -> chattea.commands.release.release_by_tag
chattea release create        -> chattea.commands.release.create_release
chattea release edit          -> chattea.commands.release.edit_release
chattea release delete        -> chattea.commands.release.delete_release
chattea release asset list    -> chattea.commands.release.list_assets
chattea release asset delete  -> chattea.commands.release.delete_asset
chattea runner token          -> chattea.commands.runner.create_runner_token
chattea runner list           -> chattea.commands.runner.list_registered_runners
chattea runner view           -> chattea.commands.runner.view_registered_runner
chattea runner edit           -> chattea.commands.runner.edit_registered_runner
chattea runner delete         -> chattea.commands.runner.delete_registered_runner
chattea runner setup install  -> chattea.commands.runner.install_runner
chattea runner setup register -> chattea.commands.runner.register_runner
chattea runner setup start    -> chattea.commands.runner.start_runner_service
chattea runner setup stop     -> chattea.commands.runner.stop_runner_service
chattea runner setup status   -> chattea.commands.runner.runner_service_status
chattea runner setup logs     -> chattea.commands.runner.runner_service_logs
chattea runner setup doctor   -> chattea.commands.runner.runner_root / runner_binary / runner_config checks
chattea run list              -> chattea.commands.run.list_runs
chattea run view              -> chattea.commands.run.view_run
chattea run jobs              -> chattea.commands.run.list_run_jobs
chattea run logs              -> chattea.commands.run.run_logs
chattea run rerun             -> chattea.commands.run.rerun_run
chattea run rerun-failed      -> chattea.commands.run.rerun_run
chattea run delete            -> chattea.commands.run.delete_run
chattea job view              -> chattea.commands.job.view_job
chattea job logs              -> chattea.commands.job.job_logs
chattea job rerun             -> chattea.commands.job.rerun_job
chattea artifact list         -> chattea.commands.artifact.list_artifacts
chattea artifact view         -> chattea.commands.artifact.view_artifact
chattea artifact download     -> chattea.commands.artifact.download_artifact
chattea artifact delete       -> chattea.commands.artifact.delete_artifact
chattea project list          -> chattea.commands.project.list_projects
chattea project view          -> chattea.commands.project.view_project
chattea project create        -> chattea.commands.project.create_project
chattea project edit          -> chattea.commands.project.edit_project
chattea project delete        -> chattea.commands.project.delete_project
chattea project column list   -> chattea.commands.project.list_columns
chattea project column create -> chattea.commands.project.create_column
chattea project column edit   -> chattea.commands.project.edit_column
chattea project column delete -> chattea.commands.project.delete_column
chattea project card list     -> chattea.commands.project.list_cards
chattea project card add      -> chattea.commands.project.add_card
chattea project card remove   -> chattea.commands.project.remove_card
chattea project card move     -> chattea.commands.project.move_card
```

Lower-level reusable modules stay available:

```text
chattea.config  -> ChatTeaEnvConfig, load_config, save_config, set_token
chattea.api     -> GiteaClient, repo_clone_url, repository Project API methods, Actions run/job/artifact/runner API methods
chattea.server  -> install_binary, init_instance, run_gitea, write_user_service
chattea.commands.runner -> runner binary install, registration, user service helpers
```

CLI command modules should parse options, call these functions/classes, and render results only.

## ChatEnv Boundary

Official ChatEnv fields are:

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

`CHATTEA_URL` and old `CHATTEA_GITEA_*` names are legacy read-only fallbacks. Listen address, HTTP port, domain, service name, install version, repo names, project IDs, issue IDs, and runner IDs are intentionally not official Env fields.

## Interaction Boundary

Commands with recoverable missing input use ChatStyle `CommandSchema`, `CommandField`, `add_interactive_option()`, and `resolve_command_inputs()`.

- `-i` / `--interactive`: force prompts.
- `-I` / `--no-interactive`: disable prompts and fail fast.
- default `interactive=None`: auto-prompt only when missing input is recoverable.

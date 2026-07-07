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
└── project
    ├── list
    ├── view
    ├── create
    ├── edit
    ├── delete
    ├── column
    │   ├── list
    │   ├── create
    │   ├── edit
    │   └── delete
    ├── card
    │   ├── list
    │   ├── add
    │   ├── remove
    │   └── move
    └── issue
        ├── list
        ├── add
        ├── remove
        └── move
```

`project issue` is a compatibility alias for `project card`. Use `project card` in new docs and automation.

## Target CLI Direction

See `docs/cli-alignment.md` for the annotated target tree. In short, future API work should grow along these GitHub/Gitea resource groups:

- `repo`
- `issue`
- `label`
- `milestone`
- `pr`
- `release`
- `project`
- `workflow`
- `run`
- `job`
- `artifact`
- `runner`
- `secret`
- `variable`
- `status`

ChatTea-specific custom commands stay:

- `set-token`: configure an existing Gitea token in ChatEnv and repo-local git config.
- `server`: internal/self-hosted Gitea install, app.ini, process, and health management.

## Responsibilities

- `set-token`: store the default Gitea base URL and API token in the ChatEnv `ChatTea` active profile.
- `token create/list/delete/bootstrap`: create/list/delete Gitea access tokens via BasicAuth; bootstrap creates a token and then configures ChatTea/Git credentials.
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
- `project list/view/create/edit/delete`: manage repository-scoped Gitea Projects.
- `project column list/create/edit/delete`: manage columns in a repository Project board.
- `project card list/add/remove/move`: manage issue/PR cards in Project columns.

## CLI to Python Function Mapping

Every CLI command has an importable Python function behind it so integrations do not need to shell out.

```text
chattea set-token             -> chattea.commands.auth.configure_token
chattea auth login            -> chattea.commands.auth.configure_token
chattea auth status           -> chattea.config.load_config
chattea auth token            -> chattea.config.load_config
chattea api                   -> chattea.commands.api.call_api
chattea server install        -> chattea.commands.server.install_gitea
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
chattea.api     -> GiteaClient, repo_clone_url, repository Project API methods
chattea.git     -> clone_repo
chattea.server  -> install_binary, init_instance, run_gitea, write_user_service
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

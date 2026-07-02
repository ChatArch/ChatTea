# ChatTea Interface Tree

ChatTea targets the practical Gitea lifecycle: install a local Gitea binary, initialize a minimal instance, run/manage the service, configure an API token, and perform basic repository operations.

## P0 CLI Surface

```text
chattea
├── set-token
├── server
│   ├── install
│   ├── init
│   ├── serve
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   ├── logs
│   ├── version
│   └── health
└── repo
    ├── list
    ├── view
    ├── create
    ├── clone
    └── migrate
```

## Responsibilities

- `set-token`: store the default Gitea base URL and API token in the ChatEnv `ChatTea` active profile.
- `server install`: download a Gitea Linux binary into a local prefix.
- `server init`: create a minimal `app.ini` for a local SQLite-backed Gitea instance under `$CHATARCH_HOME/chattea` by default.
- `server serve`: run Gitea in the foreground for debugging or one-off sessions.
- `server start/stop/restart/status/logs`: manage the fixed user-level systemd service `chattea-gitea.service`.
- `server version/health`: inspect the local binary or configured Gitea HTTP endpoint.
- `repo list/view/create`: cover basic repository inventory and creation via Gitea API.
- `repo clone`: clone from the configured Gitea instance without configuring Git auth headers.
- `repo migrate`: create a Gitea migration from an existing Git clone URL.

## CLI to Python Function Mapping

Every CLI command has an importable Python function behind it so integrations do not need to shell out.

```text
chattea set-token        -> chattea.cli.configure_token
chattea server install   -> chattea.commands.server.install_gitea
chattea server init      -> chattea.commands.server.init_gitea_server
chattea server serve     -> chattea.commands.server.serve_gitea
chattea server start     -> chattea.commands.server.start_gitea_service
chattea server stop      -> chattea.commands.server.stop_gitea_service
chattea server restart   -> chattea.commands.server.restart_gitea_service
chattea server status    -> chattea.commands.server.status_gitea_service
chattea server logs      -> chattea.commands.server.logs_gitea_service
chattea server version   -> chattea.commands.server.gitea_version
chattea server health    -> chattea.commands.server.check_gitea_health
chattea repo list        -> chattea.commands.repo.list_repositories
chattea repo view        -> chattea.commands.repo.view_repository
chattea repo create      -> chattea.commands.repo.create_repository
chattea repo clone       -> chattea.commands.repo.clone_repository
chattea repo migrate     -> chattea.commands.repo.migrate_repository
```

Lower-level reusable modules stay available:

```text
chattea.config  -> ChatTeaEnvConfig, load_config, save_config, set_token
chattea.api     -> GiteaClient, repo_clone_url
chattea.git     -> clone_repo
chattea.server  -> install_binary, init_instance, run_gitea, write_user_service
```

CLI command modules should parse options, call these functions/classes, and render results only.

## ChatEnv Boundary

Official ChatEnv fields are:

```text
CHATTEA_GITEA_BASE_URL
CHATTEA_GITEA_LISTEN_ADDR
CHATTEA_GITEA_HTTP_PORT
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_GITEA_BINARY
CHATTEA_GITEA_WORK_PATH
CHATTEA_GITEA_CONFIG
```

`CHATTEA_URL` is a legacy read-only fallback. `CHATTEA_GITEA_DOMAIN`, `CHATTEA_GITEA_SERVICE_NAME`, and `CHATTEA_GITEA_VERSION` are intentionally not official Env fields.

## Interaction Boundary

Commands with recoverable missing input use ChatStyle `CommandSchema`, `CommandField`, `add_interactive_option()`, and `resolve_command_inputs()`.

- `-i` / `--interactive`: force prompts.
- `-I` / `--no-interactive`: disable prompts and fail fast.
- default `interactive=None`: auto-prompt only when missing input is recoverable.

## Deferred Surface

PR, Actions, releases, hooks, org membership, and admin CRUD are intentionally deferred until the local install/start/repo workflow is stable.

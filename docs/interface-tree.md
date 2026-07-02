# ChatTea Interface Tree

ChatTea targets the practical Gitea lifecycle: install a local Gitea binary, initialize a minimal instance, run/manage the service, inspect/edit the managed Gitea `app.ini`, configure an API token, and perform basic repository operations.

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
│   ├── health
│   └── config
│       ├── path
│       ├── show
│       ├── get
│       └── set
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
- `server init`: create a minimal `app.ini` for a local SQLite-backed Gitea instance; listen address and HTTP port are CLI init parameters, not Env fields.
- `server serve`: run Gitea in the foreground for debugging or one-off sessions.
- `server start/stop/restart/status/logs`: manage the fixed user-level systemd service `chattea-gitea.service`.
- `server version/health`: inspect the local binary or configured Gitea HTTP endpoint.
- `server config path/show/get/set`: inspect or update the managed Gitea `app.ini`, independent from ChatEnv.
- `repo list/view/create`: cover basic repository inventory and creation via Gitea API.
- `repo clone`: clone from the configured Gitea instance without configuring Git auth headers.
- `repo migrate`: create a Gitea migration from an existing Git clone URL.

## CLI to Python Function Mapping

Every CLI command has an importable Python function behind it so integrations do not need to shell out.

```text
chattea set-token             -> chattea.cli.configure_token
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
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

`CHATTEA_URL` and old `CHATTEA_GITEA_*` names are legacy read-only fallbacks. Listen address, HTTP port, domain, service name, and install version are intentionally not official Env fields.

## Gitea app.ini Boundary

Gitea service configuration lives in the `app.ini` pointed to by `CHATTEA_CONFIG`. `chattea server init` writes values like:

```ini
[server]
HTTP_ADDR = 127.0.0.1
HTTP_PORT = 3000
DOMAIN = 127.0.0.1
ROOT_URL = http://127.0.0.1:3000/
```

Use `chattea server config show/get/set` to inspect or edit this file. `show` masks known secret keys unless `--no-mask` is passed.

## Interaction Boundary

Commands with recoverable missing input use ChatStyle `CommandSchema`, `CommandField`, `add_interactive_option()`, and `resolve_command_inputs()`.

- `-i` / `--interactive`: force prompts.
- `-I` / `--no-interactive`: disable prompts and fail fast.
- default `interactive=None`: auto-prompt only when missing input is recoverable.

## Deferred Surface

PR, Actions, releases, hooks, org membership, and admin CRUD are intentionally deferred until the local install/start/repo workflow is stable.

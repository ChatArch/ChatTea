# ChatTea Interface Tree

ChatTea first targets the practical Gitea lifecycle: install a local Gitea binary, initialize a minimal instance, run/manage the service, configure an API token, and perform basic repository operations.

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
- `server start/stop/restart/status/logs`: manage the user-level systemd service.
- `server version/health`: inspect the local binary or configured Gitea HTTP endpoint.
- `repo list/view/create`: cover basic repository inventory and creation via Gitea API.
- `repo clone`: clone from the configured Gitea instance without configuring Git auth headers.
- `repo migrate`: create a Gitea migration from an existing Git clone URL.

## Python API Boundary

The CLI must stay a thin wrapper. Reusable behavior lives in importable modules so Python callers do not need to shell out:

```text
chattea.config  -> ChatTeaEnvConfig, load_config, save_config, set_token
chattea.api     -> GiteaClient, repo_clone_url
chattea.git     -> clone_repo
chattea.server  -> install_binary, init_instance, run_gitea, write_user_service
```

CLI command modules should parse options, call these functions/classes, and render results only.

## Deferred Surface

PR, Actions, releases, hooks, org membership, and admin CRUD are intentionally deferred until the local install/start/repo workflow is stable.

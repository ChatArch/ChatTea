# ChatTea Docs

ChatTea is ChatArch's Gitea management CLI/API package. It covers local installation, initialization, service management, app.ini inspection/editing, token configuration, and basic repository operations. Since `0.2.1`, ChatTea uses ChatEnv and stores runtime files under `$CHATARCH_HOME/chattea` by default.

## CLI

```bash
chattea --help
chattea server --help
chattea server config --help
chattea repo --help
```

## CLI Tree

See `cli-alignment.md` for the evidence-bound alignment target.

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
│   ├── label
│   └── assign
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
│   └── review
├── release
│   ├── list
│   ├── view
│   ├── latest
│   ├── by-tag
│   ├── create
│   ├── edit
│   ├── delete
│   └── asset
├── runner
│   ├── token
│   ├── list
│   ├── view
│   ├── edit
│   ├── delete
│   └── setup
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
├── artifact
│   ├── list
│   ├── view
│   ├── download
│   └── delete
└── project
    ├── list
    ├── view
    ├── create
    ├── edit
    ├── delete
    ├── column
    ├── card
    └── issue
```

`server bootstrap` performs the first local install/init/admin/token/credential workflow. `token bootstrap` creates a Gitea access token through BasicAuth and then configures ChatTea/Git credentials. `issue`, `label`, `milestone`, `pr`, and `release` cover repo-level collaboration. `runner`, `run`, `job`, and `artifact` cover the first Gitea Actions/Flow surface: runner registration/lifecycle, PR-triggered runs, jobs, logs, and artifacts. `project issue` is a compatibility alias for `project card`. New docs and automation should use `project card`.

See [CLI Guide](cli-guide.md) for the complete CLI tree, Gitea Web screenshots, and end-to-end examples.

See [Repo Collaboration Quick Start](repo-collaboration-quickstart.md) for a local end-to-end repo collaboration smoke flow with terminal screenshots.

See [Actions / Flow Quick Start](actions-flow-quickstart.md) for the runner registration, PR-triggered run, job, and logs smoke flow.

## End-to-End Local Gitea Setup

Install on a new machine:

```bash
python -m pip install -U ChatTea
chattea --version
```

For source development:

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
python -m pip install -e ".[dev,docs]"
python -m pytest -q
```

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli test -t chattea

chattea server install
chattea server init --base-url http://127.0.0.1:3000 --listen-addr 127.0.0.1 --http-port 3000
chattea server start
chattea server health
```

For LAN access, pass listen settings to `server init`; they are written to Gitea `app.ini`, not ChatEnv:

```bash
chattea server init --base-url http://172.25.52.106:3000 --listen-addr 0.0.0.0 --http-port 3000
```

## ChatEnv Fields

Official ChatEnv fields:

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

- `CHATTEA_BASE_URL`: public Gitea website/API base URL, also used for Gitea `ROOT_URL` defaults.
- `CHATTEA_TOKEN`: sensitive Gitea API token.
- `CHATTEA_HOME`: ChatTea-managed local data root.
- `CHATTEA_BINARY`: Gitea binary path.
- `CHATTEA_WORK_PATH`: Gitea work directory for repositories, database, sessions, and logs.
- `CHATTEA_CONFIG`: Gitea `app.ini` path, not a separate ChatTea JSON config.

`CHATTEA_URL` and old `CHATTEA_GITEA_*` names are legacy read-only fallbacks. Listen address, HTTP port, domain, service name, and install version are not official Env fields.

## Gitea app.ini Flow

```bash
chattea server config path
chattea server config show
chattea server config get --section server --key HTTP_PORT
chattea server config set --section server --key HTTP_PORT --value 3001
chattea server restart
```

`server config show` masks known sensitive keys by default.

## Update and Autostart

Update ChatTea:

```bash
python -m pip install -U ChatTea
python -m chatenv.cli test -t chattea -I
chattea --version
```

Update the managed Gitea binary:

```bash
chattea server stop
chattea server install --force
chattea server start
chattea server health
```

Enable user systemd autostart:

```bash
chattea server start
chattea server status
loginctl enable-linger "$USER"
```

Some systems require administrator policy for `loginctl enable-linger`. Without lingering, the user service may not survive logout.

## Token and Repository Flow

```bash
chattea set-token --base-url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea repo create --owner gitea_admin --name demo
chattea repo list
chattea repo view gitea_admin/demo
chattea repo clone gitea_admin/demo
```

## Python API

The CLI is intentionally thin. Python callers can import the underlying functions directly:

```python
from chattea.commands.server import install_gitea, init_gitea_server, start_gitea_service
from chattea.commands.server import get_gitea_config_value, set_gitea_config_value
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

install_gitea("1.26.4")
init_gitea_server(base_url="http://127.0.0.1:3000", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()
set_gitea_config_value("server", "HTTP_PORT", "3001")

client = GiteaClient(url="http://127.0.0.1:3000", token="...")
repo = create_repository(name="demo", owner="gitea_admin")
clone = clone_repository("gitea_admin/demo")
```

## Local Preview

```bash
pip install -e ".[docs]"
mkdocs serve
```

Chinese version: [index.md](index.md).

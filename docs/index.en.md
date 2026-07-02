# ChatTea Docs

ChatTea is ChatArch's Gitea management CLI/API package. It covers local installation, initialization, service management, app.ini inspection/editing, token configuration, and basic repository operations. Since `0.2.0`, ChatTea uses ChatEnv and stores runtime files under `$CHATARCH_HOME/chattea` by default.

## CLI

```bash
chattea --help
chattea server --help
chattea server config --help
chattea repo --help
```

## End-to-End Local Gitea Setup

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli test -t chattea

chattea server install --version 1.26.4
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

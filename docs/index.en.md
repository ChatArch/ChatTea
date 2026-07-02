# ChatTea Docs

ChatTea is ChatArch's Gitea management CLI/API package. It covers local installation, initialization, service management, token configuration, and basic repository operations. Since `0.2.0`, ChatTea uses ChatEnv and stores runtime files under `$CHATARCH_HOME/chattea` by default.

## CLI

```bash
chattea --help
chattea server --help
chattea repo --help
```

## End-to-End Local Gitea Setup

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=127.0.0.1
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
python -m chatenv.cli test -t chattea

chattea server install --version 1.26.4
chattea server init
chattea server start
chattea server health
```

For LAN access, use a public base URL and bind to all interfaces:

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://172.25.52.106:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=0.0.0.0
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

## ChatEnv Fields

Official ChatEnv fields:

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

- `CHATTEA_GITEA_BASE_URL`: public Gitea website/API base URL, also used for Gitea `ROOT_URL`.
- `CHATTEA_GITEA_LISTEN_ADDR`: IP/host the local managed Gitea process binds to.
- `CHATTEA_GITEA_HTTP_PORT`: HTTP port the local managed Gitea process listens on.
- `CHATTEA_TOKEN`: sensitive Gitea API token.
- `CHATTEA_HOME`: ChatTea-managed local data root.
- `CHATTEA_GITEA_BINARY`: Gitea binary path.
- `CHATTEA_GITEA_WORK_PATH`: Gitea work directory for repositories, database, sessions, and logs.
- `CHATTEA_GITEA_CONFIG`: Gitea `app.ini` path.

`CHATTEA_URL` is a legacy read-only fallback. `CHATTEA_GITEA_DOMAIN`, `CHATTEA_GITEA_SERVICE_NAME`, and `CHATTEA_GITEA_VERSION` are not official Env fields.

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
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

install_gitea("1.26.4")
init_gitea_server(base_url="http://127.0.0.1:3000", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()

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

# ChatTea Docs

ChatTea is ChatArch's Gitea management CLI/API package. It covers local installation, initialization, service management, token configuration, and basic repository operations. Since `0.2.0`, ChatTea uses ChatEnv and stores runtime files under `$CHATARCH_HOME/chattea` by default.

## CLI

```bash
chattea --help
chattea server --help
chattea repo --help
```

## Python API

The CLI is intentionally thin. Python callers can import the underlying modules directly:

```python
from pathlib import Path
from chattea.server import install_binary, init_instance
from chattea.api import GiteaClient

binary = install_binary("1.26.4")
config = init_instance(binary=binary)
client = GiteaClient(url="http://127.0.0.1:3000", token="...")
```

`chattea set-token` writes `$CHATARCH_HOME/envs/ChatTea/.env`. Legacy `~/.config/chattea/config.json` remains a read-only compatibility fallback.

Default paths:

```text
$CHATARCH_HOME/chattea/bin/gitea
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
$CHATARCH_HOME/chattea/gitea/data/gitea.db
~/.config/systemd/user/chattea-gitea.service
```

ChatEnv fields:

```text
CHATTEA_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_GITEA_BINARY
CHATTEA_GITEA_WORK_PATH
CHATTEA_GITEA_CONFIG
CHATTEA_GITEA_HTTP_PORT
CHATTEA_GITEA_DOMAIN
CHATTEA_GITEA_SERVICE_NAME
```

## Local Preview

```bash
pip install -e ".[docs]"
mkdocs serve
```

Chinese version: [index.md](index.md).

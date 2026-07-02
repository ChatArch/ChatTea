# ChatTea Docs

ChatTea is ChatArch's Gitea management CLI/API package. The first version covers local installation, initialization, service management, token configuration, and basic repository operations.

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
config = init_instance(Path("~/gitea").expanduser(), binary=binary)
client = GiteaClient(url="http://127.0.0.1:3000", token="...")
```

## Local Preview

```bash
pip install -e ".[docs]"
mkdocs serve
```

Chinese version: [index.md](index.md).

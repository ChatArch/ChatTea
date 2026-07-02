# ChatTea 文档

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包。它覆盖从安装到启动 Gitea，以及最常用的 token 和仓库操作。`0.2.0` 起，ChatTea 接入 ChatEnv，默认路径收敛到 `$CHATARCH_HOME/chattea`。

## CLI

```bash
chattea --help
chattea server --help
chattea repo --help
```

命令树：

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

## 从安装到启动

```bash
chattea server install --version 1.26.4
chattea server init
chattea server start
chattea server health --url http://127.0.0.1:3000
```

调试时可以使用前台启动：

```bash
chattea server serve
```

## 配置 token

```bash
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
```

`set-token` 只保存 Gitea base URL 和 API token，不维护复杂 auth 子树。

配置写入 ChatEnv active profile：`$CHATARCH_HOME/envs/ChatTea/.env`。旧的 `~/.config/chattea/config.json` 只作为只读兼容 fallback。

默认路径：

```text
$CHATARCH_HOME/chattea/bin/gitea
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
$CHATARCH_HOME/chattea/gitea/data/gitea.db
~/.config/systemd/user/chattea-gitea.service
```

ChatEnv 字段：

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

## 仓库操作

```bash
chattea repo list
chattea repo view gitea_admin/demo
chattea repo create --owner gitea_admin --name demo
chattea repo clone gitea_admin/demo
chattea repo migrate --clone-url https://github.com/ChatArch/ChatTea.git --owner gitea_admin --name ChatTea
```

## Python API

CLI 只是一层薄封装。需要在 Python 中复用时，优先直接调用裸函数或 client：

```python
from pathlib import Path
from chattea.server import install_binary, init_instance
from chattea.api import GiteaClient

binary = install_binary("1.26.4")
config = init_instance(binary=binary)

client = GiteaClient(url="http://127.0.0.1:3000", token="...")
repos = client.list_repos()
```

更多接口树见：[interface-tree.md](interface-tree.md)。

## 本地预览

```bash
pip install -e ".[docs]"
mkdocs serve
```

英文版见：[index.en.md](index.en.md)。

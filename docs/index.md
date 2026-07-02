# ChatTea 文档

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包。第一版覆盖从安装到启动 Gitea，以及最常用的 token 和仓库操作。

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
chattea server init --work-path ~/gitea --http-port 3000
chattea server start --work-path ~/gitea --config ~/gitea/custom/conf/app.ini
chattea server health --url http://127.0.0.1:3000
```

调试时可以使用前台启动：

```bash
chattea server serve --work-path ~/gitea --config ~/gitea/custom/conf/app.ini
```

## 配置 token

```bash
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
```

`set-token` 只保存 Gitea base URL 和 API token，不维护复杂 auth 子树。

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
config = init_instance(Path("~/gitea").expanduser(), binary=binary)

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

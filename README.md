<div align="center">
    <a href="https://pypi.python.org/pypi/ChatTea">
        <img src="https://img.shields.io/pypi/v/ChatTea.svg" alt="PyPI version" />
    </a>
    <a href="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml">
        <img src="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml/badge.svg" alt="Tests" />
    </a>
    <a href="https://ChatArch.github.io/ChatTea">
        <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# ChatTea

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包，聚焦本地 Gitea 的安装、初始化、启动、token 配置和基础仓库操作。`0.2.0` 起配置接入 ChatEnv，默认运行目录收敛到 `~/.chatarch/chattea`。

## 快速开始

```bash
pip install -e ".[dev,docs]"
chattea --help
python -m pytest -q
```

## 从零启动一个 Gitea 服务

### 1. 初始化 ChatEnv

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea
```

### 2. 配置服务访问和监听地址

本机访问：

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=127.0.0.1
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

局域网访问：

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://172.25.52.106:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=0.0.0.0
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

### 3. 安装并初始化 Gitea

```bash
chattea server install --version 1.26.4
chattea server init
chattea server start
chattea server health
```

调试时可以前台运行：

```bash
chattea server serve
```

### 4. 配置 API token 并创建仓库

```bash
chattea set-token --base-url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea repo create --owner gitea_admin --name demo
chattea repo list
chattea repo view gitea_admin/demo
chattea repo clone gitea_admin/demo
```

迁移已有 Git 仓库：

```bash
chattea repo migrate \
  --clone-url https://github.com/ChatArch/ChatTea.git \
  --owner gitea_admin \
  --name ChatTea
```

## ChatEnv 字段

正式字段只有这些：

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

- `CHATTEA_GITEA_BASE_URL`：用户和 API 访问 Gitea 的完整地址，也用于 Gitea `ROOT_URL`。
- `CHATTEA_GITEA_LISTEN_ADDR`：本地 Gitea 进程绑定的 IP/host，例如 `127.0.0.1` 或 `0.0.0.0`。
- `CHATTEA_GITEA_HTTP_PORT`：本地 Gitea 进程监听端口，例如 `3000`。
- `CHATTEA_TOKEN`：Gitea API token，敏感字段，展示时默认 mask。
- `CHATTEA_HOME`：ChatTea 管理本地 Gitea 的根目录，默认 `$CHATARCH_HOME/chattea`。
- `CHATTEA_GITEA_BINARY`：Gitea binary 路径，默认 `$CHATTEA_HOME/bin/gitea`。
- `CHATTEA_GITEA_WORK_PATH`：Gitea 工作目录，保存仓库、数据库、session 和日志。
- `CHATTEA_GITEA_CONFIG`：Gitea `app.ini` 文件路径，默认 `$CHATTEA_GITEA_WORK_PATH/custom/conf/app.ini`。

旧字段 `CHATTEA_URL` 只做兼容读取，不再作为正式 Env 展示或写入。`CHATTEA_GITEA_DOMAIN`、`CHATTEA_GITEA_SERVICE_NAME`、`CHATTEA_GITEA_VERSION` 不作为 Env 暴露。

完整逐项解释和保留/删除理由见 `docs/index.md`。

## CLI 结构

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

## Python API

CLI 是薄封装。需要集成调用时，可以直接 import 函数或 client：

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

## 开发说明

扩展脚手架前，先阅读 `DEVELOP.md` 和 `AGENTS.md`。接口树见 `docs/interface-tree.md`。

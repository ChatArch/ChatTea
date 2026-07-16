<div align="center">
    <a href="https://pypi.python.org/pypi/ChatTea">
        <img src="https://img.shields.io/pypi/v/ChatTea.svg" alt="PyPI version" />
    </a>
    <a href="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml">
        <img src="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml/badge.svg" alt="Tests" />
    </a>
    <a href="https://arch.gh.wzhecnu.cn/ChatTea/">
        <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# ChatTea

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包，聚焦内部 Gitea 的安装、初始化、启动、token 配置、Gitea `app.ini` 查看/编辑和仓库协作自动化。`server install` 默认安装最新 ChatArch 内部 Gitea release；`0.2.1` 起配置接入 ChatEnv，默认运行目录收敛到 `~/.chatarch/chattea`。

文档入口：<https://arch.gh.wzhecnu.cn/ChatTea/>

按场景选择文档：

| 场景 | 文档 |
| --- | --- |
| 从空机器启动本地 Gitea | `docs/from-scratch-quickstart.md` |
| 仓库、Issue、Project、PR、Release 协作 | `docs/repo-collaboration-quickstart.md` |
| 机器人账号、服务账号和 `@bot` 唤醒 | `docs/bot-service-account-plan.md` |
| Runner、Actions run/job/log/artifact | `docs/actions-flow-quickstart.md` |
| 完整 CLI 树和截图示例 | `docs/cli-guide.md` |

## 快速开始

```bash
pip install -e ".[dev,docs]"
chattea --help
python -m pytest -q
```

## 从零启动一个 Gitea 服务

### 0. 新机器安装

稳定版：

```bash
python -m pip install -U ChatTea
chattea --version
```

源码开发：

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
python -m pip install -e ".[dev,docs]"
python -m pytest -q
```

### 1. 初始化 ChatEnv

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea
```

### 2. 配置长期 Env

```bash
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
chattea set-token --base-url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea auth status
```

高级路径配置：

```bash
python -m chatenv.cli set CHATTEA_HOME=/srv/chattea
python -m chatenv.cli set CHATTEA_BINARY=/usr/local/bin/gitea
python -m chatenv.cli set CHATTEA_WORK_PATH=/srv/gitea
python -m chatenv.cli set CHATTEA_CONFIG=/srv/gitea/custom/conf/app.ini
```

### 3. 一步启动本地 Gitea

```bash
export GITEA_ADMIN_PASSWORD='[REDACTED]'
chattea server bootstrap \
  --base-url http://127.0.0.1:3000 \
  --admin-user gitea_admin \
  --admin-email admin@example.com \
  --admin-password-env GITEA_ADMIN_PASSWORD \
  -I
chattea server health
```

`server bootstrap` 会串起安装、初始化 `app.ini`、创建初始 admin、生成 token、写入 ChatTea/ChatEnv 凭据和健康检查。需要定制监听地址或端口时，再使用 `server init` 或 `server config set` 修改 Gitea `app.ini`；`--listen-addr` 和 `--http-port` 不属于 ChatEnv 字段。

局域网访问可以这样初始化底层 `app.ini`：

```bash
chattea server init --base-url http://172.25.52.106:3000 --listen-addr 0.0.0.0 --http-port 3000
```

### 4. 查看和修改 Gitea app.ini

```bash
chattea server config path
chattea server config show
chattea server config get --section server --key HTTP_PORT
chattea server config set --section server --key HTTP_PORT --value 3001
chattea server restart
```

`server config show` 默认会 mask `SECRET_KEY`、`INTERNAL_TOKEN`、`JWT_SECRET` 等敏感值。

### 5. 更新和自启动

更新 ChatTea 包：

```bash
python -m pip install -U ChatTea
python -m chatenv.cli test -t chattea -I
chattea --version
```

更新 Gitea binary：

```bash
chattea server stop
chattea server install --force
chattea server start
chattea server health
```

启用 user systemd 自启动：

```bash
chattea server start
chattea server status
loginctl enable-linger "$USER"
```

`loginctl enable-linger` 可能需要管理员策略允许；如果失败，服务仍可在当前登录会话里运行，但退出登录后不一定保持。

### 6. 仓库操作

```bash
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

### 7. 单仓库 Project board 操作

`chattea project` 封装 Gitea repository-scoped Project board API，不是 GitHub Projects v2 兼容层。Project 中的 issue/PR 是 card，所以主入口是 `project card`；`project issue` 仅作为兼容 alias 保留。

```bash
chattea project create --repo gitea_admin/demo --title Roadmap
chattea project column create --repo gitea_admin/demo 1 --title Todo
chattea project card add --repo gitea_admin/demo 1 2 42
chattea project card move --repo gitea_admin/demo 1 42 --column 3 --sorting 0
```

## ChatEnv 字段

正式字段只有这些：

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

- `CHATTEA_BASE_URL`：用户和 API 访问 Gitea 的完整地址，也用于 Gitea `ROOT_URL`。
- `CHATTEA_TOKEN`：Gitea API token，敏感字段，展示时默认 mask。
- `CHATTEA_HOME`：ChatTea 管理本地 Gitea 的根目录，默认 `$CHATARCH_HOME/chattea`。
- `CHATTEA_BINARY`：Gitea binary 路径，默认 `$CHATTEA_HOME/bin/gitea`。
- `CHATTEA_WORK_PATH`：Gitea 工作目录，保存仓库、数据库、session 和日志。
- `CHATTEA_CONFIG`：Gitea `app.ini` 文件路径，默认 `$CHATTEA_WORK_PATH/custom/conf/app.ini`。

旧字段 `CHATTEA_URL` 和 `CHATTEA_GITEA_*` 只做兼容读取，不再作为正式 Env 展示或写入。`listen addr / port / domain / service name / version` 不作为 Env 暴露。

完整逐项解释和保留/删除理由见 `docs/index.md`。

## CLI 结构

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
├── bot
│   ├── plan
│   ├── create
│   ├── delete
│   └── token
│       └── create
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
│   ├── registry
│   ├── local
│   ├── pool
│   └── workflow
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

See `docs/cli-guide.md` for the complete CLI tree, Gitea Web screenshots, and end-to-end examples.

See `docs/repo-collaboration-quickstart.md` for a local end-to-end repo collaboration practice flow with terminal screenshots.

See `docs/actions-flow-quickstart.md` and `docs/runner-environment-and-registration.md` for Actions runner/run/job/log practice and Runner environment details.

## Python API

CLI 是薄封装。需要集成调用时，可以直接 import 函数或 client：

```python
from chattea.commands.server import install_gitea, init_gitea_server, start_gitea_service
from chattea.commands.server import get_gitea_config_value, set_gitea_config_value
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

install_gitea()
init_gitea_server(base_url="http://127.0.0.1:3000", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()
set_gitea_config_value("server", "HTTP_PORT", "3001")

client = GiteaClient(url="http://127.0.0.1:3000", token="...")
repo = create_repository(name="demo", owner="gitea_admin")
clone = clone_repository("gitea_admin/demo")
```

## 开发说明

扩展脚手架前，先阅读 `DEVELOP.md` 和 `AGENTS.md`。接口树见 `docs/interface-tree.md`。

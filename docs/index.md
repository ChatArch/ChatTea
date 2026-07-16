# ChatTea 文档

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包。它负责下载安装到启动本地 Gitea，也提供 令牌 配置、仓库创建、仓库查看、clone、迁移，以及 Gitea `app.ini` 的查看和小范围编辑。`0.2.1` 起，ChatTea 配置接入 ChatEnv，正式 Env 只保留长期、常用、跨命令共享的配置。

站点入口：<https://arch.gh.wzhecnu.cn/ChatTea/>

## 按场景选择文档

| 场景 | 文档 |
| --- | --- |
| 从空机器启动本地 Gitea | [从零开始快速开始](from-scratch-quickstart.md) |
| 仓库、问题、项目看板、PR、发布版本协作 | [仓库协作快速开始](repo-collaboration-quickstart.md) |
| 已有 Gitea 服务上的组织、用户、仓库、问题、PR 端到端流程 | [Gitea 端到端快速开始](gitea-quickstart.md) |
| ChatTea 管理的 Gitea 服务运维、nginx/public 入口、安全边界 | [Gitea 服务运维](gitea-service-operations.md) |
| Gitea 仓库、用户、组织、团队可见性和访问令牌权限范围 | [Gitea 权限与可见性](gitea-permissions-and-visibility.md) |
| 机器人账号、服务账号、`@bot` 唤醒和自动化主体实践 | [机器人账号与服务账号](bot-service-account-plan.md) |
| 运行器、Actions 运行、任务、日志和产物 | [Actions / Flow（动作 / 流程）快速开始](actions-flow-quickstart.md) |
| Runner 安装环境、执行范围、注册、多实例和并发维护 | [Runner 运行环境与多实例](runner-environment-and-registration.md) |
| Runner 多实例注册、维护和第一版 infra 方案 | [Runner 多实例第一版方案](runner-multi-instance-plan.md) |
| 完整 CLI 树、截图和路由映射 | [CLI 实战指南](cli-guide.md) |
| 简明 CLI 能力地图与当前封装缺口 | [CLI 能力地图](chattea-cli-tree.md) |
| 当前接口树与 Python 函数映射 | [接口树](interface-tree.md) |

## CLI

```bash
chattea --help
chattea server --help
chattea server config --help
chattea repo --help
```

命令树：

完整对齐目标见 `cli-alignment.md`。

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

`server bootstrap` 负责第一轮本地 install/init/admin/令牌/credential 流程。`token bootstrap` 通过 BasicAuth 创建 Gitea 访问令牌，然后配置 ChatTea/Git 凭据。`issue`、`label`、`milestone`、`pr` 和 `release` 覆盖 仓库 级协作。`runner`、`run`、`job` 和 `artifact` 覆盖第一版 Gitea Actions/Flow 能力：运行器 注册和生命周期、PR 触发的 run、job、logs 和 产物。`project issue` 是 `project card` 的兼容别名；新文档和新自动化应使用 `project card`。

机器人账号与服务账号已进入第一版 local backend 实践。Gitea 当前底层支持 bot 用户类型，本机 admin CLI 可创建 bot，但稳定 REST API 尚未完整暴露 bot 管理能力；已验证的能力和 `@bot` 唤醒机制见 [机器人账号与服务账号](bot-service-account-plan.md)。

完整 CLI 树、Gitea Web 截图和端到端示例见 [CLI 指南](cli-guide.md)。

本地端到端仓库协作实践流程和终端截图见 [仓库协作快速开始](repo-collaboration-quickstart.md)。

Actions / Flow 中的运行器注册、PR 触发 run、job 和 logs 实践流程见 [Actions / Flow（动作 / 流程）快速开始](actions-flow-quickstart.md)。

## 新机器配置清单

在一台新机器上，先确认 Python 环境、ChatEnv、ChatTea 和 Gitea 运行时 目录都准备好。推荐先用普通用户安装和运行，ChatTea 默认使用 用户级 systemd，不需要 root 级系统服务。

### 1. 安装 ChatTea

从 PyPI 安装稳定版：

```bash
python -m pip install -U ChatTea
```

从源码调试或参与开发：

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
python -m pip install -e ".[dev,docs]"
```

确认 CLI 可用：

```bash
chattea --version
chattea --help
```

### 2. 初始化 ChatEnv 配置档

ChatTea 的长期配置走 ChatEnv。新机器先创建 active 配置档，再查看默认值：

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea -I
```

最少需要设置 Gitea 网站/API 地址：

```bash
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:<port>
```

如果数据目录不想放在默认 `$CHATARCH_HOME/chattea`，再设置高级路径：

```bash
python -m chatenv.cli set CHATTEA_HOME=/srv/chattea
python -m chatenv.cli set CHATTEA_WORK_PATH=/srv/gitea
python -m chatenv.cli set CHATTEA_CONFIG=/srv/gitea/custom/conf/app.ini
```

### 3. 初始化 Gitea app.ini

`listen addr`、`HTTP port`、`DOMAIN`、`ROOT_URL` 都属于 Gitea `app.ini`，不属于 ChatEnv。新机器按访问场景选择一组参数。

本机访问：

```bash
chattea server install
chattea server init --base-url http://127.0.0.1:<port> --listen-addr 127.0.0.1 --http-port 3000
```

局域网访问：

```bash
chattea server install
chattea server init --base-url http://172.25.52.106:3000 --listen-addr 0.0.0.0 --http-port 3000
```

反向代理访问：

```bash
chattea server install
chattea server init --base-url https://git.example.com --listen-addr 127.0.0.1 --http-port 3000
```

初始化后可以检查生成的配置：

```bash
chattea server config path
chattea server config show
chattea server config get --section server --key ROOT_URL
```

## 从零创建一个本地 Gitea 服务

### 1. 安装 ChatTea 开发环境

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
pip install -e ".[dev,docs]"
python -m pytest -q
```

安装后确认 CLI 和 ChatEnv provider 可用：

```bash
chattea --help
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea
```

### 2. 配置长期 Env

ChatTea 的 Env 只放长期共享配置。最常用的是 Gitea 网站/API 入口和 API 令牌：

```bash
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:<port>
chattea set-token --base-url http://127.0.0.1:<port> --token "$GITEA_TOKEN"
```

如果需要改目录或使用已有 Gitea 二进制文件，可以设置高级路径字段：

```bash
python -m chatenv.cli set CHATTEA_HOME=/srv/chattea
python -m chatenv.cli set CHATTEA_BINARY=/usr/local/bin/gitea
python -m chatenv.cli set CHATTEA_WORK_PATH=/srv/gitea
python -m chatenv.cli set CHATTEA_CONFIG=/srv/gitea/custom/conf/app.ini
```

### 3. 一步启动本地 Gitea

从空机器开始，优先使用 `server bootstrap`，它会串起安装、初始化 `app.ini`、创建初始 admin、生成 令牌、写入 ChatTea/ChatEnv 凭据和健康检查：

```bash
export GITEA_ADMIN_PASSWORD='***'
chattea server bootstrap \
  --base-url http://127.0.0.1:<port> \
  --admin-user gitea_admin \
  --admin-email admin@example.com \
  --admin-password-env GITEA_ADMIN_PASSWORD \
  -I
chattea server health
```

`server bootstrap` 适合 首次运行 happy path。需要只改底层 Gitea `app.ini` 时，再使用 `server init` 或 `server config set`。

`listen address` 和 `HTTP port` 是 Gitea app.ini 的内容，不是 ChatEnv。需要改变监听 IP/端口时，作为初始化参数传给 CLI：

本机访问：

```bash
chattea server init \
  --base-url http://127.0.0.1:<port> \
  --listen-addr 127.0.0.1 \
  --http-port 3000
```

局域网访问：

```bash
chattea server init \
  --base-url http://172.25.52.106:3000 \
  --listen-addr 0.0.0.0 \
  --http-port 3000
```

反向代理访问：

```bash
chattea server init \
  --base-url https://git.example.com \
  --listen-addr 127.0.0.1 \
  --http-port 3000
```

这些参数会落到 Gitea `app.ini`：

```ini
[server]
HTTP_ADDR = 127.0.0.1
HTTP_PORT = 3000
DOMAIN = git.example.com
ROOT_URL = https://git.example.com/
```

### 4. 启动和检查服务

`server bootstrap` 已经可以完成首次启动和健康检查。后续运行维护使用 用户级 systemd：

```bash
chattea server start
chattea server status
chattea server logs --lines 100
chattea server health
```

开发调试时也可以前台启动：

```bash
chattea server serve
```

停止或重启：

```bash
chattea server stop
chattea server restart
```

systemd unit 名固定为 `chattea-gitea.service`。它是内部实现细节，不作为 Env 暴露。

## 自启动和运行维护

ChatTea 使用 用户级 systemd 管理 Gitea。`chattea server start` 会写入 用户级 unit、执行 `systemctl --user daemon-reload`，并 `enable --now` 固定的 `chattea-gitea.service`。

首次启用：

```bash
chattea server start
chattea server status
chattea server health
```

查看日志：

```bash
chattea server logs --lines 100
chattea server logs --follow
```

如果希望用户退出登录后服务仍保持运行，机器需要启用 user lingering：

```bash
loginctl enable-linger "$USER"
```

有些系统需要管理员权限才能启用 lingering；如果这条命令失败，请让管理员执行或确认机器的 用户级 systemd 策略。启用后可以重启机器，再检查：

```bash
systemctl --user status chattea-gitea.service
chattea server health
```

如果只是临时调试，不需要自启动，可以不用 `server start`，直接前台运行：

```bash
chattea server serve
```

## 更新和升级

更新分成三类：更新 ChatTea 包、更新 Gitea 二进制文件、更新 Gitea app.ini。不要把三者混在一起。

### 更新 ChatTea 包

从 PyPI 更新：

```bash
python -m pip install -U ChatTea
chattea --version
python -m chatenv.cli test -t chattea -I
```

从源码分支更新：

```bash
git pull
python -m pip install -e ".[dev,docs]"
python -m pytest -q
chattea --version
```

### 更新 Gitea 二进制文件

更新 Gitea 本体时，先停止服务，再覆盖 二进制文件，最后启动并健康检查：

```bash
chattea server stop
chattea server install --force
chattea server start
chattea server version
chattea server health
```

如果 Gitea 新版本需要数据库迁移，Gitea 通常会在启动时处理；更新前仍建议备份 `CHATTEA_WORK_PATH`，尤其是 `data/gitea.db` 和 `data/gitea-repositories/`。

### 更新 Gitea app.ini

小范围修改用 `server config set`，例如改端口：

```bash
chattea server config set --section server --key HTTP_PORT --value 3001
chattea server restart
chattea server config get --section server --key HTTP_PORT
```

不要随便用 `chattea server init --force` 覆盖已有 `app.ini`。`--force` 会重新生成配置和安全密钥，只适合明确要重建本地测试实例的场景。生产或长期使用的实例应该优先备份并用 `server config set` 修改单项配置。

## 查看和修改 Gitea app.ini

Gitea 背后的服务配置在 `app.ini`，这和 ChatEnv 是两套东西。ChatEnv 负责 ChatTea 的长期参数，`server config` 负责查看或小范围编辑 Gitea app.ini。

查看 app.ini 路径：

```bash
chattea server config path
```

查看 app.ini 内容，默认会 mask `SECRET_KEY`、`INTERNAL_TOKEN`、`JWT_SECRET` 等敏感值：

```bash
chattea server config show
```

读取单个配置：

```bash
chattea server config get --section server --key HTTP_PORT
```

修改单个配置：

```bash
chattea server config set --section server --key HTTP_PORT --value 3001
chattea server restart
```

`server config set` 是编辑 Gitea `app.ini`，不是写 ChatEnv。

## 创建和使用仓库

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

缺少可恢复参数时，相关命令会走 ChatStyle 交互；`-i` 强制交互，`-I` 禁止交互并快速失败。

## ChatEnv 字段逐项说明

### `CHATTEA_BASE_URL`

这是用户、浏览器和 ChatTea API 访问 Gitea 的完整地址。常见值是 `http://127.0.0.1:<port>`、`http://172.25.52.106:3000` 或 `https://git.example.com`。

它会用于 ChatTea API client 的默认 URL，也会在 `server init` 默认值中用于 Gitea `ROOT_URL`。Gitea `DOMAIN` 会从这个 URL 的 host 解析出来。

决定：保留。它是服务身份和 API 入口，是长期共享配置。

### `CHATTEA_TOKEN`

这是 Gitea API 令牌，用于需要认证的仓库命令，例如 `repo list`、`repo create`、`repo view` 和 `repo migrate`。

它是敏感字段。`chatenv cat -t chattea` 默认应该 mask 展示；只有用户显式 `--no-mask` 时才可能明文输出。

决定：保留。这是访问 Gitea API 的必要认证配置。

### `CHATTEA_HOME`

这是 ChatTea 管理本地 Gitea 的根目录。默认值来自 ChatEnv 的 `CHATARCH_HOME`，通常是 `$CHATARCH_HOME/chattea`。

默认的 Gitea 二进制文件、work path 和 app.ini 都会从这个目录派生。用户如果要把整个本地管理目录放到别的磁盘，改这个变量最自然。

决定：保留。这是路径总控配置，但属于高级配置。

### `CHATTEA_BINARY`

这是 Gitea 二进制文件路径。默认是 `$CHATTEA_HOME/bin/gitea`。

如果用户已经通过系统包管理器安装了 Gitea，或者要指定自己下载的 二进制文件，可以改这个变量。`server serve/start/version/init` 都会用到它。

决定：保留。这是部署工具的真实可定制项。

### `CHATTEA_WORK_PATH`

这是 Gitea 的工作目录。Gitea 的仓库数据、SQLite 数据库、session、log 和 `custom/` 目录都在这里。

默认是 `$CHATTEA_HOME/gitea`。用户如果要把仓库和数据库放到更大的磁盘或持久化目录，应该改这个变量。

决定：保留。这是服务数据位置，必须可配置。

### `CHATTEA_CONFIG`

这是 Gitea `app.ini` 配置文件路径，不是旧的 ChatTea JSON 配置文件。默认是 `$CHATTEA_WORK_PATH/custom/conf/app.ini`。

高级用户可能已经有自己的 `app.ini`，或者希望把配置文件放到固定位置。普通用户一般不用改；要看内容用 `chattea server config show`。

决定：保留，但属于高级配置。文档必须明确它写的是 Gitea `app.ini` 路径。

## 不作为正式 Env 的旧字段和参数

### `CHATTEA_URL`

旧版本用它表示 Gitea API base URL。现在它和 `CHATTEA_BASE_URL` 语义重复，而且名字不够清楚。

新版本只做兼容读取：如果旧环境里存在 `CHATTEA_URL`，`load_config()` 可以 回退项 使用。但 `chatenv cat -t chattea` 不再展示它，`set-token` 也不再写它。

决定：不保留为正式 Env。

### `CHATTEA_GITEA_*`

旧草案里出现过 `CHATTEA_GITEA_BASE_URL`、`CHATTEA_GITEA_BINARY`、`CHATTEA_GITEA_WORK_PATH`、`CHATTEA_GITEA_CONFIG` 等字段。

因为包名已经是 ChatTea，语义就是 Gitea 管理工具，Env 再加一层 `GITEA` 会显得绕。新版本优先用短名，旧字段只做兼容读取。

决定：不保留为正式 Env。

### `CHATTEA_GITEA_LISTEN_ADDR` / `CHATTEA_GITEA_HTTP_PORT`

监听地址和端口会写进 Gitea `app.ini` 的 `HTTP_ADDR` 和 `HTTP_PORT`。

它们是初始化/服务配置参数，不是 ChatEnv 需要长期识别的全局变量。需要设置时使用 `chattea server init --listen-addr ... --http-port ...`，需要查看/修改时使用 `chattea server config`。

决定：不保留为正式 Env。

### `CHATTEA_GITEA_DOMAIN`

Gitea `app.ini` 里确实有 `DOMAIN`，但用户不应该同时维护 `BASE_URL` 和 `DOMAIN`。

ChatTea 会从 `CHATTEA_BASE_URL` 或 `server init --base-url` 解析 host，并自动写入 `DOMAIN`。这样可以避免 URL 和 domain 不一致。

决定：不保留。

### `CHATTEA_GITEA_SERVICE_NAME`

这是 用户级 systemd unit 名，例如 `chattea-gitea.service`。它只是本机服务管理的内部名字。

普通用户基本不会改，也几乎不会冲突。未来如果要多实例，应该设计 instance/配置档，而不是提前暴露 service name。

决定：不保留。内部固定使用 `chattea-gitea.service`。

### `CHATTEA_GITEA_VERSION`

Gitea 版本是 `chattea server install --version` 的一次性输入。

它不应该作为长期 Env，否则用户会误以为修改 Env 就能自动升级或降级本地 二进制文件。

决定：不保留。

## Python API（编程接口）

CLI 只是一层薄封装。需要在 Python 中复用时，优先直接调用裸函数或 client：

```python
from chattea.commands.server import install_gitea, init_gitea_server, start_gitea_service
from chattea.commands.server import get_gitea_config_value, set_gitea_config_value
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

binary = install_gitea("1.26.4")
config = init_gitea_server(base_url="http://127.0.0.1:<port>", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()

port = get_gitea_config_value("server", "HTTP_PORT")
set_gitea_config_value("server", "HTTP_PORT", "3001")

client = GiteaClient(url="http://127.0.0.1:<port>", token="...")
repo = create_repository(name="demo", owner="gitea_admin")
clone = clone_repository("gitea_admin/demo")
```

更多接口树见：[interface-tree.md](interface-tree.md)。

## 本地预览

```bash
pip install -e ".[docs]"
mkdocs serve
```

英文版见：[index.en.md](index.en.md)。

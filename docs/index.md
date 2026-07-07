# ChatTea 文档

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包。它负责下载安装到启动本地 Gitea，也提供 token 配置、仓库创建、仓库查看、clone、迁移，以及 Gitea `app.ini` 的查看和小范围编辑。`0.2.1` 起，ChatTea 配置接入 ChatEnv，正式 Env 只保留长期、常用、跨命令共享的配置。

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

`server bootstrap` performs the first local install/init/admin/token/credential workflow. `token bootstrap` creates a Gitea access token through BasicAuth and then configures ChatTea/Git credentials. `issue`, `label`, `milestone`, `pr`, and `release` cover the current repo-level collaboration surface. `project issue` is a compatibility alias for `project card`. New docs and automation should use `project card`. `pr checkout` and Workflow/Runner surfaces are intentionally deferred.

## 新机器配置清单

在一台新机器上，先确认 Python 环境、ChatEnv、ChatTea 和 Gitea runtime 目录都准备好。推荐先用普通用户安装和运行，ChatTea 默认使用 user systemd，不需要 root 级系统服务。

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

### 2. 初始化 ChatEnv profile

ChatTea 的长期配置走 ChatEnv。新机器先创建 active profile，再查看默认值：

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea -I
```

最少需要设置 Gitea 网站/API 地址：

```bash
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
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
chattea server init --base-url http://127.0.0.1:3000 --listen-addr 127.0.0.1 --http-port 3000
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

ChatTea 的 Env 只放长期共享配置。最常用的是 Gitea 网站/API 入口和 API token：

```bash
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
chattea set-token --base-url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
```

如果需要改目录或使用已有 Gitea binary，可以设置高级路径字段：

```bash
python -m chatenv.cli set CHATTEA_HOME=/srv/chattea
python -m chatenv.cli set CHATTEA_BINARY=/usr/local/bin/gitea
python -m chatenv.cli set CHATTEA_WORK_PATH=/srv/gitea
python -m chatenv.cli set CHATTEA_CONFIG=/srv/gitea/custom/conf/app.ini
```

### 3. 下载并初始化 Gitea

```bash
chattea server install
chattea server init
```

`server init` 会生成 Gitea `app.ini`，默认位置来自 `CHATTEA_CONFIG`：

```text
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
```

`listen address` 和 `HTTP port` 是 Gitea app.ini 的内容，不是 ChatEnv。需要改变监听 IP/端口时，作为初始化参数传给 CLI：

本机访问：

```bash
chattea server init \
  --base-url http://127.0.0.1:3000 \
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

开发调试时可以前台启动：

```bash
chattea server serve
```

常驻运行时使用 user systemd：

```bash
chattea server start
chattea server status
chattea server logs --lines 100
chattea server health
```

停止或重启：

```bash
chattea server stop
chattea server restart
```

systemd unit 名固定为 `chattea-gitea.service`。它是内部实现细节，不作为 Env 暴露。

## 自启动和运行维护

ChatTea 使用 user systemd 管理 Gitea。`chattea server start` 会写入 user unit、执行 `systemctl --user daemon-reload`，并 `enable --now` 固定的 `chattea-gitea.service`。

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

有些系统需要管理员权限才能启用 lingering；如果这条命令失败，请让管理员执行或确认机器的 user systemd 策略。启用后可以重启机器，再检查：

```bash
systemctl --user status chattea-gitea.service
chattea server health
```

如果只是临时调试，不需要自启动，可以不用 `server start`，直接前台运行：

```bash
chattea server serve
```

## 更新和升级

更新分成三类：更新 ChatTea 包、更新 Gitea binary、更新 Gitea app.ini。不要把三者混在一起。

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

### 更新 Gitea binary

更新 Gitea 本体时，先停止服务，再覆盖 binary，最后启动并健康检查：

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

这是用户、浏览器和 ChatTea API 访问 Gitea 的完整地址。常见值是 `http://127.0.0.1:3000`、`http://172.25.52.106:3000` 或 `https://git.example.com`。

它会用于 ChatTea API client 的默认 URL，也会在 `server init` 默认值中用于 Gitea `ROOT_URL`。Gitea `DOMAIN` 会从这个 URL 的 host 解析出来。

决定：保留。它是服务身份和 API 入口，是长期共享配置。

### `CHATTEA_TOKEN`

这是 Gitea API token，用于需要认证的仓库命令，例如 `repo list`、`repo create`、`repo view` 和 `repo migrate`。

它是敏感字段。`chatenv cat -t chattea` 默认应该 mask 展示；只有用户显式 `--no-mask` 时才可能明文输出。

决定：保留。这是访问 Gitea API 的必要认证配置。

### `CHATTEA_HOME`

这是 ChatTea 管理本地 Gitea 的根目录。默认值来自 ChatEnv 的 `CHATARCH_HOME`，通常是 `$CHATARCH_HOME/chattea`。

默认的 Gitea binary、work path 和 app.ini 都会从这个目录派生。用户如果要把整个本地管理目录放到别的磁盘，改这个变量最自然。

决定：保留。这是路径总控配置，但属于高级配置。

### `CHATTEA_BINARY`

这是 Gitea 二进制文件路径。默认是 `$CHATTEA_HOME/bin/gitea`。

如果用户已经通过系统包管理器安装了 Gitea，或者要指定自己下载的 binary，可以改这个变量。`server serve/start/version/init` 都会用到它。

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

新版本只做兼容读取：如果旧环境里存在 `CHATTEA_URL`，`load_config()` 可以 fallback 使用。但 `chatenv cat -t chattea` 不再展示它，`set-token` 也不再写它。

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

这是 user systemd unit 名，例如 `chattea-gitea.service`。它只是本机服务管理的内部名字。

普通用户基本不会改，也几乎不会冲突。未来如果要多实例，应该设计 instance/profile，而不是提前暴露 service name。

决定：不保留。内部固定使用 `chattea-gitea.service`。

### `CHATTEA_GITEA_VERSION`

Gitea 版本是 `chattea server install --version` 的一次性输入。

它不应该作为长期 Env，否则用户会误以为修改 Env 就能自动升级或降级本地 binary。

决定：不保留。

## Python API

CLI 只是一层薄封装。需要在 Python 中复用时，优先直接调用裸函数或 client：

```python
from chattea.commands.server import install_gitea, init_gitea_server, start_gitea_service
from chattea.commands.server import get_gitea_config_value, set_gitea_config_value
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

binary = install_gitea("1.26.4")
config = init_gitea_server(base_url="http://127.0.0.1:3000", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()

port = get_gitea_config_value("server", "HTTP_PORT")
set_gitea_config_value("server", "HTTP_PORT", "3001")

client = GiteaClient(url="http://127.0.0.1:3000", token="...")
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

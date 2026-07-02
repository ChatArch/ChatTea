# ChatTea 文档

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包。它负责从下载安装到启动本地 Gitea，也提供 token 配置、仓库创建、仓库查看、clone 和迁移等基础操作。`0.2.0` 起，ChatTea 配置接入 ChatEnv，所有正式配置都在 `ChatTea` 类型下管理。

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

## 从零创建一个本地 Gitea 服务

### 1. 安装 ChatTea 开发环境

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
pip install -e ".[dev,docs]"
python -m pytest -q
```

安装后确认 CLI 可用：

```bash
chattea --help
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli cat -t chattea
python -m chatenv.cli test -t chattea
```

### 2. 配置本地服务地址

本机访问场景：

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=127.0.0.1
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

局域网访问场景：

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=http://172.25.52.106:3000
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=0.0.0.0
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

反向代理场景：

```bash
python -m chatenv.cli set CHATTEA_GITEA_BASE_URL=https://git.example.com
python -m chatenv.cli set CHATTEA_GITEA_LISTEN_ADDR=127.0.0.1
python -m chatenv.cli set CHATTEA_GITEA_HTTP_PORT=3000
```

这三个变量含义不同：`BASE_URL` 是用户和 API 怎么访问 Gitea；`LISTEN_ADDR` 是进程绑定在哪个 IP/host；`HTTP_PORT` 是进程监听哪个端口。

### 3. 下载并初始化 Gitea

```bash
chattea server install --version 1.26.4
chattea server init
```

`server init` 会生成 Gitea `app.ini`，默认位置是：

```text
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
```

如果需要强制交互确认地址和端口，可以使用：

```bash
chattea server init -i
```

如果在 CI 或脚本里禁止交互，可以使用：

```bash
chattea server init -I
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

### 5. 创建 token 并配置 ChatTea

在 Gitea 页面创建 API token 后写入 ChatEnv：

```bash
chattea set-token --base-url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
```

兼容旧命令：

```bash
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
```

`set-token` 会写入 `$CHATARCH_HOME/envs/ChatTea/.env`。CLI 输出会 mask token；实际 env 文件需要保存真实 token。

### 6. 创建和使用仓库

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

### `CHATTEA_GITEA_BASE_URL`

这是用户、浏览器和 ChatTea API 访问 Gitea 的完整地址。常见值是 `http://127.0.0.1:3000`、`http://172.25.52.106:3000` 或 `https://git.example.com`。

它会用于 ChatTea API client 的默认 URL，也会写入 Gitea `app.ini` 的 `ROOT_URL`。Gitea 需要的 `DOMAIN` 会从这个 URL 的 host 解析出来。

决定：保留。这是服务配置里最核心、最用户可理解的入口地址。

### `CHATTEA_GITEA_LISTEN_ADDR`

这是本地 Gitea 进程实际监听的 IP/host。只能写 `127.0.0.1`、`0.0.0.0`、`172.25.52.106` 这类地址，不要写 `http://...`。

`127.0.0.1` 表示只允许本机访问；`0.0.0.0` 表示绑定所有网卡，局域网机器可以访问。它会写入 Gitea `app.ini` 的 `HTTP_ADDR`。

决定：保留。部署服务时绑定地址是真实配置，不应该被 Base URL 偷偷代替。

### `CHATTEA_GITEA_HTTP_PORT`

这是本地 Gitea 进程实际监听的 HTTP 端口。常见值是 `3000`、`3001` 或 `8080`。

它会写入 Gitea `app.ini` 的 `HTTP_PORT`。端口冲突很常见，所以用户需要能明确调整它。

决定：保留。端口是服务运行配置，不是内部细节。

### `CHATTEA_TOKEN`

这是 Gitea API token，用于需要认证的仓库命令，例如 `repo list`、`repo create`、`repo view` 和 `repo migrate`。

它是敏感字段。`chatenv cat -t chattea` 默认应该 mask 展示；只有用户显式 `--no-mask` 时才可能明文输出。

决定：保留。这是访问 Gitea API 的必要认证配置。

### `CHATTEA_HOME`

这是 ChatTea 管理本地 Gitea 的根目录。默认值来自 ChatEnv 的 `CHATARCH_HOME`，通常是 `$CHATARCH_HOME/chattea`。

默认的 Gitea binary、work path 和 app.ini 都会从这个目录派生。用户如果要把整个本地管理目录放到别的磁盘，改这个变量最自然。

决定：保留。这是路径总控配置，但属于高级配置。

### `CHATTEA_GITEA_BINARY`

这是 Gitea 二进制文件路径。默认是 `$CHATTEA_HOME/bin/gitea`。

如果用户已经通过系统包管理器安装了 Gitea，或者要指定自己下载的 binary，可以改这个变量。`server serve/start/version/init` 都会用到它。

决定：保留。这是部署工具的真实可定制项。

### `CHATTEA_GITEA_WORK_PATH`

这是 Gitea 的工作目录。Gitea 的仓库数据、SQLite 数据库、session、log 和 `custom/` 目录都在这里。

默认是 `$CHATTEA_HOME/gitea`。用户如果要把仓库和数据库放到更大的磁盘或持久化目录，应该改这个变量。

决定：保留。这是服务数据位置，必须可配置。

### `CHATTEA_GITEA_CONFIG`

这是 Gitea `app.ini` 配置文件路径，不是 ChatTea 自己的配置文件。默认是 `$CHATTEA_GITEA_WORK_PATH/custom/conf/app.ini`。

高级用户可能已经有自己的 `app.ini`，或者希望把配置文件放到固定位置。普通用户一般不用改。

决定：保留，但属于高级配置。文档必须明确它写的是 Gitea `app.ini` 路径。

## 不作为正式 Env 的旧字段

### `CHATTEA_URL`

旧版本用它表示 Gitea API base URL。现在它和 `CHATTEA_GITEA_BASE_URL` 语义重复，而且名字不够清楚。

新版本只做兼容读取：如果旧环境里存在 `CHATTEA_URL`，`load_config()` 可以 fallback 使用。但 `chatenv cat -t chattea` 不再展示它，`set-token` 也不再写它。

决定：不保留为正式 Env。

### `CHATTEA_GITEA_DOMAIN`

Gitea `app.ini` 里确实有 `DOMAIN`，但用户不应该同时维护 `BASE_URL` 和 `DOMAIN`。

ChatTea 会从 `CHATTEA_GITEA_BASE_URL` 解析 host，并自动写入 `DOMAIN`。这样可以避免 URL 和 domain 不一致。

决定：不保留。

### `CHATTEA_GITEA_SERVICE_NAME`

这是 user systemd unit 名，例如 `chattea-gitea.service`。它只是本机服务管理的内部名字。

普通用户基本不会改，也几乎不会冲突。未来如果要多实例，应该设计 instance/profile，而不是提前暴露 service name。

决定：不保留。内部固定使用 `chattea-gitea.service`。

### `CHATTEA_GITEA_VERSION`

Gitea 版本是 `chattea server install --version` 的一次性输入。

它不应该作为长期 Env，否则用户会误以为修改 Env 就能自动升级或降级本地 binary。

决定：不保留。

### `CHATTEA_CONFIG`

这是旧 JSON 配置文件路径，用于 `~/.config/chattea/config.json` 兼容读取。

新配置已经统一走 ChatEnv，不应该再让用户理解两套配置系统。

决定：不保留为正式 Env，只做 legacy fallback。

## Python API

CLI 只是一层薄封装。需要在 Python 中复用时，优先直接调用裸函数或 client：

```python
from chattea.commands.server import install_gitea, init_gitea_server, start_gitea_service
from chattea.commands.repo import create_repository, clone_repository
from chattea.api import GiteaClient

binary = install_gitea("1.26.4")
config = init_gitea_server(base_url="http://127.0.0.1:3000", listen_addr="127.0.0.1", http_port=3000)
start_gitea_service()

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

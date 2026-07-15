# ChatTea 从零开始快速开始

这篇文档说明如何从空机器启动到一个可用的、由 ChatTea 管理的 ChatArch Gitea 实例。

核心模型分两阶段：

```text
A. 空机器 -> 本地 Gitea 服务、初始管理员、初始令牌
B. token 已配置 -> ChatTea 通过 Gitea REST API 管理仓库、项目、PR、issue、release 和 Actions
```

从零开始路径不要假设已经有 Gitea 服务。已有 Gitea 服务的接入流程是次级路径。

## 命令角色

```text
chattea server bootstrap
  空机器路径：安装、初始化并启动本地 ChatArch Gitea，创建初始管理员，生成初始令牌，配置 ChatTea，并验证 API。

chattea token bootstrap
  已有 Gitea 路径：给定已有 Gitea 服务和用户名密码，通过 REST 创建 访问令牌，然后配置 ChatTea。

chattea set-token
  已有 token 路径：给定已经创建好的 token，把它保存到 ChatTea/ChatEnv，并按需配置 repo-local git config。
```

`0.2.3` 的当前实现状态：

```text
已实现：
  chattea set-token
  chattea token create/list/delete/bootstrap
  chattea server bootstrap
  集中的 令牌解析
  runner/run/job/artifact Actions 能力面

server bootstrap 状态：
  本地 install/init/admin/token/credential 链路已实现
  service start 可通过 --start-service 选择启用
  重跑加固：如果本地管理员 token 名已存在，会复用当前已配置 token
```

## 服务端和客户端边界

ChatTea 在完整流程里有两个角色：

```text
服务端
  运行托管 ChatArch Gitea 服务的机器。
  它拥有 Gitea binary、app.ini、database、repositories、logs、初始管理员和生成的 访问令牌。

客户端
  任何想通过 ChatTea 管理该 Gitea 服务的机器。
  它不需要 Gitea binary 或 app.ini，只需要 ChatTea、base URL 和 访问令牌。
```

从零开始的 引导 是服务端动作：

```text
chattea server bootstrap
  在服务机器上运行。
  创建本地 Gitea 服务、初始管理员和初始 访问令牌。
  把生成的 token 写入服务机器的 ChatEnv profile。
```

已有 令牌 后，客户端配置才开始：

```text
chattea set-token
  在已有 token 的客户端机器上运行。
  把 CHATTEA_BASE_URL 和 CHATTEA_TOKEN 写入该客户端的 ChatEnv profile。

chattea token bootstrap
  在已有 Gitea 服务和用户名密码的客户端机器上运行。
  使用 BasicAuth 通过 REST 创建 token，然后写入该客户端的 ChatEnv profile。
```

这意味着空白服务器一开始不是客户端。它先用 `server bootstrap` 在本机把服务拉起来。之后同一台机器也可以作为客户端，因为它已经配置了 `CHATTEA_BASE_URL` 和 `CHATTEA_TOKEN`。其它开发机或 CI 机器可以通过 `set-token` 或 `token bootstrap` 指向该服务 URL。

第一阶段只管理一个目标 Gitea 实例：

```text
当前范围：
  一个 server-side Gitea 实例。
  每台机器 / 每个 profile 一个 active client target。
  同机 server+client，以及远程 client 到 server 的流程。

暂不纳入：
  一个 active ChatTea profile 同时管理多个 Gitea 实例。
  实例切换 UX。
  多服务命名和生命周期隔离。
```

## A. 空机器到本地 Gitea

目标是一条命令完成主要链路：

```bash
export GITEA_ADMIN_PASSWORD='***'

chattea server bootstrap \
  --base-url http://127.0.0.1:<port> \
  --admin-user gitea_admin \
  --admin-email admin@example.com \
  --admin-password-env GITEA_ADMIN_PASSWORD
```

`server bootstrap` 应组合下面这些步骤。

### A1. 安装 ChatArch Gitea

对应 ChatTea 本地安装逻辑：

```text
chattea server install
```

预期行为：

```text
下载最新 ChatArch internal Gitea release
校验 .sha256 checksum
安装 binary 到 CHATTEA_HOME/bin/gitea
```

默认路径来自 ChatEnv 或内置默认值：

```text
CHATTEA_HOME      -> ~/.chatarch/chattea
CHATTEA_BINARY    -> ~/.chatarch/chattea/bin/gitea
```

### A2. 创建 app.ini

对应命令：

```text
chattea server init
```

预期输出文件：

```text
CHATTEA_CONFIG
```

默认路径：

```text
~/.chatarch/chattea/gitea/custom/conf/app.ini
```

重要配置默认值：

```text
[server]
ROOT_URL = http://127.0.0.1:<port>/
HTTP_ADDR = 127.0.0.1
HTTP_PORT = 3000

[database]
DB_TYPE = sqlite3

[security]
INSTALL_LOCK = true

[service]
DISABLE_REGISTRATION = true
REGISTER_EMAIL_CONFIRM = false
```

默认关闭注册。初始管理员由本地 Gitea admin CLI 创建，不依赖开放注册。

### A3. 初始化数据库

使用本地 Gitea 二进制文件：

```text
gitea migrate --config app.ini --work-path ...
```

这个步骤不需要已有账号或 令牌。

### A4. 创建初始管理员

这一步解决 chicken-and-egg 问题。

第一个管理员不能通过普通 REST API 创建，因为 REST admin API 需要已有管理员鉴权。因此从零开始路径必须使用本地 Gitea admin CLI：

```bash
gitea admin user create \
  --config app.ini \
  --work-path ... \
  --username gitea_admin \
  --password '***' \
  --email admin@example.com \
  --admin \
  --must-change-password=false
```

在 ChatTea 中，密码应来自：

```text
--admin-password-env GITEA_ADMIN_PASSWORD
```

密码可以来自 `--admin-password-env`，也可以来自敏感的 `CHATTEA_BOOTSTRAP_ADMIN_PASSWORD` ChatEnv 字段。CLI 输出不得打印密码。

### A5. 生成初始访问令牌

第一个 令牌 也应通过本地 Gitea admin CLI 生成：

```bash
gitea admin user generate-access-token \
  --config app.ini \
  --work-path ... \
  --username gitea_admin \
  --token-name default \
  --scopes all \
  --raw
```

初始 引导 默认使用 Gitea 内置的最大 scope：

```text
all
```

默认 令牌名：

```text
default
```

完整链路稳定后，可以再收紧 scope。

如果重跑时发现同名本地管理员 令牌 已存在，`server bootstrap` 会复用同一 base URL 下当前已配置的 `CHATTEA_TOKEN`，而不是重新打印或要求输入 原始令牌。如果没有匹配的已配置 令牌，则给出清晰错误，要求使用不同的 `--token-name` 或用现有 令牌 运行 `chattea set-token`。

### A6. 配置 ChatTea 凭据

这一步就是 `set-token`。

概念上等价于：

```bash
chattea set-token \
  --base-url http://127.0.0.1:<port> \
  --token '***'
```

实现上，`server bootstrap` 应直接调用同一套 Python 凭据函数，而不是 通过 shell 调用。

### A7. 启动和验证

使用受支持的本地模式启动 Gitea：

```text
Linux 上使用 user-level systemd 的 server start
或本地真实验证使用 server serve / 托管前台进程
```

然后验证：

```text
GET /api/v1/version
GET /api/v1/user
```

`/version` 证明服务可达；`/user` 证明生成的 令牌 有效。

## B. 令牌配置之后

完成 `set-token` 或 `server bootstrap` 后，后续命令不应再使用用户名密码，而应使用已配置 令牌。

示例：

```bash
chattea repo list
chattea repo create --name demo
chattea project list --repo gitea_admin/demo
chattea api /user
```

令牌解析顺序：

```text
1. 显式 CLI token 参数
2. 当前 repo-local git config
3. ChatTea ChatEnv active profile
4. 如果命令需要鉴权但没有 token，则清晰失败
```

## set-token 与 ChatEnv 的关系

`set-token` 和 ChatEnv 是连接在一起的，不是两套互不相关的配置系统。

当前 ChatTea 流程：

```text
chattea set-token
  -> chattea.commands.auth.configure_token
  -> chattea.credentials.configure_token
  -> chattea.config.set_token / save_config
  -> chatenv EnvStore active ChatTea profile
```

因此，长期 ChatTea 配置通过 ChatEnv 字段保存：

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

当 `set-token` 能识别当前 Gitea git 远端 时，它还会配置 仓库本地 git 鉴权：

```text
git config --local http.<gitea-repo-url>.extraHeader "Authorization: Basic ..."
```

这部分 git config 只是 git transport 的便利配置，不取代 ChatEnv。

总结：

```text
ChatEnv 保存稳定的 ChatTea 配置。
set-token 写入 ChatEnv，并按需写入 repo-local git config。
repo-local git config 帮助 git pull/push。
Gitea API 命令通过统一 令牌解析 路径读取 token。
```

## 不应写入 ChatEnv 的内容

不要把这些作为稳定 ChatEnv 字段：

```text
admin password
one-time bootstrap password
repo id
project id
issue id
runner id
default admin token raw output before set-token
```

管理员密码只是 引导 输入。访问令牌 只有写入 `CHATTEA_TOKEN` 后才成为长期配置。

## 已有远程 Gitea 流程

如果 Gitea 服务和用户已经存在，使用：

```bash
export GITEA_PASSWORD='***'

chattea token bootstrap \
  --base-url https://gitea.example.com \
  --username gitea_admin \
  --password-env GITEA_PASSWORD
```

默认情况下，`token bootstrap` 对托管 令牌名 可重跑。如果 `default` 已存在，它会删除该 同名令牌，再创建新 令牌，然后调用 `set-token`。如果要阻止轮换，使用 `--if-exists error`。

这个流程使用 Gitea REST API：

```text
POST /api/v1/users/{username}/tokens
```

随后调用与 `set-token` 相同的 credential path。

这不是空机器路径，而是已有 Gitea 路径。

## 已有令牌流程

如果用户已经在 Gitea Web UI 中创建了 令牌：

```bash
chattea set-token \
  --base-url https://gitea.example.com \
  --token '***'
```

这是最短路径，但前提是 令牌 已经存在。

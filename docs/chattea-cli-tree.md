# ChatTea CLI 能力地图

这篇文档是当前 ChatTea CLI 的简明能力地图，用来校对哪些 Gitea 流程已经有一等 ChatTea 命令，哪些流程还需要 `chattea api`。

可导入 Python 函数映射见 [接口树](interface-tree.md)。更完整的路由映射和实践截图见 [CLI 指南](cli-guide.md)。官方 `tea` CLI 与 ChatTea 覆盖范围对比见 [官方 tea CLI 对比](tea-cli-comparison.md)。

## 顶层命令

```text
chattea
├── api                 # 调用尚未被一等封装的原始 Gitea API
├── artifact            # 查看、下载、删除 Gitea Actions 产物
├── auth                # 配置和检查 ChatTea base URL / token
├── bot                 # 管理本机 Gitea bot / 服务账号和 token
├── issue               # 管理仓库问题、评论、标签和负责人
├── job                 # 查看、读取日志或重跑 Gitea Actions job
├── label               # 管理仓库标签
├── milestone           # 管理仓库里程碑
├── notification        # 轮询和标记当前用户的通知线程
├── org                 # 管理组织、团队和团队成员
├── pr                  # 管理合并请求、评论、review、diff/patch 和合并
├── project             # 管理 Gitea 仓库项目看板、列和卡片
├── release             # 管理仓库发布版本和发布附件
├── repo                # 创建、查看、列出、clone 和迁移仓库
├── run                 # 查看或控制 Gitea Actions workflow run
├── runner              # 管理 Gitea Actions 运行器和注册令牌
├── server              # 安装、初始化、启动和检查本机托管的 Gitea 服务
├── set-token           # 配置 ChatTea API token 和仓库本地 git 鉴权
├── token               # 创建、列出、删除和引导配置 Gitea access token
└── user                # 管理员创建和删除 Gitea 用户
```

## CLI backend 分层

ChatTea CLI 需要同时覆盖两类能力：一类是 Gitea 已经提供的 REST API，另一类是只有部署机器本地才具备的能力，例如 `gitea dump`、`app.ini`、systemd、runner root、native bot admin CLI、Pages publish 目录等。

因此当前命令可以按 backend 分成三类：

| Backend | 执行位置 | 典型命令 | 说明 |
| --- | --- | --- | --- |
| `gitea-rest` | 任意能访问 Gitea API 的机器 | `repo`、`issue`、`pr`、`release`、`run`、`job` | 只调用 Gitea REST API |
| `local` | 当前执行 CLI 的机器 | `server`、`server backup`、`bot`、`runner local` | 需要本机 binary、文件、systemd 或 admin CLI |
| `hybrid` | 当前机器 + Gitea API | `auth`、`set-token`、`repo clone`、`artifact download`、`runner local register` | 既调远端 API，也修改当前机器状态 |

目标不是让用户记住两套命令，而是保持同一套 CLI 语义，只让 backend 决定在哪里执行：

```text
chattea <command> ... --backend local
chattea <command> ... --backend service --endpoint <entry-url>
```

`local` backend 直接在当前机器执行；`service` backend 通过 ChatTea control service 的二级接口，把请求发送到托管 Gitea 的机器执行。这样备份、server 管理、bot 创建、Pages publish 等原本只能本机操作的命令，可以在远端控制机上用同样的 CLI 形态发起。

目标形态：

```text
目标机器：chattea local serve --listen 127.0.0.1:<control-port>
客户端：  chattea <command> ... --backend service --endpoint https://<entry-host>/control/
```

二级接口不是替代 Gitea REST API。它只包装 Gitea REST API 没有覆盖、但 ChatTea 运行时需要的本地能力：

```text
CLI command
  -> backend resolver
  -> gitea-rest backend    -> Gitea /api/v1
  -> local backend         -> current machine files / systemd / binaries
  -> service backend       -> /control/v1/jobs -> remote local backend
```

第一版建议只把明确需要本地权限、且可以审计为 job 的能力放进 `service` backend。纯 Gitea 对象继续直连 Gitea REST API，不绕 control service。

## REST API、Local 和 Hybrid 命令清单

### 走 Gitea REST API 的命令

这些命令主要操作 Gitea 业务对象，只要有 base URL 和 token，就可以从远端执行：

```text
chattea api
chattea repo list/view/create/edit/generate/migrate
chattea issue ...
chattea pr ...
chattea label ...
chattea milestone ...
chattea release ...
chattea project ...
chattea org list/view/create/team/...
chattea user create/delete
chattea notification list/view/mark-read/poll
chattea runner registry ...
chattea run list/view/jobs/logs/rerun/rerun-failed/delete
chattea job view/logs/rerun
chattea artifact list/view/delete
```

`user create/delete` 是 admin API，不是本机 admin CLI；它能创建普通 user，但不能完整表达 native bot user。

### 必须本地执行的命令

这些命令需要访问部署机器或 runner 机器上的本地资源：

```text
chattea server install/init/bootstrap/serve
chattea server start/stop/restart/status/logs/health/version
chattea server config path/show/get/set
chattea server backup dump
chattea server migrate mysql

chattea bot plan/create/delete/token create

chattea runner local install/create/register/list/view/start/stop/restart/status/logs/doctor/remove/config/...
chattea runner pool create/start/stop/status/remove
```

原因分别是：

| 能力 | 本地依赖 |
| --- | --- |
| server install/init | Gitea binary、work path、`app.ini`、数据库初始化 |
| server start/logs | user systemd、journalctl、本机 service name |
| server backup dump | `gitea dump`、repo data、attachments、database、checksums |
| server migrate mysql | 本机 SQLite、ChatData/MySQL runtime、维护窗口 |
| bot create/token | `gitea admin user create --user-type bot`、`generate-access-token` |
| runner local/pool | runner binary、`.runner`、`config.yaml`、runner workdir、systemd |

这些能力是二级接口服务化的主要候选。

### Hybrid 命令

这些命令既调用 Gitea API，也修改当前执行机器的本地状态：

```text
chattea auth login/status/token
chattea set-token
chattea token bootstrap
chattea repo clone
chattea artifact download
chattea runner local register
chattea runner workflow labels/example/check
```

其中 `runner local register` 会向 Gitea 注册 runner，同时写本机 runner root 和 config；`artifact download` 调 API，但结果写到当前文件系统。

## 本地能力服务化：二级接口

服务化目标是把 local backend 抽象成可远程触发的 job，而不是为每个能力重新设计一套 CLI。用户面对的一级命令保持一致，二级接口只负责选择执行后端：

```text
chattea backup create --backend local
chattea backup create --backend service --endpoint https://<entry-host>

chattea bot create --username chattea-pages-bot --backend local
chattea bot create --username chattea-pages-bot --backend service --endpoint https://<entry-host>

chattea pages publish --repo <owner>/<repo> --source site/ --backend local
chattea pages publish --repo <owner>/<repo> --source site/ --backend service --endpoint https://<entry-host>
```

`--backend service` 的内部流程：

```text
CLI
  -> POST /control/v1/jobs
  -> ChatTea control service validates auth / allowlist / confirmation headers
  -> server-side local backend executes the same operation
  -> job writes logs, manifest, result JSON
  -> CLI polls /control/v1/jobs/<id>
  -> CLI renders the same final output shape as local backend
```

这样可以把 backup 和其它本地能力统一起来：backup 不再是特殊的一套服务，而是 local capability service 的一个 job type。

### 建议优先服务化的 local jobs

| Job type | 对应 CLI | 说明 |
| --- | --- | --- |
| `backup.create` | `chattea backup create` / 当前 `server backup dump` | 完整实例备份、DB-only 导出、manifest、checksum |
| `backup.list/status/logs/download` | `chattea backup ...` | 读取 manifest 和 job 结果，适合 Web UI / Bot 展示 |
| `pages.publish` | `chattea pages publish` | Actions 或远端 CLI 把构建产物交给服务器发布 |
| `server.status/logs` | `chattea server status/logs --backend service` | 远程看服务状态和日志摘要 |
| `server.restart` | `chattea server restart --backend service` | 需要显式确认和审计 |
| `bot.create/token` | `chattea bot create/token ... --backend service` | 远程创建 native bot user 和 scoped token，token 只显示一次 |
| `runner.local.status/logs` | `chattea runner local status/logs --backend service` | 查看部署机上的 runner 状态 |

### 第一版不建议直接开放的 service jobs

| Job type | 原因 |
| --- | --- |
| `restore.apply` | 恢复会覆盖数据，必须维护窗口、本地确认、完整性校验 |
| 任意 `server config set` | 容易远程写坏 `app.ini`，应先限制到 allowlist key |
| 任意 shell command | 不可审计、权限边界过大 |
| 删除 runner root / backup purge | 需要二次确认和保留期策略 |

原则：service backend 只能暴露 allowlist job，不提供通用远程 shell。

## 原始 API

```text
chattea api PATH        # 调用指定 Gitea API 路径
├── --method METHOD     # 指定 HTTP 方法，默认 GET
├── --data JSON         # 传入 JSON request body
└── --param KEY=VALUE   # 传入 query 参数
```

当前仍保留 `chattea api` 作为兜底能力；一旦某条真实流程反复依赖某个 API，就提升成一等命令。组织任务账号实践中，`POST /orgs`、`POST /admin/users`、`POST /orgs/{org}/teams`、`PUT /teams/{id}/members/{username}` 和 `/notifications` 已经提升为 `user`、`org`、`notification` 命令。

## 认证和令牌

```text
chattea auth            # 管理当前 ChatTea 认证状态
├── login               # 写入 ChatTea base URL / token，并尝试配置仓库本地 git 鉴权
├── status              # 显示当前 base URL 和脱敏 token 状态
└── token               # 显示脱敏 token，便于确认当前配置

chattea set-token       # 配置已有 token；常在 git 仓库内配置 extraHeader

chattea token           # 管理 Gitea access token 生命周期
├── bootstrap           # 创建 token，然后配置 ChatTea/Git 凭据
├── create              # 用用户名密码 BasicAuth 创建 access token
├── delete              # 按 id 或 name 删除 access token
└── list                # 用用户名密码 BasicAuth 列出 access token
```

实践校对点：`chattea set-token` 会同时写入远端 URL 带 `.git` 和不带 `.git` 两种 `extraHeader` key，避免 git remote 与 `http.<url>.extraHeader` key 不一致导致 `git push` 不带鉴权 header。

## 用户、组织和通知

```text
chattea user            # 管理员管理 Gitea 用户
├── create              # 通过 admin API 创建用户，支持 private visibility
└── delete              # 通过 admin API 删除用户

chattea org             # 管理组织和团队
├── create              # 创建组织，默认 private visibility
├── list                # 列出组织
├── view                # 查看组织
└── team                # 管理组织团队
    ├── create          # 创建 team，默认 write + all repos + 常用 repo units
    ├── list            # 列出组织团队
    └── member          # 管理 team 成员
        ├── add         # 把用户加入 team
        └── remove      # 从 team 移除用户

chattea notification    # 当前 token 对应用户的通知线程
├── list                # 列出 notifications
├── poll                # 轮询 unread issue/pull notifications
├── view                # 查看 notification thread
└── mark-read           # 标记 thread 为 read/unread/pinned
```

这些命令是从组织任务账号实践中补出来的最小 Infra：先支持创建 private 组织和普通任务账号，再通过 notification 轮询实现 `@任务账号` 的触发入口。

## 机器人账号与服务账号

```text
chattea bot             # 管理本机 Gitea bot / 服务账号
├── plan                # 检查本机 Gitea binary 是否支持 bot create / token generate / delete
├── create              # 创建 Gitea UserTypeBot，可同时生成 scoped token
├── delete              # 删除本机 bot / 用户；临时实践账号可配合 --purge 清理
└── token               # 管理本机 bot token
    └── create          # 给已存在 bot 生成 scoped token
```

`bot` 第一版只承诺本机托管 Gitea 的 local backend：通过 `gitea admin user create --user-type bot` 和 `gitea admin user generate-access-token --raw` 工作。稳定 REST API 还不能完整创建和识别 `UserTypeBot`，所以远程 API-only 场景暂不声称是真 bot。`@bot` 唤醒机制、主要用途和真实截图见 [机器人账号与服务账号](bot-service-account-plan.md)。

## 仓库

```text
chattea repo            # 管理 Gitea 仓库
├── clone               # 从配置的 Gitea base URL clone 仓库
├── create              # 创建用户或组织仓库；支持 --template 创建模板仓库
├── edit                # 修改仓库元数据、public/private、archive 和 template 状态
├── generate            # 从 template repository 生成新仓库
├── list                # 列出当前用户或指定 owner 的仓库
├── migrate             # 从已有 Git URL 迁移仓库到 Gitea
└── view                # 查看 owner/name 仓库详情
```

权限相关行为：

- `repo create --public` 创建 public 仓库；
- `repo create --private` 显式创建 private 仓库；
- 不传 `--public` / `--private` 时仍默认创建 private 仓库；
- `repo create --template` 创建模板仓库；
- `repo edit OWNER/NAME --template` / `--no-template` 可切换已有仓库的模板状态；
- `repo generate --template OWNER/TEMPLATE --owner TARGET --name NAME --copy-git-content` 可从模板生成新仓库，且至少需要选择一个 `--copy-*` 项；
- 当前普通仓库 create/edit 流程没有暴露仓库级 `internal` visibility 输入。

## 问题

```text
chattea issue           # 管理仓库问题
├── create              # 创建问题
├── list                # 按 open/closed/all 列问题
├── view                # 查看问题详情
├── edit                # 修改标题、正文、状态、标签、里程碑或负责人
├── close               # 关闭问题
├── reopen              # 重开问题
├── delete              # 删除问题，需要确认
├── comment             # 管理问题评论
│   ├── create          # 添加问题评论
│   ├── list            # 列出问题评论
│   ├── edit            # 编辑问题评论
│   └── delete          # 删除问题评论，需要确认
├── label               # 管理问题标签绑定
│   ├── add             # 给问题添加标签 id
│   └── remove          # 从问题移除标签 id
└── assign              # 管理问题负责人
    ├── add             # 添加问题负责人
    └── remove          # 移除问题负责人
```

当前端到端快速开始已覆盖 create、view、评论 create/list/edit、close、reopen、按状态 list。

## 合并请求

```text
chattea pr              # 管理 Gitea pull request
├── create              # 从 head 分支向 base 分支创建 PR
├── list                # 按 open/closed/all 列 PR
├── view                # 查看 PR 详情
├── edit                # 修改 PR 标题、正文、状态或 base
├── close               # 关闭 PR
├── reopen              # 重开 PR
├── merge               # 用 merge/rebase/squash/fast-forward 等方式合并 PR
├── diff                # 输出 PR diff
├── patch               # 输出 PR patch
├── commits             # 列出 PR commits
├── files               # 列出 PR 变更文件
├── comment             # 管理 PR 的 issue-comment
│   ├── create          # 添加 PR 评论
│   └── list            # 列出 PR 评论
└── review              # 管理 PR review
    ├── create          # 创建 PR review event
    ├── list            # 列出 PR reviews
    └── submit          # 提交已有 pending review
```

当前端到端快速开始已覆盖 create、view、files、commits、评论、review、close、reopen、merge。

## 标签和里程碑

```text
chattea label           # 管理仓库标签
├── create              # 创建标签
├── list                # 列出标签
├── view                # 查看标签详情
├── edit                # 修改标签名称、颜色或描述
└── delete              # 删除标签

chattea milestone       # 管理仓库里程碑
├── create              # 创建里程碑
├── list                # 列出里程碑
├── view                # 查看里程碑详情
├── edit                # 修改里程碑
├── close               # 关闭里程碑
└── delete              # 删除里程碑
```

这些命令配合问题 / PR 的标签 ID 和里程碑 ID 使用。

## 项目看板

```text
chattea project         # 管理仓库级 Gitea Project 看板
├── create              # 创建项目看板
├── list                # 列出仓库项目看板
├── view                # 查看项目看板详情
├── edit                # 编辑项目看板
├── delete              # 删除项目看板
├── column              # 管理项目看板列
│   ├── create          # 创建项目列
│   ├── list            # 列出项目列
│   ├── edit            # 编辑项目列
│   └── delete          # 删除项目列
├── card                # 管理问题 / PR 卡片
│   ├── add             # 把问题或 PR 加入列
│   ├── list            # 列出列中的卡片
│   ├── move            # 移动卡片到另一列或排序位置
│   └── remove          # 从列中移除卡片
└── issue               # `project card` 的兼容别名
```

新文档和新自动化优先使用 `project card`。`project issue` 只保留为兼容别名。

## 发布版本

```text
chattea release         # 管理仓库发布版本
├── create              # 创建发布版本
├── list                # 列出发布版本
├── view                # 查看发布版本详情
├── latest              # 查看最新发布版本
├── by-tag              # 按 tag 查看发布版本
├── edit                # 编辑发布版本
├── delete              # 删除发布版本
└── asset               # 管理发布附件
    ├── list            # 列出发布附件
    └── delete          # 删除发布附件
```

发布附件上传暂不作为一等命令，等 HTTP client 支持 multipart upload 后再补。

## Actions：运行、任务、产物和运行器

```text
chattea run             # 管理 Gitea Actions workflow run
├── list                # 列出 run
├── view                # 查看 run 详情
├── jobs                # 列出 run 下的 jobs
├── logs                # 汇总 run 下的 job logs
├── rerun               # 重跑 run
├── rerun-failed        # 只重跑失败 jobs
└── delete              # 删除 run

chattea job             # 管理 Gitea Actions job
├── view                # 查看 job 详情
├── logs                # 读取 job 日志
└── rerun               # 重跑 job

chattea artifact        # 管理 Gitea Actions 产物
├── list                # 列出产物
├── view                # 查看产物详情
├── download            # 下载产物 zip
└── delete              # 删除产物

chattea runner                    # 管理 Gitea Actions 运行器
├── registry                      # 管理 Gitea 服务器侧 runner 记录
│   ├── token                     # 获取 repo/user/org/admin 注册令牌
│   ├── list                      # 按 scope 列出 runner
│   ├── view                      # 查看 runner 详情
│   ├── enable                    # 启用 runner
│   ├── disable                   # 禁用 runner
│   └── delete                    # 删除 runner 记录
├── local                         # 管理本机 runner 实例
│   ├── install                   # 安装或复制 gitea-runner binary
│   ├── create                    # 创建 runner root 和 config，不注册
│   ├── register                  # 创建本机 root/config 并注册到 Gitea
│   ├── list                      # 列出本机已管理 runner instances
│   ├── view                      # 查看本机 runner root/config/service 摘要
│   ├── start                     # 启动 chattea-runner@name.service
│   ├── stop                      # 停止 runner service
│   ├── restart                   # 重启 runner service
│   ├── status                    # 查看 systemd user service 状态
│   ├── logs                      # 查看 runner service 日志
│   ├── doctor                    # 检查 binary/config/.runner/workdir
│   ├── config                    # 修改 runner config.yaml
│   │   ├── show                  # 显示 labels/capacity/workdir/backend 摘要
│   │   ├── set-labels            # 更新 labels
│   │   ├── set-capacity          # 更新 capacity
│   │   ├── set-workdir           # 更新 host workdir_parent
│   │   └── set-backend           # 更新 label backend 后缀
│   └── remove                    # disable service 并删除本机 runner root
├── pool                          # 批量管理同机多个 runner
│   ├── create                    # 创建或注册 N 个 runner
│   ├── start                     # 启动 pool 内所有 runner
│   ├── stop                      # 停止 pool 内所有 runner
│   ├── status                    # 查看 pool 摘要
│   └── remove                    # 删除 pool 内本机 runner
└── workflow                      # workflow 与 runner label 辅助
    ├── labels                    # 列出当前 scope 可用于 runs-on 的 labels
    ├── example                   # 输出 runs-on 示例
    └── check                     # 检查 workflow runs-on 是否有匹配 runner
```

这些命令覆盖第一版 Gitea Actions 面：运行器生命周期、PR 触发的 run、job、log 和产物。Runner 运行环境、注册、多实例维护和并发结论见 [Runner 运行环境与多实例](runner-environment-and-registration.md)，Actions / Runner 的端到端流程见 [Actions / Flow（动作 / 流程）快速开始](actions-flow-quickstart.md)。

## 服务

```text
chattea server          # 管理本机托管的 Gitea 服务
├── backup              # 运行 Gitea dump，支持完整备份和 DB-only SQL 导出
├── bootstrap           # 串起 install/init/admin/token/credential，可选择 sqlite3/mysql
├── install             # 下载 ChatArch Gitea 二进制文件，可选准备 MySQL infra
├── init                # 创建最小 app.ini，可选择 sqlite3/mysql 后端，可跳过 gitea migrate
├── start               # 安装并启动用户级 systemd 服务，可指定 service name
├── stop                # 停止用户级 systemd 服务，可指定 service name
├── restart             # 重启用户级 systemd 服务，可指定 service name
├── status              # 查看用户级 systemd 服务状态
├── logs                # 查看服务日志
├── health              # 检查 Gitea API 是否可达
├── config              # 查看或编辑托管 app.ini
├── migrate             # 迁移托管 Gitea backend；当前支持 mysql
├── version             # 查看二进制文件或 server 版本
└── serve               # 前台运行 Gitea，用于调试和本地实践
```

Gitea 服务默认由 `chattea-gitea.service` 管理；side-by-side 迁移或 shadow 实例可以通过 `--service-name` 使用独立 service。运行器由 `chattea-runner@<runner-name>.service` 管理。新装实例默认仍使用 SQLite；需要 MySQL 时可以在 `server install`、`server init` 或 `server bootstrap` 加 `--database-backend mysql`，ChatTea 会通过 ChatData 准备本机 MySQL 二进制 runtime 和 user systemd service。

Pages 静态站点发布规划为本地 backend 能力，不是 Gitea REST API 命令。目标是用 `chattea pages service ...` 管理第二个 Web 服务，用 `chattea pages publish` 让 Actions job 直接发布到 `<chattea-home>/pages/sites/<owner>/<repo>/`；机制见 [Gitea Pages 机制与静态站点发布](gitea-pages.md)，文件边界见 [ChatTea 运行时文件系统与服务边界](runtime-filesystem-layout.md)。

## 当前封装边界和后续项

组织任务账号实践暴露出的 `org`、`user`、`team member` 和 `notification` 基础命令已经补成一等 CLI：

- `chattea user create/delete`：管理员创建和删除普通用户；
- `chattea org create/list/view`：创建、列出和查看组织；
- `chattea org team create/list`：创建和列出组织 team；
- `chattea org team member add/remove`：维护 team 成员；
- `chattea notification list/view/poll/mark-read`：支撑 mention 驱动的任务账号轮询。

目前仍保留为后续项或 raw API 兜底的部分：

- `user list/view/edit`：当前只封装了实践必须的 admin create/delete；
- team 的编辑、删除、仓库绑定调整：当前只封装 create/list/member add/remove；
- 通过 admin create-as-user 路径创建 user-owned 仓库：尚未作为第一版受管仓库模型的主路径；
- GitHub Enterprise 风格的 `internal` 仓库可见性：当前普通 Gitea create/edit 路径没有作为稳定输入暴露；
- release asset 上传：当前有 asset list/delete，上传等 HTTP client 支持 multipart 后再补；
- Pages 静态站点发布：当前 Gitea 实例没有官方 Pages REST 路由；计划作为 ChatTea local backend 实现 `pages service/publish/status/workflow`，默认 path URL 为 `<pages-domain>/<owner>/<repo>/`，resolver/custom domain 不在 v0.1；
- bot / service account 的远程 REST backend：Gitea 底层和本机 admin CLI 已支持 bot 用户类型，但稳定 REST API 尚未完整暴露；当前 `bot` 命令只承诺本机 local backend。

原则：真实流程反复依赖某条 raw API 时，再提升成一等命令；补完后同步更新本页和快速开始。

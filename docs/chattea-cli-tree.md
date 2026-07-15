# ChatTea CLI 能力地图

这篇文档是当前 ChatTea CLI 的简明能力地图，用来校对哪些 Gitea 流程已经有一等 ChatTea 命令，哪些流程还需要 `chattea api`。

可导入 Python 函数映射见 [接口树](interface-tree.md)。更完整的 路由 mapping 和实践截图见 [CLI 实战指南](cli-guide.md)。

## 顶层命令

```text
chattea
├── api                 # 调用尚未被 ChatTea 封装的原始 Gitea API
├── artifact            # 查看、下载、删除 Gitea Actions artifact
├── auth                # 配置和检查 ChatTea base URL / token
├── issue               # 管理仓库 issue、评论、label、assignee
├── job                 # 查看或重跑 Gitea Actions job
├── label               # 管理仓库 label
├── milestone           # 管理仓库 milestone
├── pr                  # 管理 PR、PR 评论、review、diff/patch、合并
├── project             # 管理 Gitea repo project board、column、issue/PR card
├── release             # 管理仓库 release 和 release asset
├── repo                # 创建、查看、列出、clone、migrate 仓库
├── run                 # 查看或控制 Gitea Actions workflow run
├── runner              # 管理 Gitea Actions runner 和 registration token
├── server              # 安装、初始化、启动、检查本机托管的 Gitea 服务
├── set-token           # 配置 ChatTea API token 和 repo-local git auth
└── token               # 创建、列出、删除、bootstrap Gitea access token
```

## 原始 API

```text
chattea api PATH
  --method GET|POST|PUT|PATCH|DELETE
  --data JSON
  --param KEY=VALUE
```

当前实践中用 raw API 覆盖的部分：

- `POST /orgs`：创建组织；
- `POST /admin/users`：创建用户；
- `GET /orgs/{org}/teams`：查看组织 teams；
- `PUT /teams/{id}/members/{username}`：把用户加入 team。

这些是后续一等 ChatTea 封装的候选项。只有当实践流程继续依赖它们时，再补对应基础设施。

## 认证和令牌

```text
chattea auth
├── login               # 写入 ChatTea base URL / token，并尝试配置 repo-local git auth
├── status              # 显示当前 base URL 和 masked token 状态
└── token               # 显示 masked token 便于确认

chattea set-token       # login 的旧入口/快捷入口，常在 git repo 内配置 extraHeader

chattea token
├── bootstrap           # 创建 token，然后配置 ChatTea/Git credentials
├── create              # 用用户名密码 BasicAuth 创建 access token
├── delete              # 按 id 或 name 删除 access token
└── list                # 用用户名密码 BasicAuth 列出 access token
```

实践校对点：`chattea set-token` 会同时写入 远端 URL 带 `.git` 和不带 `.git` 两种 `extraHeader` key，避免 git 远端 与 `http.<url>.extraHeader` key 不一致导致 `git push` 不带鉴权 header。

## 仓库

```text
chattea repo
├── clone               # 从配置的 Gitea base URL clone 仓库
├── create              # 创建用户或组织仓库
├── list                # 列出当前用户或指定 owner 的仓库
├── migrate             # 从已有 Git URL 迁移仓库到 Gitea
└── view                # 查看 owner/name 仓库详情
```

权限相关行为：

- `repo create --public` 创建 public 仓库；
- `repo create --private` 显式创建 private 仓库；
- 不传 `--public` / `--private` 时仍默认创建 private 仓库；
- 当前普通 仓库 create/edit 流程没有暴露 仓库-level `internal` visibility 输入。

## 问题

```text
chattea issue
├── create              # 创建 issue
├── list                # 按 open/closed/all 列 issue
├── view                # 查看 issue 详情
├── edit                # 修改标题、正文、状态、label、milestone、assignee
├── close               # 关闭 issue
├── reopen              # 重开 issue
├── delete              # 删除 issue，需要确认
├── comment
│   ├── create          # 添加 issue 评论
│   ├── list            # 列出 issue 评论
│   ├── edit            # 编辑 issue 评论
│   └── delete          # 删除 issue 评论，需要确认
├── label
│   ├── add             # 给 issue 添加 label id
│   └── remove          # 从 issue 移除 label id
└── assign
    ├── add             # 添加 issue assignee
    └── remove          # 移除 issue assignee
```

当前 quick start 已覆盖 create、view、评论 create/list/edit、close、reopen、按状态 list。

## 合并请求

```text
chattea pr
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
├── files               # 列出变更文件
├── comment
│   ├── create          # 添加 PR issue-comment
│   └── list            # 列出 PR issue-comments
└── review
    ├── create          # 创建 PR review event
    ├── list            # 列出 PR reviews
    └── submit          # 提交已有 pending review
```

当前 quick start 已覆盖 create、view、files、commits、评论、review、close、reopen、merge。

## 标签和里程碑

```text
chattea label
├── create
├── list
├── view
├── edit
└── delete

chattea milestone
├── create
├── list
├── view
├── edit
├── close
└── delete
```

这些命令配合 问题 / PR 的 标签 ID 和 里程碑 ID 使用。

## 项目看板

```text
chattea project
├── create              # 创建 repo-scoped project board
├── list                # 列 repo projects
├── view                # 查看 repo project
├── edit                # 编辑 repo project
├── delete              # 删除 repo project
├── column
│   ├── create          # 创建 project column
│   ├── list            # 列 project columns
│   ├── edit            # 编辑 project column
│   └── delete          # 删除 project column
├── card                # issue/PR card helpers
│   ├── add
│   ├── list
│   ├── move
│   └── remove
└── issue               # card helpers 的兼容别名
```

新文档和新自动化优先使用 `project card`。`project issue` 只保留为兼容别名。

## 发布版本

```text
chattea release
├── create
├── list
├── view
├── latest
├── by-tag
├── edit
├── delete
└── asset
    ├── list
    └── delete
```

发布版本 附件 上传 暂不作为一等命令，等 HTTP client 支持 multipart 上传 后再补。

## Actions：运行、任务、产物和运行器

```text
chattea run
├── list
├── view
├── jobs
├── logs
├── rerun
├── rerun-failed
└── delete

chattea job
├── view
├── logs
└── rerun

chattea artifact
├── list
├── view
├── download
└── delete

chattea runner
├── setup               # 安装、注册并管理本机 runner
├── list
├── view
├── edit
├── delete
└── token               # 获取 runner registration token
    ├── --scope repo    # 需要 --repo OWNER/NAME
    ├── --scope org     # 需要 --org ORG
    ├── --scope user
    └── --scope admin
```

这些命令覆盖第一版 Gitea Actions 面：运行器 生命周期、PR 触发的 run、job、log 和 产物。

## 服务

```text
chattea server
├── bootstrap           # install/init Gitea，创建 admin/token，写 ChatTea config
├── install             # 下载 ChatArch Gitea binary
├── init                # 创建最小 app.ini
├── start               # 安装并启动 user systemd service
├── stop                # 停止 user systemd service
├── restart             # 重启 user systemd service
├── status              # 查看 user systemd service 状态
├── logs                # 查看服务日志
├── health              # 检查 Gitea API 是否可达
├── config              # 查看/编辑托管 app.ini
├── version             # 查看 binary 或 server 版本
└── serve               # 前台运行 Gitea，用于调试
```

Gitea 服务由 `chattea-gitea.service` 管理；运行器 由 `chattea-runner.service` 管理。

## 当前封装缺口

最近的 quick start 和权限实践仍需要 raw API 的部分：

- organization create/view/list；
- admin user create/view/list；
- team list/add-member/remove-member；
- 通过 admin create-as-user 路径创建 user-owned 仓库；
- 继续实践 user-owned 仓库 的 admin create-as-user 路径。

这些都是实践暴露出的基础设施后续项。只有当后续实践继续需要它们时，才补对应一等命令；补完后同步更新本页。

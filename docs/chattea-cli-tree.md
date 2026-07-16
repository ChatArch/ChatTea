# ChatTea CLI 能力地图

这篇文档是当前 ChatTea CLI 的简明能力地图，用来校对哪些 Gitea 流程已经有一等 ChatTea 命令，哪些流程还需要 `chattea api`。

可导入 Python 函数映射见 [接口树](interface-tree.md)。更完整的路由映射和实践截图见 [CLI 指南](cli-guide.md)。

## 顶层命令

```text
chattea
├── api                 # 调用尚未被一等封装的原始 Gitea API
├── artifact            # 查看、下载、删除 Gitea Actions 产物
├── auth                # 配置和检查 ChatTea base URL / token
├── issue               # 管理仓库问题、评论、标签和负责人
├── job                 # 查看、读取日志或重跑 Gitea Actions job
├── label               # 管理仓库标签
├── milestone           # 管理仓库里程碑
├── pr                  # 管理合并请求、评论、review、diff/patch 和合并
├── project             # 管理 Gitea 仓库项目看板、列和卡片
├── release             # 管理仓库发布版本和发布附件
├── repo                # 创建、查看、列出、clone 和迁移仓库
├── run                 # 查看或控制 Gitea Actions workflow run
├── runner              # 管理 Gitea Actions 运行器和注册令牌
├── server              # 安装、初始化、启动和检查本机托管的 Gitea 服务
├── set-token           # 配置 ChatTea API token 和仓库本地 git 鉴权
└── token               # 创建、列出、删除和引导配置 Gitea access token
```

## 原始 API

```text
chattea api PATH        # 调用指定 Gitea API 路径
├── --method METHOD     # 指定 HTTP 方法，默认 GET
├── --data JSON         # 传入 JSON request body
└── --param KEY=VALUE   # 传入 query 参数
```

当前实践中用 raw API 覆盖的部分：

- `POST /orgs`：创建组织；
- `POST /admin/users`：创建用户；
- `GET /orgs/{org}/teams`：查看组织团队；
- `PUT /teams/{id}/members/{username}`：把用户加入团队。

这些是后续一等 ChatTea 封装的候选项。只有当实践流程继续依赖它们时，再补对应基础设施。

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

## 仓库

```text
chattea repo            # 管理 Gitea 仓库
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
├── bootstrap           # 串起 install/init/admin/token/credential 首次引导流程
├── install             # 下载 ChatArch Gitea 二进制文件
├── init                # 创建最小 app.ini
├── start               # 安装并启动用户级 systemd 服务
├── stop                # 停止用户级 systemd 服务
├── restart             # 重启用户级 systemd 服务
├── status              # 查看用户级 systemd 服务状态
├── logs                # 查看服务日志
├── health              # 检查 Gitea API 是否可达
├── config              # 查看或编辑托管 app.ini
├── version             # 查看二进制文件或 server 版本
└── serve               # 前台运行 Gitea，用于调试和本地实践
```

Gitea 服务由 `chattea-gitea.service` 管理；运行器由 `chattea-runner@<runner-name>.service` 管理。

## 当前封装缺口

最近的端到端快速开始和权限实践仍需要 raw API 的部分：

- organization create/view/list；
- admin user create/view/list；
- team list/add-member/remove-member；
- 通过 admin create-as-user 路径创建 user-owned 仓库；
- 继续实践 user-owned 仓库的 admin create-as-user 路径；
- bot / service account：Gitea 底层和本机 admin CLI 已支持 bot 用户类型，但稳定 REST API 尚未完整暴露，第一版规划见 [机器人账号与服务账号规划](bot-service-account-plan.md)。

这些都是实践暴露出的基础设施后续项。只有当后续实践继续需要它们时，才补对应一等命令；补完后同步更新本页。

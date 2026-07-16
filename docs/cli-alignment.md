# ChatTea CLI 对齐计划

这篇文档定义 ChatTea 面向 ChatArch Gitea 的、以证据为边界的 CLI 方向。

目标不是复制 GitHub CLI。ChatTea 是 Gitea CLI，也是本地 Gitea 运维工具。命令名可以沿用熟悉的 GitHub/Gitea 资源概念，但前提是它们确实对应 Gitea 的真实 API；每个命令都必须由真实 Gitea REST 路由 支撑，或由明确设计的 ChatTea 本地能力支撑。

## 证据策略

一个命令只有满足下面任一条件，才可以进入正式 CLI 树：

1. 在 `core/gitea/routers/api/v1/**` 的 Swagger annotation 中存在 Gitea REST 路由。
2. 该命令是 ChatTea 本地能力，并且有明确实现合约，例如 `set-token`、`server` 或 `repo clone`。

不要添加占位命令。不要因为 GitHub CLI 有某个命令就添加它。如果 Gitea 不支持对应能力，应先留在树外，直到存在真实本地设计或真实 Gitea 路由。

## 实现合约

每个 CLI 命令都必须是可导入 Python 代码之上的薄 适配层。

每个公开命令都应包含：

1. 可复用 Python 函数或 method，不需要调用 CLI 也能使用；
2. CLI 包装层，只负责解析参数、解析交互输入、调用 Python 函数并渲染输出；
3. 可复用 Python 函数或 API method 的测试；
4. CLI 行为测试，覆盖命令注册、参数解析、输出和失败模式；
5. 文档，把命令映射到 Gitea REST 路由 或 ChatTea 本地函数。

CLI 不能是唯一稳定集成面。Python 集成、MCP 工具和未来 网关适配层 应直接调用 Python 函数，而不是 通过 shell 调用 到 `chattea ...`。

推荐结构：

```text
src/chattea/
├── api.py or api/<domain>.py          # Gitea REST client methods；不做 Click 渲染
├── credentials.py                     # set-token、token resolution、repo-local git credential helper
├── server.py                          # 本地 Gitea install/service/config primitives
└── commands/
    ├── token.py                       # Click command group + token 函数薄 wrapper
    ├── repo.py                        # Click command group + repo 函数薄 wrapper
    ├── issue.py                       # Click command group + issue 函数薄 wrapper
    ├── pr.py                          # Click command group + pull request 函数薄 wrapper
    ├── project.py                     # Click command group + project/card 函数薄 wrapper
    └── ...
```

实际可行时，代码结构应跟 CLI 树保持一致。如果共享底层 class 或 辅助函数 更清晰，也可以保持灵活；但 domain logic 必须可导入，并与 Click 解耦。

## 令牌和凭据合约

`set-token` 不是简单复制 `auth login`，也不只是 dotenv 写入器。

`set-token` 是 ChatTea 的凭据基础：

- 为当前 仓库/Gitea 远端 配置 令牌访问，让 git transport 可以 pull/push，不需要反复询问 令牌；
- 在合适时保存或更新 ChatTea/ChatEnv 令牌配置档；
- 为 `repo`、`issue`、`pr`、`project`、`release` 和 Actions 命令提供 API 令牌来源；
- 正常命令输出不打印 raw 令牌。

API 命令的 令牌 resolution 需要集中且一致：

1. 显式 CLI 令牌 参数；
2. 从当前 Gitea 远端 推导出的 仓库本地 git credential/config；
3. ChatTea ChatEnv 配置档 令牌；
4. 如果命令需要鉴权但没有 令牌，则干净失败。

令牌创建和令牌配置是两件事：

- `token create` 使用 Gitea BasicAuth 调用 `POST /users/{username}/tokens` 创建 访问令牌；
- `token bootstrap` 创建 访问令牌，然后立即调用与 `set-token` 相同的凭据配置路径；
- `set-token` 把已经创建好的 令牌 配置给 ChatTea 和 git transport。

## 已确认的当前 ChatTea CLI

这是当前 working branch 已实现的能力面，不是完整目标。

```text
chattea
├── set-token                         # `chattea.commands.auth.configure_token` -> ChatEnv + repo-local git extraHeader credential
├── api                               # 通过 `chattea.commands.api.call_api` 做原始 Gitea API passthrough
├── auth                              # 辅助 status/login namespace；复用 set-token 的 credential backend
│   ├── login                         # 配置 Gitea API + repo-local git credentials
│   ├── status                        # 显示已配置 base URL 和 masked token 状态
│   └── token                         # 显示 masked configured token
├── token                             # 通过 BasicAuth 管理 Gitea access token 生命周期
│   ├── create                        # POST /users/{username}/tokens -> `create_access_token`
│   ├── list                          # GET /users/{username}/tokens -> `list_access_tokens`
│   ├── delete                        # DELETE /users/{username}/tokens/{token} -> `delete_access_token`
│   └── bootstrap                     # create token + configure ChatTea/Git credentials
├── server                            # 本地 / 内部 Gitea 生命周期管理
│   ├── install                       # `chattea.commands.server.install_gitea` -> `chattea.server.install_binary`
│   ├── init                          # `chattea.commands.server.init_gitea_server`
│   ├── bootstrap                     # 通过 `bootstrap_gitea_server` 串起本地 install/init/admin/token/credential
│   ├── serve                         # `chattea.commands.server.serve_gitea`
│   ├── start                         # `chattea.commands.server.start_gitea_service`
│   ├── stop                          # `chattea.commands.server.stop_gitea_service`
│   ├── restart                       # `chattea.commands.server.restart_gitea_service`
│   ├── status                        # `chattea.commands.server.status_gitea_service`
│   ├── logs                          # `chattea.commands.server.logs_gitea_service`
│   ├── version                       # `chattea.commands.server.gitea_version`
│   ├── health                        # `chattea.commands.server.check_gitea_health`
│   └── config                        # 本地 app.ini helper
│       ├── path                      # `resolve_gitea_config_path`
│       ├── show                      # `read_gitea_config`
│       ├── get                       # `get_gitea_config_value`
│       └── set                       # `set_gitea_config_value`
├── repo                              # 仓库操作
│   ├── list                          # Gitea API-backed `list_repositories`
│   ├── view                          # Gitea API-backed `view_repository`
│   ├── create                        # Gitea API-backed `create_repository`
│   ├── clone                         # 本地 git helper `clone_repository`
│   └── migrate                       # Gitea API-backed `migrate_repository`
├── issue                             # 仓库 issue 操作；基于 /repos/{owner}/{repo}/issues
│   ├── list                          # GET /repos/{owner}/{repo}/issues
│   ├── view                          # GET /repos/{owner}/{repo}/issues/{index}
│   ├── create                        # POST /repos/{owner}/{repo}/issues
│   ├── edit                          # PATCH /repos/{owner}/{repo}/issues/{index}
│   ├── close                         # PATCH issue state=closed
│   ├── reopen                        # PATCH issue state=open
│   ├── delete                        # DELETE /repos/{owner}/{repo}/issues/{index}
│   ├── comment                       # issue comment API
│   ├── label                         # issue label assignment API
│   └── assign                        # issue assignee API
├── label                             # 仓库 label
│   ├── list                          # GET /repos/{owner}/{repo}/labels
│   ├── view                          # GET /repos/{owner}/{repo}/labels/{id}
│   ├── create                        # POST /repos/{owner}/{repo}/labels
│   ├── edit                          # PATCH /repos/{owner}/{repo}/labels/{id}
│   └── delete                        # DELETE /repos/{owner}/{repo}/labels/{id}
├── milestone                         # 仓库 milestone
│   ├── list                          # GET /repos/{owner}/{repo}/milestones
│   ├── view                          # GET /repos/{owner}/{repo}/milestones/{id}
│   ├── create                        # POST /repos/{owner}/{repo}/milestones
│   ├── edit                          # PATCH /repos/{owner}/{repo}/milestones/{id}
│   ├── close                         # PATCH milestone state=closed
│   └── delete                        # DELETE /repos/{owner}/{repo}/milestones/{id}
├── pr                                # Pull request 操作；当前树不提供本地 checkout helper
│   ├── list                          # GET /repos/{owner}/{repo}/pulls
│   ├── view                          # GET /repos/{owner}/{repo}/pulls/{index}
│   ├── create                        # POST /repos/{owner}/{repo}/pulls
│   ├── edit                          # PATCH /repos/{owner}/{repo}/pulls/{index}
│   ├── close                         # PATCH PR state=closed
│   ├── reopen                        # PATCH PR state=open
│   ├── merge                         # POST /repos/{owner}/{repo}/pulls/{index}/merge
│   ├── diff                          # GET /repos/{owner}/{repo}/pulls/{index}.diff
│   ├── patch                         # GET /repos/{owner}/{repo}/pulls/{index}.patch
│   ├── commits                       # GET /repos/{owner}/{repo}/pulls/{index}/commits
│   ├── files                         # GET /repos/{owner}/{repo}/pulls/{index}/files
│   ├── comment                       # 通过 issue comment routes 实现 PR issue-comment helper
│   └── review                        # PR review list/create/submit routes
├── release                           # 仓库 release
│   ├── list                          # GET /repos/{owner}/{repo}/releases
│   ├── view                          # GET /repos/{owner}/{repo}/releases/{id}
│   ├── latest                        # GET /repos/{owner}/{repo}/releases/latest
│   ├── by-tag                        # GET /repos/{owner}/{repo}/releases/tags/{tag}
│   ├── create                        # POST /repos/{owner}/{repo}/releases
│   ├── edit                          # PATCH /repos/{owner}/{repo}/releases/{id}
│   ├── delete                        # DELETE /repos/{owner}/{repo}/releases/{id}
│   └── asset                         # Release asset list/delete；upload 等 multipart client 支持后再补
└── project                           # Repo-scoped Gitea Project board，不是 GitHub Projects v2
    ├── list                          # GET /repos/{owner}/{repo}/projects
    ├── view                          # GET /repos/{owner}/{repo}/projects/{id}
    ├── create                        # POST /repos/{owner}/{repo}/projects
    ├── edit                          # PATCH /repos/{owner}/{repo}/projects/{id}
    ├── delete                        # DELETE /repos/{owner}/{repo}/projects/{id}
    ├── column                        # Repository Project column API
    │   ├── list                      # GET /repos/{owner}/{repo}/projects/{id}/columns
    │   ├── create                    # POST /repos/{owner}/{repo}/projects/{id}/columns
    │   ├── edit                      # PATCH /repos/{owner}/{repo}/projects/{id}/columns/{column_id}
    │   └── delete                    # DELETE /repos/{owner}/{repo}/projects/{id}/columns/{column_id}
    └── card                          # Project card API；REST path 里称为 `issues`
        ├── list                      # GET /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues
        ├── add                       # POST /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues/{issue_id}
        ├── remove                    # DELETE /repos/{owner}/{repo}/projects/{id}/columns/{column_id}/issues/{issue_id}
        └── move                      # POST /repos/{owner}/{repo}/projects/{id}/issues/{issue_id}/move
```

`project issue` 这类兼容别名可以在过渡期存在，但不是正式目标能力面。新文档和新自动化应使用 `project card`。

## 已确认可完整实现的 API 领域

下面这些领域已从 `core/gitea/routers/api/v1/**` 的 Gitea Swagger annotation 中确认，可以作为真实命令实现。每个新增命令仍必须遵守上面的实现合约。

- `user`：`/admin/users` 下的普通 admin user 创建、编辑、删除 路由；用于托管本地 引导。注意 Gitea 稳定 REST API 目前没有完整暴露 `UserTypeBot` 创建、查询和 token 管理，机器人账号规划见 `bot-service-account-plan.md`。
- `token`：`/users/{username}/tokens` list/create/delete；create 需要 BasicAuth 或反向代理 auth。
- `issue`：`/repos/{owner}/{repo}/issues`、评论、标签、reactions、pin/lock、dependencies、attachments、time tracking。
- `label`：`/repos/{owner}/{repo}/labels`，以及可选的 org 标签 路由。
- `milestone`：`/repos/{owner}/{repo}/milestones`。
- `pr`：`/repos/{owner}/{repo}/pulls`、diff/patch、files、commits、merge、update、reviews、requested reviewers。
- `release`：`/repos/{owner}/{repo}/releases` 和 发布版本 附件。
- `runner` / `run` / `job` / `artifact`：Gitea Actions MVP 能力面，用于 运行器注册和生命周期，以及 PR 触发的 run/job/log/产物 查看。API 支撑的命令映射到 `/repos/{owner}/{repo}/actions/...`；本机 runner 管理集中在 `runner local`，多实例批量操作集中在 `runner pool`。
- `project`：只覆盖 仓库级 `/repos/{owner}/{repo}/projects`；不是 GitHub Projects v2。
- `workflow`：`/repos/{owner}/{repo}/actions/workflows`。
- `run`：`/repos/{owner}/{repo}/actions/runs`。
- `job`：`/repos/{owner}/{repo}/actions/jobs`。
- `artifact`：`/repos/{owner}/{repo}/actions/artifacts`。
- `runner`：仓库/org/user/admin scoped `/actions/runners` 路由。
- `secret`：仓库/org/user scoped `/actions/secrets` 路由；注意观察到的 annotation 中 user scope 缺少 list 路由。
- `variable`：仓库/org/user scoped `/actions/variables` 路由。
- `status`：`/repos/{owner}/{repo}/statuses/{sha}` 和 combined status 路由。

## 引导流程方向

初始配置应实现为真实工作流组合，不应只是 占位命令。

- `server bootstrap` 或 顶层 `bootstrap` 是本地托管 Gitea 流程：install、init、start、创建默认用户、生成 / 创建 令牌、运行 set-token，并验证 `/user`。
- `token bootstrap` 是远程 / 已有 Gitea 流程：BasicAuth 创建 令牌、运行 set-token，并验证 `/user`。
- 密码应从 prompt、`--password-env` 或敏感 ChatEnv 引导字段读取；这些字段只服务一次性 bootstrap，不应作为长期业务凭据输出、提交或写入公开文档。
- 生成的 访问令牌应通过 credential path 保存，并在正常输出中脱敏。

## 非目标

- 不声称完整兼容 GitHub API 或 GitHub CLI。
- 不把 Gitea 仓库 Project boards 建模成 GitHub Projects v2。
- 不把 `checkout` 加入正式 REST-backed tree。如果之后需要，应明确设计为本地 git 辅助函数，并提供证据和测试。
- 不添加 `runner install/start/stop/logs` 这类 运行器生命周期 命令，除非已有真实本地 运行器生命周期 设计。
- 不把业务逻辑只放在 Click command body 里。
- 不把 仓库/project/问题/运行器 ID 作为 ChatEnv 字段；它们是请求参数。

## 测试和持续集成合约

每个已实现领域都应有下面这些 gate：

1. 覆盖 API path、method、payload、令牌 resolution 和错误处理的单元测试；
2. 覆盖非平凡命令行为的直接 Python function 测试；
3. 覆盖 help、成功路径和预期失败的 CLI 行为测试；
4. 可行时，在本地 ChatArch Gitea 实例上运行 真实集成实践，使用任务本地状态和临时 仓库/project/问题；
5. PR ready 前运行 `pytest`、package build、`twine check`、`mkdocs build --strict` 和 `git diff --check`。

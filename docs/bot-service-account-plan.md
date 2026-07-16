# 机器人账号与服务账号 CLI 规划

本文记录 Gitea 机器人账号能力的调研结论，以及 ChatTea 第一版 `bot`/服务账号 CLI 的规划。这里的“机器人”不是 Actions runner，而是用于自动化调用 Gitea API、Git over HTTPS、CI/CD 或仓库维护任务的账号主体。

## 结论

Gitea 已经有底层 bot 用户类型，但稳定 REST API 还没有完整暴露 bot 管理能力。

- Gitea 模型层有 `UserTypeBot`，源码中 `models/user/user.go` 定义 `UserTypeBot // 4`。
- Gitea 自带的系统账号 `gitea-actions` 是 bot 类型，源码中 `models/user/user_system.go` 用于 Actions。
- 本机 Gitea admin CLI 已支持创建 bot：`gitea admin user create --user-type bot`。
- 本机 admin CLI 创建用户时还能同时生成访问令牌：`--access-token --access-token-name --access-token-scopes`。
- 当前托管 Gitea binary 还提供 `gitea admin user generate-access-token --username <user> --token-name <name> --scopes <scopes> --raw`，可用于后续给 bot 单独生成或轮换 token。
- 稳定 REST API 的 `CreateUserOption`、`EditUserOption`、`User` schema 没有 `user_type`、`type`、`is_bot` 字段。
- `/admin/users` 当前只按 individual user 搜索；API 返回也不能可靠区分 bot。
- `/users/{username}/tokens` 能创建 token，但路由需要 self-or-admin + BasicAuth/reverse-proxy auth；不能只拿一个已有 API token 去给另一个 bot 账号发 token。

所以 ChatTea 第一版不能把 bot 做成完全 REST-backed 的远程通用能力。第一版应该明确分成两条路径：

1. **本机托管 Gitea**：通过 ChatTea 管理的 Gitea binary/config/work-path 调用 `gitea admin user create --user-type bot`，这是当前能真实创建 bot 的路径。
2. **远程 Gitea**：如果只能走稳定 REST API，则先只能创建受限的 individual machine user，不能声称是 Gitea bot 用户类型。

## 官方状态

### 已有能力

Gitea admin CLI 当前已经包含这些 bot/service-account 相关能力：

```bash
gitea admin user create \
  --username <bot-name> \
  --email <bot-email> \
  --user-type bot \
  --restricted \
  --access-token \
  --access-token-name <token-name> \
  --access-token-scopes <scopes>
```

对于已存在的 bot 或普通自动化用户，当前托管 Gitea binary 还支持单独生成 token：

```bash
gitea admin user generate-access-token \
  --username <bot-name> \
  --token-name <token-name> \
  --scopes <scopes> \
  --raw
```

源码和运行时依据：

- `cmd/admin_user_create.go`：`--user-type individual|bot`。
- `cmd/admin_user_create.go`：bot 用户不能设置 password / random password。
- `cmd/admin_user_create.go`：`--access-token`、`--access-token-name`、`--access-token-scopes`。
- `cmd/admin_user_create.go`：创建用户后调用 `auth_model.NewAccessToken` 并只打印一次 token。
- 运行中的托管 Gitea binary 暴露 `admin user generate-access-token`，可作为 ChatTea 本机 backend 的 token create/rotate 基础能力。

### REST API 缺口

官方 OpenAPI 当前暴露的 schema 仍是普通用户形态：

- `CreateUserOption` 有 `username`、`email`、`password`、`restricted`、`visibility` 等字段；没有 `user_type` / `is_bot`。
- `EditUserOption` 有 `prohibit_login`、`restricted` 等字段；没有 bot 类型转换字段。
- `User` 响应没有 `type` / `is_bot` 字段。
- `CreateAccessTokenOption` 支持 `name` 和 `scopes`，但 token 路由需要 BasicAuth/reverse-proxy auth，不适合 passwordless bot 自助轮换。

官方 API 页面：

- <https://docs.gitea.com/api/1.24/#operation/adminCreateUser>
- <https://docs.gitea.com/api/1.24/#operation/userCreateToken>
- <https://gitea.com/swagger.v1.json>

### 上游讨论

官方仓库已有长期讨论和正在推进的 PR，说明 bot 账号仍是一个演进中的能力面：

- `feat: manage bot accounts from the admin UI, API and CLI`：<https://github.com/go-gitea/gitea/pull/38181>
- `[Proposal] Add "bot account" as a type of user`：<https://github.com/go-gitea/gitea/issues/13044>
- `Repository service account for Gitea Actions`：<https://github.com/go-gitea/gitea/issues/26754>
- `Organization and Repository level access token`：<https://github.com/go-gitea/gitea/issues/25900>
- `API token: add bot type`：<https://github.com/go-gitea/gitea/issues/32359>

其中 PR #38181 计划补 admin UI、API、CLI 上的一等 bot 管理，包括 bot token 面板、individual/bot 转换、bot auth hardening。ChatTea 应跟踪这个 PR；一旦上游发布包含这些 API 的版本，再把 ChatTea 的 bot 命令从本机 CLI backend 扩展到 REST backend。

## ChatTea 当前状态

ChatTea `0.3.0` 已有的相关能力：

- `chattea token create/list/delete/bootstrap`：通过 BasicAuth 调 Gitea `/users/{username}/tokens`。
- `chattea server bootstrap`：本地托管 Gitea 时创建初始管理员、创建管理员 token、写入 ChatTea 凭据。
- `chattea set-token` / `chattea auth login`：配置 `CHATTEA_BASE_URL`、`CHATTEA_TOKEN` 和 repo-local git credential。
- `chattea api`：可临时调用还没有封装的 Gitea REST API。

当前缺口：

- 没有一等 `user`、`admin user`、`bot` 或 `service-account` 命令组。
- `token` 命令把认证主体和 token 所属用户合在一个 `--username` 上；不适合“管理员给 bot 创建 token”。
- 稳定 REST API 不能创建真正的 `UserTypeBot`，所以 ChatTea 不能只靠 `GiteaClient` 完成 bot 创建。
- 文档没有定义“bot 用户”和“受限 machine user”的差异，容易把两者混用。

## 第一版 CLI 规划

第一版目标是把真实可做的路径封装出来，并把 API 缺口显式暴露给用户。

```text
chattea bot
├── create          # 本机 backend：创建 Gitea UserTypeBot，并可同时生成 token
├── view            # 查看 bot 基本状态；REST 不返回 type 时标明“无法确认是否为 bot”
├── list            # 本机 backend 可列出 bot；REST backend 只能列 individual 或标明不完整
├── token
│   ├── create      # 给 bot 生成 token；本机 backend 走 gitea admin user generate-access-token
│   ├── list        # 列出 bot token；远程 REST 需要 admin BasicAuth 或后续上游 API
│   ├── rotate      # 删除同名 token 后重新生成
│   └── delete      # 删除 bot token
└── plan            # 输出当前 Gitea backend 能力判断和推荐命令
```

建议参数：

```bash
chattea bot create \
  --username release-bot \
  --email release-bot@example.invalid \
  --restricted \
  --token-name release-bot \
  --scope write:repository,write:issue \
  --show-token-once
```

本机 backend 的实现原则：

- 使用 ChatTea 已解析出的 `CHATTEA_BINARY`、`CHATTEA_CONFIG`、`CHATTEA_WORK_PATH`。
- 调用 `gitea admin user create --user-type bot`，不传 password。
- 如果需要 token，传 `--access-token --access-token-name --access-token-scopes`。
- 对已存在 bot 的 token 创建或轮换，优先调用 `gitea admin user generate-access-token --raw`。
- 解析 stdout 时默认脱敏 token；只有显式 `--show-token-once` 才打印原始 token。
- 允许 `--save-as-current` 把生成的 bot token 写入 ChatTea 凭据，但默认不覆盖当前管理员 token。
- 所有真实 token、密码、服务 URL、本机路径都只进入本地受限记录，不进入公开文档。

远程 REST backend 的实现原则：

- 不把普通 `POST /admin/users` 创建的用户称为 bot。
- 如果用户明确需要远程 API-only 方案，命令名应使用 `service-user` 或 `machine-user`，文档称为“受限普通用户”。
- 只有上游 API 出现 `user_type` / `is_bot` / bot token management 后，才把 `chattea bot create --backend api` 标记为完整支持。

## 文档和实践要求

新增 bot CLI 时必须同时更新：

- CLI 树：`docs/chattea-cli-tree.md`。
- CLI 实战指南：`docs/cli-guide.md`。
- 权限与可见性文档：`docs/gitea-permissions-and-visibility.md`。
- 从零开始快速开始：如果 bot 用于替换管理员 token，需要写清迁移步骤。
- 本文：把“规划”改成“已实践路径”，附脱敏命令记录。

真实实践至少要覆盖：

1. 本机创建 bot 用户；
2. 生成 scoped token；
3. 用 bot token 调 `/user` 确认主体；
4. 用 bot token 对一个临时仓库执行最小权限操作；
5. 轮换 token；
6. 删除临时 bot 或清理 token；
7. 记录网页端能看到的 bot 标识或管理页面证据。

## 待确认问题

- ChatTea 是否需要单独的 `service-user` 命令，还是把 API-only 受限普通用户放进 `bot create --backend api --mode restricted-user`。
- bot token 是否应支持写入独立命名凭据，而不是覆盖 `CHATTEA_TOKEN`。
- bot 与 repo/org 权限绑定是否先通过团队成员关系完成，还是等上游 repository/org token 能力。
- 如果上游 PR #38181 合并，ChatTea 是否需要按 Gitea 版本自动选择 `api` backend。

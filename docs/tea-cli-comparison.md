# 官方 tea CLI 与 ChatTea 覆盖范围对比

本文用于校对 ChatTea 与 Gitea 官方命令行工具 `tea` 的能力边界。官方 `tea` 是 Gitea 通用生产力 CLI；ChatTea 是 ChatArch 内部围绕“托管 Gitea、任务账号、组织权限、Actions Runner 和真实协作流程”做的流程型 CLI。

本页基于 `tea v0.14.2` 的 `--help` 输出整理。完整校对记录保存在本轮 Playground project 中，公开文档只保留结论和命令形态。

## 官方 tea 顶层能力

```text
tea
├── issues / issue / i                  # issue 列表、创建和更新
├── pulls / pull / pr                   # PR 管理和本地 checkout
├── labels / label                      # issue label 管理
├── milestones / milestone / ms         # milestone 管理
├── releases / release / r              # release 和 release asset 管理
├── times / time / t                    # issue / PR time tracking
├── organizations / organization / org  # organization 列表、创建和删除
├── repos / repo                        # repository 管理
├── branches / branch / b               # branch 查询、保护、重命名
├── actions / action                    # Actions secrets、variables、runs、workflows
├── wiki                                # wiki 页面管理
├── webhooks / webhook / hooks / hook   # webhook 管理
├── comments / comment / c              # issue / PR 评论管理
├── open / o                            # 在浏览器打开当前对象
├── notifications / notification / n    # notification 查看和标记
├── clone / C                           # clone repository
├── api                                 # 调用认证后的 API
├── whoami                              # 查看当前登录用户
├── admin / a                           # 管理员操作
├── logins / login                      # 登录配置
├── logout                              # 退出登录
└── ssh-keys / ssh-key                  # SSH 公钥管理
```

## 官方 tea 的重点子命令

```text
tea repos
├── list
├── search
├── create
├── create-from-template
├── fork
├── migrate
├── delete
└── edit

tea pulls
├── list
├── checkout
├── clean
├── create
├── close / reopen / edit
├── review / approve / reject
├── merge
├── review-comments
├── resolve / unresolve

tea actions
├── secrets list/create/delete
├── variables list/set/delete
├── runs list/view/delete/logs
└── workflows list/view/dispatch/enable/disable

tea admin users
├── list
├── create
├── edit
└── delete

tea releases assets
├── list
├── create
└── delete
```

## ChatTea 当前覆盖范围

```text
chattea
├── server              # 本机 Gitea 安装、初始化、systemd user service、日志和健康检查
├── auth / set-token    # ChatTea token、repo-local git extraHeader 配置
├── token               # access token list/create/delete/bootstrap
├── bot                 # 本机 Gitea bot / 服务账号 local backend
├── user                # admin create/delete 普通用户
├── org                 # org create/list/view、team create/list、team member add/remove
├── repo                # repo create/list/view/clone/migrate
├── issue               # issue create/list/view/edit/close/reopen/delete、comment、label、assign
├── pr                  # PR create/list/view/edit/close/reopen/merge、diff/patch、files、commits、comment、review
├── label / milestone   # label 和 milestone 管理
├── project             # 仓库级 project board、column、card
├── release             # release create/list/view/latest/by-tag/edit/delete、asset list/delete
├── notification        # notification list/view/poll/mark-read
├── runner              # runner registry/local/pool/workflow 管理
├── run / job / artifact # Actions run、job、log、artifact 管理
└── api                 # raw Gitea API 兜底
```

## 覆盖范围对比

| 领域 | 官方 tea | ChatTea | 结论 |
| --- | --- | --- | --- |
| 登录和凭据 | `logins`、OAuth refresh、git credential helper | `auth`、`set-token`、`token bootstrap`、repo-local `extraHeader` | tea 更像通用登录管理；ChatTea 更强调项目内 Git 鉴权可复现。 |
| 仓库基础操作 | list/search/create/fork/migrate/delete/edit/clone | create/list/view/edit/generate/clone/migrate | tea 的仓库 CRUD 更完整；ChatTea 暂缺 repo delete/search/fork。 |
| Template 仓库 | create `--template`、edit `--template true/false`、`create-from-template` | `repo create --template`、`repo edit --template/--no-template`、`repo generate` | 两边都已覆盖 template 主链路；命名不同。 |
| Issue / PR | issue/PR CRUD、PR checkout/clean、approve/reject、review comments resolve | issue/PR CRUD、comment、review create/list/submit、diff/patch/files/commits | 基础协作两边都有；tea 的本地 PR helper 更强，ChatTea 的 API 输出和流程脚本更适合自动化。 |
| 评论 | 独立 `comments` 命令 | issue/pr 下的 comment 子命令 | 功能重叠，组织方式不同。 |
| 标签 / 里程碑 | label、milestone、milestone issue 绑定 | label、milestone，issue/PR 可绑定标签/里程碑 | tea 对 milestone issue 绑定更显式。 |
| Release | release CRUD、asset list/create/delete | release CRUD、asset list/delete | ChatTea 暂缺 release asset upload。 |
| Actions | secrets、variables、runs、workflows dispatch/enable/disable | run、job、artifact、runner registry/local/pool/workflow | tea 更覆盖 workflow 配置对象；ChatTea 更覆盖自托管 runner 生命周期。 |
| Runner | 未作为重点命令面 | runner registry/local/pool/workflow | ChatTea 明显更强，适合托管环境。 |
| Organization | org list/create/delete | org create/list/view、team create/list/member add/remove | tea 有 org delete；ChatTea 有 team 管理，这是组织权限实践需要的能力。 |
| Admin user | admin users list/create/edit/delete | user create/delete | tea 更完整；ChatTea 先满足实践中的建号/清理。 |
| Wiki / Webhook / SSH key / Time tracking / Branch | 有一等命令 | 暂未封装 | 这些是 ChatTea 后续可按实践需要补的横向能力。 |
| 本机服务管理 | 不负责安装或 systemd | `server`、`bot`、`runner local` | ChatTea 是托管 Gitea 工作流的一部分，这是和 tea 最大差异之一。 |
| raw API | `tea api` | `chattea api` | 两边都有兜底 API。 |

## 当前 Git / Gitea 支持概要

ChatTea 目前已经支持的 Git/Gitea 主线流程：

1. 本机 Gitea 生命周期：安装、初始化、启动、停止、重启、日志、健康检查。
2. 凭据和 Git transport：配置 API token，并在仓库本地写入 Git `extraHeader`，支持 HTTPS push/pull/clone 的实践链路。
3. 仓库：创建、列出、查看、clone、迁移；默认 private，支持显式 `--public` / `--private`。
4. 组织权限：创建组织、创建 team、列 team、添加/移除 team 成员。
5. 用户：管理员创建和删除普通用户。
6. 协作对象：issue、PR、评论、标签、里程碑、release、project board。
7. 任务账号入口：notification list/view/poll/mark-read，支撑 `@任务账号` 后的轮询。
8. Actions 和 Runner：workflow run、job、日志、artifact、runner 注册记录、本机 runner instance、runner pool。

当前还没有补齐的 Git/Gitea 能力：

- repo delete/search/fork；
- release asset upload；
- wiki、webhook、SSH key、branch protection、time tracking；
- admin user list/view/edit；
- team edit/delete、selected-repos team 的仓库绑定管理；
- Actions secrets/variables/workflows dispatch/enable/disable。

## Template 能力结论

官方 tea 已经覆盖 template 相关能力：

```bash
tea repos create --template
tea repos edit --template true
tea repos edit --template false
tea repos create-from-template --template <owner>/<template-repo> --name <new-repo> --owner <owner>
```

当前 Gitea Swagger 也确认底层 API 支持：

- `CreateRepoOption.template`：创建仓库时设为模板；
- `EditRepoOption.template`：把已有仓库设为模板或取消模板；
- `POST /repos/{template_owner}/{template_repo}/generate`：从模板仓库生成新仓库；
- `GenerateRepoOption` 支持 `name`、`owner`、`private`、`description`、`default_branch` 等字段。

ChatTea 现在按这个接口补了三类命令：

```text
chattea repo create --template
chattea repo edit OWNER/NAME --template / --no-template
chattea repo generate --template OWNER/TEMPLATE --owner TARGET_OWNER --name NEW_REPO [--private] --copy-git-content [--copy-labels ...]
```

当前实现范围：

1. `repo create --template`：创建仓库时直接设为模板仓库。
2. `repo edit OWNER/NAME --template/--no-template`：切换已有仓库的模板状态；同命令也支持描述、网站、public/private、archive 和默认分支。
3. `repo generate --template OWNER/TEMPLATE --owner TARGET_OWNER --name NEW_REPO`：从模板仓库生成新仓库；Gitea 要求至少选择一个 template item，因此 ChatTea 本地校验至少传一个 `--copy-*`，例如 `--copy-git-content`。可复制 git content、hooks、avatar、labels、topics、webhooks 和 protected branches。

## 下一步建议

- 已用真实本机 Gitea 环境跑通 template smoke：创建模板仓库、切换模板状态、从模板生成仓库，并确认 generate 需要至少一个复制项。
- 第二优先级：补 repo delete/search/fork，让 ChatTea 的仓库管理面继续接近 tea。
- 第三优先级：按真实流程需要补 wiki、webhook、branch protection、SSH key 和 Actions secrets/variables/workflow dispatch。

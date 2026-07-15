# 仓库协作快速开始

这篇文档记录一次在隔离 ChatArch Gitea 实例上运行的本地 ChatTea CLI 端到端流程。它是一个代表性的 冒烟验证路径，不是每个 仓库 级命令的完整测试。

该流程覆盖这些命令：

```text
chattea server bootstrap
chattea server health
chattea repo create
chattea label create/list
chattea milestone create/list
chattea issue create/comment/close/list
chattea release create 在空仓库上的错误处理
```

ChatTea `0.2.3` 还包括 `pr`、`release`、`runner`、`run`、`job` 和 `artifact` 命令组。本文只聚焦仓库协作；运行器注册、PR 触发的工作流 run、job、log 和产物见 [Actions / Flow 快速开始](actions-flow-quickstart.md)。

## 1. 启动隔离的本地 Gitea

这次 冒烟验证使用任务本地的 `CHATARCH_HOME`、任务本地的 Gitea work path，以及本地 ChatArch Gitea 二进制文件。管理员密码通过环境变量传入，CLI 不打印密码。

![ChatTea 本地引导和健康检查](assets/repo-collaboration/bootstrap-health.svg)

等价命令形态：

```bash
export CHATARCH_HOME=/path/to/local-smoke/chatarch-home
export GITEA_ADMIN_PASSWORD='[REDACTED]'

chattea server bootstrap \
  --binary ~/.local/bin/gitea \
  --work-path /path/to/local-smoke/gitea-work \
  --config /path/to/local-smoke/gitea-work/custom/conf/app.ini \
  --base-url http://127.0.0.1:13017 \
  --listen-addr 127.0.0.1 \
  --http-port 13017 \
  --admin-user smoke \
  --admin-email smoke@example.invalid \
  --admin-password-env GITEA_ADMIN_PASSWORD \
  --token-name default \
  --token-scopes all \
  -I

chattea server health --url http://127.0.0.1:13017
```

这个步骤证明：

- ChatTea 可以从隔离状态初始化一个本地 ChatArch Gitea 实例；
- `server bootstrap` 会通过本地 Gitea admin CLI 创建管理员和 令牌；
- 生成的 令牌 在 CLI 输出中会被脱敏；
- `server health` 可以确认 Gitea API 端点 可达。

## 2. 运行仓库协作流程

完成 引导 后，同一个 ChatEnv 配置档 会提供 `CHATTEA_BASE_URL` 和 `CHATTEA_TOKEN`，因此 仓库 级命令不再需要重复传 令牌 参数。

![面向本地 Gitea 的仓库协作 CLI 流程](assets/repo-collaboration/repo-issue-flow.svg)

等价命令形态：

```bash
chattea repo create \
  --owner smoke \
  --name cli-demo \
  --description 'ChatTea CLI smoke repository' \
  -I

chattea label create \
  --repo smoke/cli-demo \
  --name docs \
  --color 00aaee \
  --description 'Documentation work'

chattea label list --repo smoke/cli-demo

chattea milestone create \
  --repo smoke/cli-demo \
  --title v1.0 \
  --description 'First documentation milestone'

chattea milestone list --repo smoke/cli-demo

chattea issue create \
  --repo smoke/cli-demo \
  --title 'Document ChatTea CLI flow' \
  --body 'Smoke test issue created by ChatTea.' \
  --label 1 \
  --milestone 1 \
  --assignee smoke

chattea issue comment create \
  --repo smoke/cli-demo \
  1 \
  --body 'Comment created through chattea issue comment create.'

chattea issue close --repo smoke/cli-demo 1
chattea issue list --repo smoke/cli-demo --state all
```

这个步骤证明：

- `repo create` 可以通过 Gitea API 创建仓库；
- `label create/list` 可以创建并读取仓库 标签；
- `milestone create/list` 可以创建并读取仓库 里程碑；
- `issue create` 可以绑定 标签、里程碑和 负责人；
- `issue comment create` 可以添加 问题 评论；
- `issue close` 可以通过 问题 edit 路由 更新 问题 状态；
- `issue list --state all` 可以看到最终 已关闭问题 状态。

同一个结果也能在 Gitea Web UI 中看到。问题页面会展示由 ChatTea 创建的 已关闭问题，以及 `docs` 标签、`v1.0` 里程碑和通过 `chattea issue comment create` 创建的评论。

![Gitea Web UI 中由 ChatTea 创建的 已关闭问题](assets/repo-collaboration/gitea-issue-web.png)

## 3. Release 命令错误处理

Release 路由底层是 `POST /api/v1/repos/{owner}/{repo}/releases`，但空仓库无法创建 release。冒烟验证流程故意在空的 `cli-demo` 仓库上尝试创建 release，用来验证 CLI 会输出干净的 Gitea API 错误，而不是 Python 回溯。

![空仓库上 release create 的干净错误](assets/repo-collaboration/release-empty-repo-error.svg)

真正的 release create 冒烟验证 应该在至少有一个 commit/tag 的仓库上运行：

```bash
chattea release create \
  --repo smoke/cli-demo \
  --tag v0.1.0 \
  --name 'Local smoke release'
```

## 已复核但未放进截图流程的能力

ChatTea 还包括下面这些 API 支撑的能力，单元测试、CLI 覆盖和 路由 证据见 `docs/interface-tree.md`、`docs/cli-alignment.md` 和 `docs/actions-flow-quickstart.md`：

- `chattea pr list/view/create/edit/close/reopen/merge/diff/patch/commits/files`
- `chattea pr comment list/create`
- `chattea pr review list/create/submit`
- `chattea release list/view/latest/by-tag/create/edit/delete`
- `chattea release asset list/delete`
- `chattea runner token/list/view/edit/delete`
- `chattea runner setup install/register/start/stop/status/logs/doctor`
- `chattea run list/view/jobs/logs/rerun/rerun-failed/delete`
- `chattea job view/logs/rerun`
- `chattea artifact list/view/download/delete`

当前仍刻意不纳入一等能力面的部分：

- `chattea pr checkout`：这是本地 git 工作流，不属于当前 REST 支撑的能力面；
- 发布版本 附件 上传：等 HTTP client 增加 multipart upload 支持后再补。

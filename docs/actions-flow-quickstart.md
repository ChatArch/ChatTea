# Actions / Flow（动作 / 流程）快速开始

这篇文档记录 ChatTea 已实际跑通过的 Actions / Flow 流程。验收链路是：启用 Actions，注册运行器，推送工作流文件，通过 PR 触发工作流，查看 run/job，并读取日志。本文只写已经有实际命令和截图证据的内容。

## CLI 能力面

```text
chattea runner                # 管理 Gitea Actions 运行器
├── token                     # 获取运行器注册令牌
├── list                      # 列出运行器
├── view                      # 查看运行器详情
├── edit                      # 启用或禁用运行器
├── delete                    # 删除运行器
└── setup                     # 本机运行器安装和服务管理
    ├── install               # 安装 gitea-runner
    ├── register              # 注册运行器
    ├── start                 # 启动运行器服务
    ├── stop                  # 停止运行器服务
    ├── status                # 查看运行器服务状态
    ├── logs                  # 查看运行器服务日志
    └── doctor                # 检查运行器配置和二进制文件

chattea run                   # 查看和控制 workflow run
├── list                      # 列出 run
├── view                      # 查看 run 详情
├── jobs                      # 列出 run 下的 jobs
├── logs                      # 汇总 run 下的 job logs
├── rerun                     # 重跑 run
├── rerun-failed              # 只重跑失败 jobs
└── delete                    # 删除 run

chattea job                   # 查看和重跑 job
├── view                      # 查看 job 详情
├── logs                      # 读取 job 日志
└── rerun                     # 重跑 job

chattea artifact              # 查看和下载 Actions 产物
├── list                      # 列出产物
├── view                      # 查看产物详情
├── download                  # 下载产物 zip
└── delete                    # 删除产物
```

## REST API 映射

```text
chattea runner token       -> POST /repos/{owner}/{repo}/actions/runners/registration-token
chattea runner list        -> GET /repos/{owner}/{repo}/actions/runners
chattea runner view        -> GET /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner edit        -> PATCH /repos/{owner}/{repo}/actions/runners/{runner_id}
chattea runner delete      -> DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}

chattea run list           -> GET /repos/{owner}/{repo}/actions/runs
chattea run view           -> GET /repos/{owner}/{repo}/actions/runs/{run}
chattea run jobs           -> GET /repos/{owner}/{repo}/actions/runs/{run}/jobs
chattea run logs           -> 聚合 run jobs 和 job logs 的本地辅助函数
chattea run rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun
chattea run rerun-failed   -> POST /repos/{owner}/{repo}/actions/runs/{run}/rerun-failed-jobs
chattea run delete         -> DELETE /repos/{owner}/{repo}/actions/runs/{run}

chattea job view           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}
chattea job logs           -> GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs
chattea job rerun          -> POST /repos/{owner}/{repo}/actions/runs/{run}/jobs/{job_id}/rerun

chattea artifact list      -> GET /repos/{owner}/{repo}/actions/artifacts
chattea artifact download  -> GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip
chattea artifact delete    -> DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}
```

`runner setup` 系列命令是本地系统辅助函数：安装或定位 `gitea-runner`，在 ChatTea 运行时目录下写运行器配置，用 Gitea 注册令牌注册运行器，并管理用户级 systemd 服务。

## 运行器配置和运行环境

一次运行器注册至少涉及四类本地状态：

```text
<runner-root>/bin/gitea-runner          # 运行器二进制文件
<runner-root>/config/config.yaml        # 运行器配置
<runner-root>/.runner                   # 注册后的本地 runner 身份文件，敏感，不提交
<runner-root>/work/                     # host 后端执行 job 的工作目录父目录
```

实践中生成的 `config.yaml` 关键字段如下：

```yaml
runner:
  file: .runner
  capacity: 1
  timeout: 3h
  labels:
    - "<runner-label>:host"
cache:
  enabled: false
host:
  workdir_parent: <runner-root>/work
```

这里的 `capacity: 1` 表示单个 runner daemon 同时只接一个 job。要在同一台机器、同一 Unix 用户下并发跑多个 job，实践路径是启动多个 runner root，每个 root 有自己的 `.runner`、`config.yaml` 和 `work/`。本轮真实实践注册了两个 repo-scope runner，它们分别使用不同 label 和不同 root；同一个 workflow 里的两个 job 几乎同时开始，并都成功完成。

当前 ChatTea CLI 的 `runner setup start` 使用固定的用户级 systemd service 名 `chattea-runner.service`，因此它适合管理一个默认 runner。多 runner 并发实践使用的是多个独立 root 加手动启动多个 `gitea-runner daemon -c <config>`。如果要把多 runner 变成长期服务，后续 infra 应支持按 runner name/root 生成多个 service 名。

## Host 后端和 Docker

实践使用的是 host 后端，不依赖 Docker。注册 label 时写成：

```text
<runner-label>:host
```

workflow 中引用时只写冒号前的 label：

```yaml
runs-on: <runner-label>
```

host 后端下，job 以启动 runner daemon 的同一 Unix 用户执行，工作目录位于 `host.workdir_parent` 下。它适合本机可信任务和内网开发验证；如果执行不可信 workflow，需要额外隔离策略。

## Scope：repo、user、org、admin

Gitea runner 注册令牌支持四种 scope。ChatTea CLI 暴露为 `chattea runner token --scope ...` 和 `chattea runner setup register --scope ...`。

| Scope | 注册命令形态 | 本轮实践结果 |
| --- | --- | --- |
| repo | `--scope repo --repo OWNER/REPO` | 两个 repo-scope host runner 被同一个 PR workflow 的两个 job 分别调用，pull_request run 成功 |
| user | `--scope user` | user-scope host runner 被用户仓库 workflow 调用，push run 成功 |
| org | `--scope org --org ORG` | org-scope host runner 被组织仓库 workflow 调用，push run 成功 |
| admin | `--scope admin` | admin-scope host runner 被仓库 workflow 调用，push run 成功 |

实践结论：workflow 是否能调用 runner，核心取决于 runner 的 scope 是否覆盖该仓库，以及 workflow 的 `runs-on` 是否匹配 runner 注册 label。

## 运行器设置

运行工作流前，先在 ChatTea 管理的开发 Gitea 服务上启用 Actions：

```bash
chattea server config set --section actions --key ENABLED --value true -I
chattea server restart
chattea server health
```

安装并注册仓库级运行器：

```bash
chattea runner setup install --force
chattea runner setup register --scope repo --repo gitea_admin/demo --name chattea-runner-demo --labels ubuntu-latest:host
chattea runner setup start
chattea runner setup status
chattea runner list --scope repo --repo gitea_admin/demo
```

运行器设置和维护命令已经在本地 Gitea 实例上实际运行，并保留了终端记录：

![运行器设置和维护 CLI 记录](assets/cli-guide/runner-lifecycle.svg)

默认运行器运行时来自 `CHATTEA_HOME`，使用小写 ChatTea 运行时路径：

```text
~/.chatarch/chattea/runner/bin/gitea-runner
~/.chatarch/chattea/runner/config/config.yaml
~/.chatarch/chattea/runner/work
```

默认标签使用 host 后端：

```text
ubuntu-latest:host
```

这样第一轮真实实践不依赖 Docker 镜像拉取。

## PR 触发工作流

已实践的最小工作流放在 `.gitea/workflows/pr-practice.yml`：

```yaml
name: ChatTea PR Practice
on:
  pull_request:
  push:
jobs:
  practice:
    runs-on: ubuntu-latest
    steps:
      - name: Print context
        run: |
          echo "chattea actions practice"
          echo "event=$GITHUB_EVENT_NAME"
          echo "repo=$GITHUB_REPOSITORY"
      - name: Verify shell
        run: |
          pwd
          echo "ok" > practice-result.txt
          cat practice-result.txt
```

推送 feature 分支并打开 PR 后，用下面命令检查 run：

```bash
chattea run list --repo gitea_admin/demo
chattea run view --repo gitea_admin/demo <run-id>
chattea run jobs --repo gitea_admin/demo <run-id>
chattea job logs --repo gitea_admin/demo <job-id>
```

对应的 Gitea Web 页面和 CLI 日志读取都已经实际验证：

![Gitea Actions run 页面](assets/cli-guide/gitea-actions-run.png)

![Gitea Actions job log 页面](assets/cli-guide/gitea-actions-job-log.png)

![PR 触发的 Actions run、job 和 logs CLI 记录](assets/cli-guide/actions-run-job-log.svg)

## 已验证的本地实践结果

开发服务器上的真实实践覆盖了两组结果。

第一组验证 repo-scope 多 runner 并发和 PR 触发：

```text
scope: repo
runner count: 2
runner backend: host
runner capacity: 1 per daemon
workflow event: pull_request
workflow jobs: runner_a, runner_b
runs-on: <runner-label-a>, <runner-label-b>
job result: both completed successfully
job start: two jobs started within about one second
```

第二组验证 scope 覆盖范围：

```text
user-scope runner -> user-owned repo push workflow -> success
org-scope runner  -> org-owned repo push workflow  -> success
admin-scope runner -> repo push workflow           -> success
```

实践注意：推送新分支后立刻创建 PR，可能和 Gitea 分支可见性刷新产生竞态。如果刚 push 后创建 PR 返回 `404`，短暂等待后用同一个 `head=<feature-branch>` 请求载荷重试即可。

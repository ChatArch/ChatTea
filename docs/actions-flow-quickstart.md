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

开发服务器上的真实实践覆盖了以下结果：

```text
repository: gitea_admin/<actions-practice-repo>
runner: <chattea-runner-name>
pull_request run: completed
job: completed
result: success
log marker: chattea actions practice
```

实践注意：推送新分支后立刻创建 PR，可能和 Gitea 分支可见性刷新产生竞态。如果刚 push 后创建 PR 返回 `404`，短暂等待后用同一个 `head=<feature-branch>` 请求载荷重试即可。

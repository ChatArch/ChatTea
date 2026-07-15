# Actions / Flow（动作 / 流程）快速开始

这篇文档记录 ChatTea 第一版 Actions / Flow 能力。它关注日常自动化最重要的验收闭环：注册 运行器，通过 合并请求 触发 工作流，查看 run/job，并读取日志。

## CLI 能力面

```text
chattea runner
├── token
├── list
├── view
├── edit
├── delete
└── setup
    ├── install
    ├── register
    ├── start
    ├── stop
    ├── status
    ├── logs
    └── doctor

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
chattea run logs           -> 聚合 run jobs 和 job logs 的本地 helper
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

`runner setup` 系列命令是本地系统辅助函数：安装或定位 `gitea-runner`，在 ChatTea 运行时目录下写 运行器 配置，用 Gitea 注册令牌注册 运行器，并管理 用户级 systemd 服务。

## 运行器设置

运行 工作流 前，先在 ChatTea 管理的开发 Gitea 服务上启用 Actions：

```bash
chattea server config set --section actions --key ENABLED --value true -I
chattea server restart
chattea server health
```

安装并注册 仓库 级 运行器：

```bash
chattea runner setup install --force
chattea runner setup register --scope repo --repo gitea_admin/demo --name chattea-runner-demo --labels ubuntu-latest:host
chattea runner setup start
chattea runner list --scope repo --repo gitea_admin/demo
```

默认 运行器 运行时 来自 `CHATTEA_HOME`，使用小写 ChatTea 运行时 路径：

```text
~/.chatarch/chattea/runner/bin/gitea-runner
~/.chatarch/chattea/runner/config/config.yaml
~/.chatarch/chattea/runner/work
```

默认 标签 使用 host 后端：

```text
ubuntu-latest:host
```

这样第一轮开发 冒烟验证不依赖 Docker 镜像拉取。

## PR 触发冒烟验证

最小 工作流 可以放在 `.gitea/workflows/pr-smoke.yml`：

```yaml
name: ChatTea PR Smoke
on:
  pull_request:
  push:
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - name: Print context
        run: |
          echo "chattea actions smoke"
          echo "event=$GITHUB_EVENT_NAME"
          echo "repo=$GITHUB_REPOSITORY"
      - name: Verify shell
        run: |
          pwd
          echo "ok" > smoke-result.txt
          cat smoke-result.txt
```

推送 feature 分支并打开 PR 后，用下面命令检查 run：

```bash
chattea run list --repo gitea_admin/demo
chattea run view --repo gitea_admin/demo 6
chattea run jobs --repo gitea_admin/demo 6
chattea job logs --repo gitea_admin/demo 6
```

## 已验证的本地冒烟结果

开发服务器上的一次真实 冒烟验证 验证了以下结果：

```text
repo: gitea_admin/actions-pr-smoke-20260708025144
runner: chattea-runner-actions-pr-smoke-20260708025144
pull_request run: 6
job: 6
result: success
log marker: chattea actions smoke
```

实践注意：推送新分支后立刻创建 PR，可能和 Gitea 分支可见性刷新产生竞态。如果刚 push 后创建 PR 返回 `404`，短暂等待后用同一个 `head=feature/pr-smoke` 请求载荷 重试即可。

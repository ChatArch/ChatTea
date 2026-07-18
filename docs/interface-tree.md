# ChatTea 接口树

ChatTea 面向 Gitea API 采用接近 GitHub 的资源模型，同时保留 ChatTea 自有命令，用于自托管 / 内部 Gitea 服务管理。

## 当前 CLI 能力面

```text
chattea
├── set-token
├── api
├── auth
│   ├── login
│   ├── status
│   └── token
├── token
│   ├── create
│   ├── list
│   ├── delete
│   └── bootstrap
├── server
│   ├── install
│   ├── init
│   ├── bootstrap
│   ├── serve
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   ├── logs
│   ├── version
│   ├── health
│   └── config
│       ├── path
│       ├── show
│       ├── get
│       └── set
├── repo
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── generate
│   ├── clone
│   └── migrate
├── issue
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── delete
│   ├── comment
│   │   ├── list
│   │   ├── create
│   │   ├── edit
│   │   └── delete
│   ├── label
│   │   ├── add
│   │   └── remove
│   └── assign
│       ├── add
│       └── remove
├── label
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   └── delete
├── milestone
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   └── delete
├── pr
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── reopen
│   ├── merge
│   ├── diff
│   ├── patch
│   ├── commits
│   ├── files
│   ├── comment
│   │   ├── list
│   │   └── create
│   └── review
│       ├── list
│       ├── create
│       └── submit
├── release
│   ├── list
│   ├── view
│   ├── latest
│   ├── by-tag
│   ├── create
│   ├── edit
│   ├── delete
│   └── asset
│       ├── list
│       └── delete
├── project
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── delete
│   ├── column
│   │   ├── list
│   │   ├── create
│   │   ├── edit
│   │   └── delete
│   ├── card
│   │   ├── list
│   │   ├── add
│   │   ├── remove
│   │   └── move
│   └── issue
│       ├── list
│       ├── add
│       ├── remove
│       └── move
├── runner
│   ├── registry
│   │   ├── token
│   │   ├── list
│   │   ├── view
│   │   ├── enable
│   │   ├── disable
│   │   └── delete
│   ├── local
│   │   ├── install
│   │   ├── create
│   │   ├── register
│   │   ├── list
│   │   ├── view
│   │   ├── start
│   │   ├── stop
│   │   ├── restart
│   │   ├── status
│   │   ├── logs
│   │   ├── doctor
│   │   ├── config
│   │   └── remove
│   ├── pool
│   │   ├── create
│   │   ├── start
│   │   ├── stop
│   │   ├── status
│   │   └── remove
│   └── workflow
│       ├── labels
│       ├── example
│       └── check
├── run
│   ├── list
│   ├── view
│   ├── jobs
│   ├── logs
│   ├── rerun
│   ├── rerun-failed
│   └── delete
├── job
│   ├── view
│   ├── logs
│   └── rerun
└── artifact
    ├── list
    ├── view
    ├── download
    └── delete
```

`project issue` 是 `project card` 的兼容别名。新文档和新自动化应使用 `project card`。

## 目标 CLI 方向

带注释的目标树见 [CLI 对齐计划](cli-alignment.md)。当前实现已经覆盖核心 Gitea 资源组：

- `repo`
- `issue`
- `label`
- `milestone`
- `pr`
- `release`
- `project`
- `runner`
- `run`
- `job`
- `artifact`

未来 API 能力只应在存在真实 Gitea 路由 或明确本地实现合约时扩展。候选资源组包括：

- `workflow`
- `secret`
- `variable`
- `status`

ChatTea 自有命令保留为：

- `set-token`：把已有 Gitea 令牌 配置到 ChatEnv 和 仓库本地 git config；
- `server`：管理内部 / 自托管 Gitea 的安装、`app.ini`、进程和健康检查。

## 职责边界

- `set-token`：把默认 Gitea base URL 和 API 令牌 存入 ChatEnv 的 `ChatTea` active 配置档。
- `token create/list/delete/bootstrap`：通过 BasicAuth 创建、列出、删除 Gitea 访问令牌；引导 会创建或轮换托管 令牌，然后配置 ChatTea/Git 凭据。
- `auth login/status/token`：同一套凭据状态上的辅助命名空间。
- `api`：对尚未一等封装的 路由 提供原始 Gitea API passthrough。
- `server install`：默认安装最新 ChatArch 内部 Gitea；`--version` 可固定 发布版本。
- `server init`：为本地 SQLite 支撑的 Gitea 实例创建最小 `app.ini`；监听地址 和 HTTP port 是 CLI init 参数，不是 Env 字段。
- `server serve`：前台运行 Gitea，用于调试或一次性会话。
- `server start/stop/restart/status/logs`：管理固定的 用户级 systemd 服务 `chattea-gitea.service`。
- `server version/health`：检查本地 二进制文件 或已配置的 Gitea HTTP 端点。
- `server config path/show/get/set`：查看或更新托管 Gitea `app.ini`，与 ChatEnv 独立。
- `repo list/view/create/edit/generate`：覆盖基础仓库列表、详情、创建、编辑和从模板生成；`repo create --template` 可创建模板仓库。
- `repo clone`：从已配置 Gitea 实例 clone 仓库，不额外配置 Git 鉴权 header。
- `repo migrate`：从已有 Git clone URL 创建 Gitea 迁移。
- `issue list/view/create/edit/close/reopen/delete`：通过 `/repos/{owner}/{repo}/issues` 路由 管理仓库 问题。
- `issue comment list/create/edit/delete`：通过 问题 评论 路由 管理评论；PR 评论复用 Gitea 问题-评论 模型。
- `issue label add/remove` 和 `issue assign add/remove`：通过 仓库级 问题 路由 管理 标签 和 负责人。
- `label list/view/create/edit/delete`：通过 `/repos/{owner}/{repo}/labels` 管理仓库 标签。
- `milestone list/view/create/edit/close/delete`：通过 `/repos/{owner}/{repo}/milestones` 管理仓库 里程碑。
- `pr list/view/create/edit/close/reopen/merge/diff/patch/commits/files`：通过 `/repos/{owner}/{repo}/pulls` 路由 管理 PR。`pr checkout` 不属于当前能力面。
- `pr review list/create/submit`：通过 `/repos/{owner}/{repo}/pulls/{index}/reviews` 路由 管理 PR review。
- `release list/view/latest/by-tag/create/edit/delete`：通过 `/repos/{owner}/{repo}/releases` 路由 管理 发布版本。
- `release asset list/delete`：查看和删除 发布版本 附件。Multipart 附件 上传 等 HTTP client 支持 上传 后再补。
- `project list/view/create/edit/delete`：管理 仓库级 Gitea Projects。
- `project column list/create/edit/delete`：管理 仓库 项目看板 中的 column。
- `project card list/add/remove/move`：管理 项目列 中的 问题/PR card。
- `runner registry token/list/view/enable/disable/delete`：通过 仓库/org/user/admin 运行器 API 管理 Gitea Actions 服务器侧 runner 记录。
- `runner local install/create/register/list/view/start/stop/restart/status/logs/doctor/config/remove`：安装并运行本机 `gitea-runner` 实例，用于开发和自托管 运行器。
- `runner pool create/start/stop/status/remove`：批量管理同机多个本机 runner 实例。
- `runner workflow labels/example/check`：辅助校验 workflow `runs-on` 和 runner label。
- `run list/view/jobs/logs/rerun/rerun-failed/delete`：查看并控制 Gitea Actions 工作流 run。
- `job view/logs/rerun`：查看 job 元数据、获取日志并通过 parent run 重跑 job。
- `artifact list/view/download/delete`：查看、下载和删除 Actions 产物。

## CLI 到 Python 函数映射

每个 CLI 命令背后都有可导入 Python 函数，集成方不需要 shell out。

```text
chattea set-token             -> chattea.commands.auth.configure_token
chattea auth login            -> chattea.commands.auth.configure_token
chattea auth status           -> chattea.config.load_config
chattea auth token            -> chattea.config.load_config
chattea api                   -> chattea.commands.api.call_api
chattea token create          -> chattea.commands.token.create_access_token
chattea token list            -> chattea.commands.token.list_access_tokens
chattea token delete          -> chattea.commands.token.delete_access_token
chattea token bootstrap       -> chattea.commands.token.bootstrap_access_token
chattea server install        -> chattea.commands.server.install_gitea
chattea server bootstrap      -> chattea.commands.server.bootstrap_gitea_server
chattea server init           -> chattea.commands.server.init_gitea_server
chattea server serve          -> chattea.commands.server.serve_gitea
chattea server start          -> chattea.commands.server.start_gitea_service
chattea server stop           -> chattea.commands.server.stop_gitea_service
chattea server restart        -> chattea.commands.server.restart_gitea_service
chattea server status         -> chattea.commands.server.status_gitea_service
chattea server logs           -> chattea.commands.server.logs_gitea_service
chattea server version        -> chattea.commands.server.gitea_version
chattea server health         -> chattea.commands.server.check_gitea_health
chattea server config path    -> chattea.commands.server.resolve_gitea_config_path
chattea server config show    -> chattea.commands.server.read_gitea_config
chattea server config get     -> chattea.commands.server.get_gitea_config_value
chattea server config set     -> chattea.commands.server.set_gitea_config_value
chattea repo list             -> chattea.commands.repo.list_repositories
chattea repo view             -> chattea.commands.repo.view_repository
chattea repo create           -> chattea.commands.repo.create_repository
chattea repo edit             -> chattea.commands.repo.edit_repository
chattea repo generate         -> chattea.commands.repo.generate_repository
chattea repo clone            -> chattea.commands.repo.clone_repository
chattea repo migrate          -> chattea.commands.repo.migrate_repository
chattea issue list            -> chattea.commands.issue.list_issues
chattea issue view            -> chattea.commands.issue.view_issue
chattea issue create          -> chattea.commands.issue.create_issue
chattea issue edit            -> chattea.commands.issue.edit_issue
chattea issue close           -> chattea.commands.issue.close_issue
chattea issue reopen          -> chattea.commands.issue.reopen_issue
chattea issue delete          -> chattea.commands.issue.delete_issue
chattea issue comment list    -> chattea.commands.issue.list_comments
chattea issue comment create  -> chattea.commands.issue.create_comment
chattea issue comment edit    -> chattea.commands.issue.edit_comment
chattea issue comment delete  -> chattea.commands.issue.delete_comment
chattea issue label add       -> chattea.commands.issue.add_labels
chattea issue label remove    -> chattea.commands.issue.remove_label
chattea issue assign add      -> chattea.commands.issue.add_assignees
chattea issue assign remove   -> chattea.commands.issue.remove_assignees
chattea label list            -> chattea.commands.label.list_labels
chattea label view            -> chattea.commands.label.view_label
chattea label create          -> chattea.commands.label.create_label
chattea label edit            -> chattea.commands.label.edit_label
chattea label delete          -> chattea.commands.label.delete_label
chattea milestone list        -> chattea.commands.milestone.list_milestones
chattea milestone view        -> chattea.commands.milestone.view_milestone
chattea milestone create      -> chattea.commands.milestone.create_milestone
chattea milestone edit        -> chattea.commands.milestone.edit_milestone
chattea milestone close       -> chattea.commands.milestone.close_milestone
chattea milestone delete      -> chattea.commands.milestone.delete_milestone
chattea pr list               -> chattea.commands.pr.list_prs
chattea pr view               -> chattea.commands.pr.view_pr
chattea pr create             -> chattea.commands.pr.create_pr
chattea pr edit               -> chattea.commands.pr.edit_pr
chattea pr close              -> chattea.commands.pr.close_pr
chattea pr reopen             -> chattea.commands.pr.reopen_pr
chattea pr merge              -> chattea.commands.pr.merge_pr
chattea pr diff               -> chattea.commands.pr.diff_pr
chattea pr patch              -> chattea.commands.pr.diff_pr
chattea pr commits            -> chattea.commands.pr.list_commits
chattea pr files              -> chattea.commands.pr.list_files
chattea pr review list        -> chattea.commands.pr.list_reviews
chattea pr review create      -> chattea.commands.pr.create_review
chattea pr review submit      -> chattea.commands.pr.submit_review
chattea release list          -> chattea.commands.release.list_releases
chattea release view          -> chattea.commands.release.view_release
chattea release latest        -> chattea.commands.release.latest_release
chattea release by-tag        -> chattea.commands.release.release_by_tag
chattea release create        -> chattea.commands.release.create_release
chattea release edit          -> chattea.commands.release.edit_release
chattea release delete        -> chattea.commands.release.delete_release
chattea release asset list    -> chattea.commands.release.list_assets
chattea release asset delete  -> chattea.commands.release.delete_asset
chattea runner registry token  -> chattea.commands.runner.create_runner_token
chattea runner registry list   -> chattea.commands.runner.list_registered_runners
chattea runner registry view   -> chattea.commands.runner.view_registered_runner
chattea runner registry enable -> chattea.commands.runner.edit_registered_runner
chattea runner registry disable -> chattea.commands.runner.edit_registered_runner
chattea runner registry delete -> chattea.commands.runner.delete_registered_runner
chattea runner local install   -> chattea.commands.runner.install_runner
chattea runner local create    -> chattea.commands.runner.create_local_runner
chattea runner local register  -> chattea.commands.runner.register_local_runner
chattea runner local list      -> chattea.commands.runner.iter_local_runners
chattea runner local view      -> chattea.commands.runner.local_runner_summary
chattea runner local start     -> chattea.commands.runner.start_runner_service
chattea runner local stop      -> chattea.commands.runner.stop_runner_service
chattea runner local restart   -> chattea.commands.runner.restart_runner_service
chattea runner local status    -> chattea.commands.runner.runner_service_status
chattea runner local logs      -> chattea.commands.runner.runner_service_logs
chattea runner local doctor    -> chattea.commands.runner.local_runner_summary checks
chattea runner local remove    -> chattea.commands.runner.remove_local_runner
chattea runner pool create     -> chattea.commands.runner.create_local_runner / register_local_runner
chattea runner pool status     -> chattea.commands.runner.pool_runners
chattea runner workflow labels -> chattea.commands.runner.extract_runner_labels
chattea runner workflow check  -> chattea.commands.runner.parse_workflow_runs_on
chattea run list              -> chattea.commands.run.list_runs
chattea run view              -> chattea.commands.run.view_run
chattea run jobs              -> chattea.commands.run.list_run_jobs
chattea run logs              -> chattea.commands.run.run_logs
chattea run rerun             -> chattea.commands.run.rerun_run
chattea run rerun-failed      -> chattea.commands.run.rerun_run
chattea run delete            -> chattea.commands.run.delete_run
chattea job view              -> chattea.commands.job.view_job
chattea job logs              -> chattea.commands.job.job_logs
chattea job rerun             -> chattea.commands.job.rerun_job
chattea artifact list         -> chattea.commands.artifact.list_artifacts
chattea artifact view         -> chattea.commands.artifact.view_artifact
chattea artifact download     -> chattea.commands.artifact.download_artifact
chattea artifact delete       -> chattea.commands.artifact.delete_artifact
chattea project list          -> chattea.commands.project.list_projects
chattea project view          -> chattea.commands.project.view_project
chattea project create        -> chattea.commands.project.create_project
chattea project edit          -> chattea.commands.project.edit_project
chattea project delete        -> chattea.commands.project.delete_project
chattea project column list   -> chattea.commands.project.list_columns
chattea project column create -> chattea.commands.project.create_column
chattea project column edit   -> chattea.commands.project.edit_column
chattea project column delete -> chattea.commands.project.delete_column
chattea project card list     -> chattea.commands.project.list_cards
chattea project card add      -> chattea.commands.project.add_card
chattea project card remove   -> chattea.commands.project.remove_card
chattea project card move     -> chattea.commands.project.move_card
```

底层可复用模块也保持可用：

```text
chattea.config  -> ChatTeaEnvConfig, load_config, save_config, set_token
chattea.api     -> GiteaClient, repo_clone_url, repository Project API methods, Actions run/job/artifact/runner API methods
chattea.server  -> install_binary, init_instance, run_gitea, write_user_service
chattea.commands.runner -> runner binary install, registration, user service helpers
```

CLI command module 只应解析参数、调用这些函数 / 类，并渲染结果。

## ChatEnv 边界

正式 ChatEnv 字段为：

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

`CHATTEA_URL` 和旧的 `CHATTEA_GITEA_*` 名称只是 legacy read-only 回退项。Listen address、HTTP port、domain、service name、install version、仓库 name、project ID、问题 ID 和 运行器 ID 都不应成为正式 Env 字段。

## 交互边界

缺少可恢复输入时，命令使用 ChatStyle 的 `CommandSchema`、`CommandField`、`add_interactive_option()` 和 `resolve_command_inputs()`。

- `-i` / `--interactive`：强制交互；
- `-I` / `--no-interactive`：禁用交互并快速失败；
- 默认 `interactive=None`：只有缺少可恢复输入时才自动 prompt。

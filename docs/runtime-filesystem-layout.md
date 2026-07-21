# ChatTea 运行时文件系统与服务边界

这篇文档从文件系统角度解释 ChatTea 托管 Gitea、Actions Runner 和 Pages 时，各类状态分别落在哪里。公开文档只写占位路径和文件形态，不写真实机器路径、真实域名、账号密码、令牌或 `.runner` 内容。

## 核心意图

ChatTea 的 user-level 设计目标是把运行时状态收敛到普通 Unix 用户可控的文件树里：

```text
<chatarch-home>/chattea/   # ChatTea 管理的 Git service、runner、Pages service
<chatdata-home>/           # ChatData 管理的本机 MySQL runtime 和实例
```

这样服务不是散落在 root 级系统目录里；安装、配置、备份、迁移、停启、清理都可以通过 ChatTea、ChatData 和 user-level systemd 来管理。

需要分清三类对象：

```text
Git service     # Gitea Web/API/Git/Actions 调度
Actions worker  # runner daemon，执行 workflow job，不对外 serve HTTP
Pages service   # 静态站点服务，直接 serve 已发布文件
```

从对外 HTTP 服务看，第一版只有两个：Git service 和 Pages service。Actions worker 是后台执行面，不是第三个网站。

## 总览

| 子系统 | user-level unit | 主要目录 | 职责 |
| --- | --- | --- | --- |
| Git service | `chattea-gitea.service` | `<chattea-home>/gitea/` | Gitea 主站、Git 仓库、API、Actions 调度 |
| MySQL backend | `chatdata-mysql-<instance>.service` | `<chatdata-home>/instances/mysql/<instance>/` | Gitea 数据库后端，可由 ChatData 管理 |
| Actions worker | `chattea-runner@<runner-name>.service` | `<chattea-home>/runners/<runner-name>/` | 执行 Gitea Actions job |
| Pages service | `chattea-pages.service` | `<chattea-home>/pages/` | 静态站点 serve 和发布状态 |
| Nginx / Caddy | system service or external edge | deployment-specific | TLS、域名、反向代理、redirect；不属于 ChatTea 核心状态 |

## Git service 文件

Git service 由 Gitea 主进程提供：

```text
chattea-gitea.service
  -> <chattea-home>/bin/gitea web \
       --config <chattea-home>/gitea/custom/conf/app.ini \
       --work-path <chattea-home>/gitea
```

主要文件和目录：

```text
<chattea-home>/bin/gitea
  Gitea binary。

<chattea-home>/gitea/custom/conf/app.ini
  Gitea 主配置，包含 server、repository、database、actions 等段。

<chattea-home>/gitea/data/gitea-repositories/<owner>/<repo>.git/
  bare Git 仓库；Git push/fetch/clone 最终读写这里。

<chattea-home>/gitea/data/
  Gitea app data，例如 attachments、avatars、LFS、queues、sessions、indexers 等。

<chattea-home>/gitea/log/
  Gitea 日志。

<restricted-env-file>
  机器本地受限环境文件，保存管理员密码、API token、base URL 等敏感值。
```

`app.ini` 中和文件位置关系最密切的段：

```ini
[repository]
ROOT = <chattea-home>/gitea/data/gitea-repositories

[server]
APP_DATA_PATH = <chattea-home>/gitea/data
ROOT_URL = <gitea-base-url>
HTTP_ADDR = 127.0.0.1
HTTP_PORT = <gitea-http-port>

[database]
DB_TYPE = mysql
HOST = <chatdata-home>/instances/mysql/<instance>/run/mysql.sock
NAME = gitea
USER = root
PASSWD =
SSL_MODE = disable

[actions]
ENABLED = true
```

Git 仓库内容和 Gitea 元数据不在同一个地方：

- Git object、refs、hooks 在 bare repo 目录；
- 仓库名称、owner、issue、PR、Actions run、runner registry 等元数据在 Gitea 数据库；
- 附件、avatar、LFS、index 等在 Gitea data 目录。

因此备份 Git service 不能只拷贝 repo 目录，也不能只导出 MySQL；要同时覆盖 database、repositories 和 data/custom。

## MySQL backend 文件

长期 Gitea 实例推荐使用 ChatData-managed MySQL，不依赖 Docker。文件形态：

```text
<chatdata-home>/runtimes/mysql/<version>/
  MySQL 官方二进制 runtime。

<chatdata-home>/instances/mysql/<instance>/
  一个本机 MySQL 实例。

<chatdata-home>/instances/mysql/<instance>/data/
  MySQL 数据文件。

<chatdata-home>/instances/mysql/<instance>/run/mysql.sock
  本机 Unix socket，Gitea app.ini 的 database HOST 指向这里。

<chatdata-home>/instances/mysql/<instance>/log/
  MySQL 日志。
```

user-level unit 形态：

```text
chatdata-mysql-<instance>.service
```

Gitea service 应依赖 MySQL service：

```ini
After=network.target chatdata-mysql-<instance>.service
Requires=chatdata-mysql-<instance>.service
```

默认本机开发实例可以使用 socket 上的本机 root 用户；如果需要独立 database user，应通过 ChatData/ChatTea 创建，并把密码放在受限环境或 secret 管理里，不写入公开文档。

## Actions worker 文件

Actions 的状态也分两层：Gitea 服务器侧 registry 和本机 runner root。

Gitea registry 在数据库里，记录：

```text
runner id
runner name
scope: repo / user / org / admin
labels
status / busy / disabled
```

本机 runner root 在文件系统里：

```text
<chattea-home>/runners/<runner-name>/
├── bin/gitea-runner
├── config/config.yaml
├── .runner
└── work/
```

文件职责：

```text
bin/gitea-runner
  runner binary。

config/config.yaml
  runner 配置，包含 capacity、labels、host.workdir_parent 等。

.runner
  注册后的 runner 身份文件，敏感；删除或泄露都会影响该 runner 身份。

work/
  job 工作区父目录。host 后端下，每个 job 会进入独立 task 子目录执行。
```

典型配置片段：

```yaml
runner:
  file: .runner
  capacity: 1
  labels:
    - "ubuntu-latest:host"
cache:
  enabled: false
host:
  workdir_parent: <chattea-home>/runners/<runner-name>/work
```

host 后端的执行边界：

- job 以启动 `chattea-runner@<runner-name>.service` 的同一 Unix 用户运行；
- job 工作目录位于 `<runner-root>/work/<task-id>/hostexecutor`；
- workflow 生成的文件、构建缓存和临时内容先落在 runner workdir；
- host 后端不是强安全沙箱，不适合执行不可信 workflow；
- 如需隔离，需要另设低权限用户、容器、虚拟机或一次性 runner 策略。

Runner scope 决定哪些仓库能用这个 runner：

| Scope | 覆盖范围 | 典型用途 |
| --- | --- | --- |
| `repo` | 一个仓库 | 项目专用构建器 |
| `user` | 当前用户范围 | 个人仓库共享 runner |
| `org` | 一个组织 | 组织项目共享 runner |
| `admin` | 全站 | 管理员提供的全局 runner |

workflow 能否被 runner 接走，取决于两个条件：scope 覆盖该仓库，且 `runs-on` 匹配 runner label。

## Pages service 文件

Pages service 是第二个对外 Web 服务，负责直接 serve 静态站点。建议默认目录：

```text
<chattea-home>/pages/
├── config.yaml
├── sites/
│   └── <owner>/
│       └── <repo>/
│           ├── index.html
│           ├── assets/
│           └── .chattea-pages.json
├── staging/
└── log/
```

文件职责：

```text
config.yaml
  Pages service 配置，例如 listen 地址、pages root、base URL、是否允许目录索引等。

sites/<owner>/<repo>/
  已发布站点。Pages service 直接从这里 serve。

sites/<owner>/<repo>/.chattea-pages.json
  发布元数据，例如 repo、commit、run_id、published_at、source。

staging/
  publish 时的临时目录。发布命令先写 staging，再原子替换 sites 下的目标目录。

log/
  Pages service 日志。
```

发布元数据示例：

```json
{
  "repo": "<owner>/<repo>",
  "commit": "<commit-sha>",
  "run_id": "<actions-run-id>",
  "published_at": "<timestamp>",
  "source": "gitea-actions"
}
```

Pages service 默认只关心文件，不关心源码仓库权限；第一版 Pages 站点按公开静态站点处理。私有 Pages 鉴权、custom domain、resolver 以后单独设计。

## Actions 到 Pages 的文件流

推荐 v0.1 用 Actions 直接发布到 Pages root，而不是先让用户手工维护 `pages` 分支：

```text
1. 用户 push main
2. Gitea 在数据库里创建 workflow run / job
3. runner daemon 从 Git service 领取 job
4. runner 在 <runner-root>/work/<task-id>/hostexecutor checkout 代码
5. workflow 构建 site/ 或 public/
6. workflow 调用 chattea pages publish --repo <owner>/<repo> --source site
7. publish 命令写 <chattea-home>/pages/staging/<tmp>
8. publish 命令原子替换 <chattea-home>/pages/sites/<owner>/<repo>/
9. Pages service 已在 serve，所以 URL 立即可访问
```

这条链路里，Git service、Actions worker 和 Pages service 都是 user-level 可控状态；Nginx 只负责把外部域名转发到对应 service。

## 检查命令

```bash
systemctl --user status chattea-gitea.service
systemctl --user status chatdata-mysql-<instance>.service
systemctl --user status 'chattea-runner@<runner-name>.service'
systemctl --user status chattea-pages.service

chattea server health --url <gitea-loopback-base-url>
chattea runner local status <runner-name>
chattea runner registry list --scope repo --repo <owner>/<repo>
chattea pages status --repo <owner>/<repo>
```

`chattea pages status` 是目标命令，不代表当前已实现。实现前可用 `curl` 和文件检查替代。

## 备份边界

最小备份要覆盖：

```text
Git service:
  <chattea-home>/gitea/custom/conf/app.ini
  <chattea-home>/gitea/data/gitea-repositories/
  <chattea-home>/gitea/data/attachments/ avatars/ lfs/ packages/ queues/ indexers/ 等需要保留的数据
  Gitea database dump

MySQL backend:
  通过 ChatData/MySQL dump 备份，不建议热拷贝 data/ 目录当作唯一备份。

Actions workers:
  <chattea-home>/runners/<runner-name>/config/config.yaml
  <chattea-home>/runners/<runner-name>/.runner 仅在明确需要恢复同一 runner 身份时备份，且必须当作 secret。
  work/ 通常是临时构建目录，不作为长期备份对象。

Pages service:
  <chattea-home>/pages/config.yaml
  <chattea-home>/pages/sites/
  .chattea-pages.json 可用于审计最后发布来源。
```

敏感文件包括受限环境文件、`.runner`、token、密码、证书私钥和任何 git extraHeader。它们只能在机器本地受限位置保存，不进入仓库、公开文档、截图或 CI 日志。

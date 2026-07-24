# Git-backed Pages 分支部署

这篇文档记录 ChatTea Pages 的 GitHub-like 分支部署模型：runner 不直接写 Pages Host 的文件系统，Pages Host 只从配置好的 Git 分支 checkout 静态文件并 serve。

## 一句话结论

```text
runner node != Pages Host
runner build static site -> git push pages branch -> Pages Host git fetch/checkout -> static serve
```

Pages Host 不运行文档构建工具链，不要求 runner 挂载 Host 目录，也不要求 runner SSH/rsync 到 Host。两者唯一需要共享的是 Gitea/Git：

```text
外部 runner 节点 --git push--> Gitea Pages 分支 --git fetch--> Pages Host
```

## 角色边界

| 角色 | 负责 | 需要访问 | 不应该需要 |
| --- | --- | --- | --- |
| Gitea | Git 仓库、Actions 调度、runner registry | runner / Pages Host 都能访问的 Git endpoint | Pages 静态文件 serve root |
| Runner node | 构建 docs、生成静态目录、push Pages 分支 | Gitea、写 Pages 分支的 credential | Pages Host filesystem、SSH、mount、rsync |
| Pages Host syncer | fetch/checkout Pages 分支、原子发布到 serve root | Gitea、读 Pages 分支的 credential | mkdocs/npm/sphinx/Lean/mathlib 等构建工具链 |
| Pages service | serve 已同步的静态文件 | 本机 `pages/sites` | Git 写权限、runner token、构建环境 |

这样部署后，heavy docs build 可以放在资源更强的 runner 节点上，Gitea/Pages Host 只作为控制面和静态托管面。

## 推荐流程

Stable Pages：

```text
push main
  -> Gitea Actions workflow
  -> 外部 runner build site/
  -> runner commit site/ 到 gh-pages 分支
  -> runner push gh-pages 到 Gitea
  -> Pages Host syncer fetch gh-pages
  -> checkout source path
  -> atomic replace pages/sites/<owner>/<repo>/
  -> Pages URL 返回新内容
```

PR preview 可以用同一模型扩展：

```text
pull_request
  -> 外部 runner build site/
  -> runner push dev/pr-<number> 分支，或 push 到 gh-pages 内的 dev/pr-<number>/ 目录
  -> Pages Host syncer 发布到 pages/sites/<owner>/<repo>/dev/pr-<number>/
  -> Gitea bot comment preview URL
```

## Git Pages 配置模型

第一版可以先不做 UI，用 repo-level config 表示 Git Pages 来源：

```json
{
  "repo": "ChatArch/ChatTea",
  "enabled": true,
  "mode": "git-branch",
  "source": {
    "repository": "ChatArch/ChatTea",
    "remote": "http://127.0.0.1:3000/ChatArch/ChatTea.git",
    "branch": "gh-pages",
    "path": "/"
  },
  "channel": "stable",
  "trigger": {
    "mode": "manual"
  },
  "base_url": "http://127.0.0.1:3001"
}
```

产品 UI 可以后续做成：

```text
Repository -> Settings -> Git Pages
```

页面字段对应：source repository、source branch、source path、publish channel、trigger mode、credential reference、last deploy status。

## 鉴权模型

这里有两个 credential，不要混用。

Runner 写权限：

```text
runner -> push gh-pages / dev/pr-N
```

可用 Gitea bot token 或写权限 deploy key。该 credential 放在 Actions secret 中，例如：

```text
CHATTEA_PAGES_PUSH_TOKEN = [REDACTED]
```

Pages Host 读权限：

```text
Pages Host -> fetch gh-pages / dev/pr-N
```

可用只读 deploy key、只读 bot token，或 public repo 无 credential。Pages Host 只需要读取配置里的 Pages 分支，不应该持有 runner 的写权限 token。

## Host-side syncer

Host syncer 只做文件同步，不执行仓库中的脚本：

```text
load repo Git Pages config
  -> validate repo / branch / source path / channel
  -> git clone/fetch configured branch into cache
  -> copy source path to staging
  -> write .chattea-pages-sync.json
  -> atomic replace pages/sites/<owner>/<repo>/<channel>
```

metadata 示例：

```json
{
  "repo": "ChatArch/ChatTea",
  "source_repository": "ChatArch/ChatTea",
  "branch": "gh-pages",
  "source_path": "/",
  "commit": "<pages-branch-commit>",
  "channel": "stable",
  "source": "git-branch",
  "published_at": "<timestamp>"
}
```

安全边界：

- branch、repo、source path、channel 都必须校验；
- `.git` 目录不复制进 serve root；
- syncer 不执行 Pages 分支里的任意命令；
- credential 只通过引用配置，不写入 metadata 或日志；
- 发布时先写 staging，再原子替换目标目录；
- 大型站点需要配置磁盘限制和清理策略。

## Workflow 模板

下面是 branch deploy 的形状。真实项目把 `Build static site` 换成 MkDocs、Sphinx、Docusaurus、Lean/mathlib docs 等构建命令即可。

```yaml
name: Git-backed Pages

on:
  push:
    branches:
      - main

jobs:
  build-and-push-pages:
    runs-on: docs-builder
    env:
      GITEA_BASE_URL: http://127.0.0.1:3000
      PAGES_BRANCH: gh-pages
      CHATTEA_PAGES_PUSH_TOKEN: ${{ secrets.CHATTEA_PAGES_PUSH_TOKEN }}
    steps:
      - name: Clone source repository
        run: |
          set -euo pipefail
          rm -rf source site
          git clone "$GITEA_BASE_URL/$GITHUB_REPOSITORY.git" source
          cd source
          git checkout "$GITHUB_SHA"

      - name: Build static site
        run: |
          set -euo pipefail
          mkdir -p site
          printf '<!doctype html><title>Pages</title><h1>%s</h1>\n' "$GITHUB_REPOSITORY" > site/index.html

      - name: Push static site to gh-pages
        run: |
          set -euo pipefail
          test -n "$CHATTEA_PAGES_PUSH_TOKEN"
          cd site
          git init
          git checkout -B "$PAGES_BRANCH"
          git config user.name "ChatTea Pages Bot"
          git config user.email "chattea-pages@example.invalid"
          git add .
          git commit -m "pages: publish $GITHUB_SHA"
          git remote add origin "$GITEA_BASE_URL/$GITHUB_REPOSITORY.git"
          git \
            -c "http.$GITEA_BASE_URL/.extraHeader=Authorization: token $CHATTEA_PAGES_PUSH_TOKEN" \
            push --force origin "HEAD:$PAGES_BRANCH"
```

注意：这个 job 可以跑在外部 runner node 上。runner 只需要能访问 Gitea，并拥有写 Pages 分支的权限。

## Hitk 实践记录

Hitk 上已经用 ChatTea 自己做过最小实践。这个实践证明了 branch deploy 数据通道可用：

```text
ChatArch/ChatTea main push
  -> Gitea Actions
  -> runner job
  -> push gh-pages
  -> Pages Host sync gh-pages
  -> Pages service 200
```

非敏感证据：

```text
repo: ChatArch/ChatTea
workflow: .gitea/workflows/pages-gh-pages.yml
run: 7
job: 13
runner: hitk-pages-branch
run conclusion: success
generated branch: gh-pages
gh-pages commit: c15237a
Pages URL: http://127.0.0.1:3001/ChatArch/ChatTea/
HTTP status: 200
```

job log 关键行：

```text
Job: publish-gh-pages
HEAD is now at 907a707 ci: publish Pages from gh-pages branch
Switched to a new branch 'gh-pages'
[gh-pages (root-commit) c15237a] pages: publish 907a707...
To http://127.0.0.1:3000/ChatArch/ChatTea.git
 * [new branch]      HEAD -> gh-pages
```

当前 Hitk runtime 里还有一个最小 config-driven slice，用来把一条 repo config 同步成 Pages：

```text
pagesctl.py config-set
pagesctl.py list
pagesctl.py sync --repo ChatArch/ChatTea
pagesctl.py status --repo ChatArch/ChatTea
```

状态输出摘要：

```text
repo: ChatArch/ChatTea
mode: git-branch
source: ChatArch/ChatTea#gh-pages:/
url: http://127.0.0.1:3001/ChatArch/ChatTea/
http_status: 200
last_commit: c15237ad169e...
```

这个 runner 是 validation runner；它证明 Gitea Actions 可以 push Pages branch。正式部署时 runner 可以移动到 Host 外的资源节点，Pages Host 机制不变。

## 当前支持状态

已经验证：

- Gitea Actions 可以生成并 push `gh-pages` 分支；
- Pages Host 可以按配置 checkout/sync `gh-pages`；
- Pages service 可以 serve 同步后的静态站点；
- runner 不需要直接写 `pages/sites`。

仍需产品化：

- 把 runtime prototype 收进正式 `chattea pages ...` CLI；
- 增加 webhook 或 polling 自动 sync；
- 增加 Git Pages 设置页面；
- 把 validation runner 替换成真正 Host 外部 runner 做一次 heavy-build 验收；
- 设计 preview branch / channel 清理策略；
- 私有仓库的 read-only deploy key / credential reference。

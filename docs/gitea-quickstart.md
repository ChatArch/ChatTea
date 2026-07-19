# ChatTea / Gitea 端到端快速开始

这篇 quick start 记录我们已经实践过的 ChatTea + Gitea 流程：从已有 Gitea 服务出发，创建组织、用户、团队成员关系、仓库、本地 git 内容、问题 和 PR。

文档使用占位符，不写真实域名、组织名、用户名、仓库名、令牌、密码、本地路径或运行日志。真实对象和日志只保存在本地项目记录中。

服务暴露模式见 [ChatTea 管理的 Gitea 服务运维](gitea-service-operations.md)。CLI 能力地图见 [ChatTea CLI 能力地图](chattea-cli-tree.md)。

## 占位符约定

| 占位符 | 含义 |
| --- | --- |
| `<gitea-api-base-url>` | ChatTea 使用的 Gitea API/browser base URL |
| `<gitea-public-base-url>` | 浏览器和 git 远端 使用的公网 HTTPS base URL |
| `<restricted-env-file>` | 保存服务凭据的机器本地受限环境文件 |
| `<chatarch-venv>` | 提供 `chattea` 的 Python 环境 |
| `<project-playground>` | 当前实践 project 内部的 `playground/` 工作目录 |
| `<demo-org>` | 示例组织名 |
| `<demo-user>` | 示例用户名 |
| `<demo-repo>` | 示例仓库名 |
| `<demo-owner>/<demo-repo>` | 示例 owner/仓库 |
| `<feature-branch>` | 示例 feature 分支 |
| `<issue-number>` | 示例 问题 编号 |
| `<pr-number>` | 示例 PR 编号 |
| `<comment-id>` | 示例 评论 id |
| `<team-id>` | 示例 team id |

## 0. 准备环境

只在服务机器的私有终端加载受限环境：

```bash
set -a
source <restricted-env-file>
set +a

export CHATTEA=<chatarch-venv>/bin/chattea
export GITEA_API=<gitea-api-base-url>
export GITEA_PUBLIC=<gitea-public-base-url>
```

确认 ChatTea auth 和 API 可达：

```bash
$CHATTEA auth status
$CHATTEA api /version --url "$GITEA_API"
```

如果这台机器还没有 ChatTea-managed Gitea，可以先选择数据库后端再初始化服务：

```bash
# 默认轻量 SQLite：
$CHATTEA server bootstrap -I

# 长期实例建议直接选择 ChatData-managed MySQL：
$CHATTEA server bootstrap \
  --database-backend mysql \
  --mysql-instance default \
  --mysql-version 8.4.6 \
  --admin-password-env GITEA_ADMIN_PASSWORD \
  --start-service \
  -I
```

MySQL 模式不使用 Docker；MySQL 二进制、实例数据和 socket 默认都放在 `~/.chatarch/chatdata/` 下。

## 1. 创建组织

组织创建已经有一等 ChatTea 命令。内部实践默认使用 private organization，避免匿名或非成员看到组织信息：

```bash
export DEMO_ORG=<demo-org>

$CHATTEA org create "$DEMO_ORG" \
  --full-name 'Demo Organization' \
  --description 'Temporary organization for a quickstart run.' \
  --visibility private \
  --url "$GITEA_API" \
  --json-output
```

常用检查：

```bash
$CHATTEA org view "$DEMO_ORG" --url "$GITEA_API"
$CHATTEA org team list "$DEMO_ORG" --url "$GITEA_API" --json-output
```

## 2. 创建用户并加入组织

密码只在私有终端或受限 secret 文件中生成，不写进文档：

```bash
export DEMO_USER=<demo-user>
export DEMO_USER_PASSWORD='[REDACTED]'
```

用户创建也已经有一等 ChatTea 命令。密码通过环境变量传入，不写入命令行参数或文档：

```bash
$CHATTEA user create \
  --username "$DEMO_USER" \
  --email "$DEMO_USER@example.invalid" \
  --password-env DEMO_USER_PASSWORD \
  --full-name 'Demo User' \
  --visibility private \
  --no-must-change-password \
  --url "$GITEA_API" \
  --json-output
```

第一版推荐新建 `developers` team，再把普通用户加入该 team。`DEVELOPERS_TEAM_ID` 从 `org team list` 输出中读取：

```bash
$CHATTEA org team create "$DEMO_ORG" \
  --name developers \
  --permission write \
  --all-repos \
  --can-create-repo \
  --visibility private \
  --url "$GITEA_API" \
  --json-output

$CHATTEA org team list "$DEMO_ORG" --url "$GITEA_API" --json-output

export DEVELOPERS_TEAM_ID=<team-id>

$CHATTEA org team member add "$DEVELOPERS_TEAM_ID" "$DEMO_USER" --url "$GITEA_API"
```

## 3. 创建仓库

仓库创建已经有一等 ChatTea 命令：

```bash
export DEMO_REPO=<demo-repo>
export DEMO_FULL_REPO=$DEMO_ORG/$DEMO_REPO

$CHATTEA repo create \
  --owner "$DEMO_ORG" \
  --name "$DEMO_REPO" \
  --description 'Demo repository.' \
  --public \
  --default-branch main \
  --url "$GITEA_API" \
  --json-output \
  -I
```

常用检查：

```bash
$CHATTEA repo view "$DEMO_FULL_REPO" --url "$GITEA_API" --json-output -I
$CHATTEA repo list --owner "$DEMO_ORG" --limit 10 --url "$GITEA_API" --json-output
```

## 4. 初始化本地 Git 并配置仓库本地令牌

```bash
mkdir -p <project-playground>/chattea-quickstart
cd <project-playground>/chattea-quickstart

git init -b main
git config user.name 'ChatTea Quickstart Bot'
git config user.email 'chattea-quickstart@example.invalid'

cat > README.md <<EOF
# ChatTea Quickstart Demo

Created for \`$DEMO_FULL_REPO\`.
EOF

git add README.md
git commit -m 'docs: add quickstart readme'
```

添加 public 远端：

```bash
git remote add origin "$GITEA_PUBLIC/$DEMO_FULL_REPO"
```

实践校对后，`chattea set-token` 应同时写入 远端 带 `.git` 和不带 `.git` 两种 `extraHeader` key，保证两种 远端 形态都能用于 `git push`。

配置 仓库本地 令牌，不打印 令牌 值：

```bash
CHATARCH_HOME="$PWD/.chatarch" \
  $CHATTEA set-token \
  --base-url "$GITEA_PUBLIC" \
  --token "$GITEA_TOKEN" \
  -I
```

只检查 git config key，不检查 header 值：

```bash
git config --local --name-only --get-regexp '^http\..*\.extraHeader$'
```

推送 main：

```bash
git push -u origin main
```

## 5. 推送 feature 分支

```bash
git switch -c <feature-branch>

cat >> README.md <<'EOF'
- 这行来自 feature 分支，并通过 PR 合并。
EOF

git add README.md
git commit -m 'docs: add quickstart branch note'
git push -u origin <feature-branch>
```

## 6. 问题流程

创建 问题：

```bash
$CHATTEA issue create \
  --repo "$DEMO_FULL_REPO" \
  --title 'Quickstart tracking issue' \
  --body 'Track the end-to-end ChatTea/Gitea quickstart run.' \
  --url "$GITEA_API"
```

查看、评论、列评论、编辑评论：

```bash
export ISSUE=<issue-number>

$CHATTEA issue view "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"

$CHATTEA issue comment create "$ISSUE" \
  --repo "$DEMO_FULL_REPO" \
  --body 'Issue comment from the quickstart demo.' \
  --url "$GITEA_API"

$CHATTEA issue comment list "$ISSUE" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"

export ISSUE_COMMENT=<comment-id>

$CHATTEA issue comment edit "$ISSUE_COMMENT" \
  --repo "$DEMO_FULL_REPO" \
  --issue "$ISSUE" \
  --body 'Edited issue comment from the quickstart demo.' \
  --url "$GITEA_API"
```

关闭、重开、再关闭：

```bash
$CHATTEA issue close "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA issue reopen "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA issue close "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
```

按状态列 问题：

```bash
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state open --url "$GITEA_API"
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state closed --url "$GITEA_API"
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state all --json-output --url "$GITEA_API"
```

## 7. 合并请求流程

创建 PR：

```bash
$CHATTEA pr create \
  --repo "$DEMO_FULL_REPO" \
  --title 'Add quickstart branch note' \
  --head <feature-branch> \
  --base main \
  --body 'Demonstrate PR creation, comments, review, close/reopen, and merge.' \
  --url "$GITEA_API"
```

查看 PR、文件和 commits：

```bash
export PR=<pr-number>

$CHATTEA pr view "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr files "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr commits "$PR" --repo "$DEMO_FULL_REPO" --limit 10 --url "$GITEA_API"
```

评论和 review：

```bash
$CHATTEA pr comment create "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --body 'PR comment from the quickstart demo.' \
  --url "$GITEA_API"

$CHATTEA pr comment list "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"

$CHATTEA pr review create "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --body 'Review comment from the quickstart demo.' \
  --event COMMENT \
  --url "$GITEA_API"

$CHATTEA pr review list "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"
```

关闭、重开并合并：

```bash
$CHATTEA pr close "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr reopen "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"

$CHATTEA pr merge "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --method merge \
  --delete-branch \
  --title 'Merge quickstart branch note' \
  --message 'Merged by ChatTea quickstart demo.' \
  --url "$GITEA_API"
```

合并后同步 main：

```bash
git switch main
git pull --ff-only origin main
```

常用 PR 查询和 diff 命令：

```bash
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state open --url "$GITEA_API"
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state closed --url "$GITEA_API"
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state all --json-output --url "$GITEA_API"
$CHATTEA pr diff "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr patch "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
```

## 基础验证清单

一次基础 ChatTea/Gitea 验证应覆盖：

- `chattea api /version`：确认 API 可达；
- `chattea repo create/list/view`：确认仓库 API；
- `chattea set-token` + `git push`：确认 git transport 鉴权；
- `chattea issue create/view/comment/list/edit/close/reopen`：确认 问题 流程；
- `chattea pr create/view/files/commits/comment/review/close/reopen/merge`：确认 PR 流程；
- 浏览器访问已脱敏的仓库、问题和 PR 页面：确认 UI 渲染。

不要提交真实 `GITEA_TOKEN`、`CHATTEA_TOKEN`、用户密码、证书私钥、git extraHeader 或实践环境 URL。

## 本流程暴露的基础设施校对点

这些不是本轮文档的主目标，但实践过程中已经明确暴露并部分补齐：

- 已补齐：`org create/list/view`、`user create/delete`、`org team create/list/member add/remove`，快速开始不再依赖 raw `chattea api` 创建组织、用户和 team 成员关系；
- 已校对：`repo create --private`，让 public/private 选择更清楚；
- 已校对：`set-token` 同时支持 `https://host/owner/repo` 和 `https://host/owner/repo.git` 两种 远端 形态；
- 仍待补：user view/list/edit、team 编辑/删除/selected-repos 仓库绑定、admin create-as-user 创建 user-owned 仓库等非第一版受管组织流程。

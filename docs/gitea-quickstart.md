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

## 1. 创建组织

当前还没有一等 `chattea org create` 命令，所以先用 raw API：

```bash
export DEMO_ORG=<demo-org>

$CHATTEA api /orgs \
  --method POST \
  --url "$GITEA_API" \
  --data '{
    "username": "<demo-org>",
    "full_name": "Demo Organization",
    "description": "Temporary organization for a quickstart run.",
    "visibility": "public"
  }'
```

常用检查：

```bash
$CHATTEA api /orgs/$DEMO_ORG --url "$GITEA_API"
$CHATTEA api /orgs/$DEMO_ORG/teams --url "$GITEA_API"
```

## 2. 创建用户并加入组织

密码只在私有终端或受限 secret 文件中生成，不写进文档：

```bash
export DEMO_USER=<demo-user>
export DEMO_USER_PASSWORD='[REDACTED]'
```

用环境变量生成请求体，避免把密码硬编码到命令历史或文档里：

```bash
python3 - <<'PY' >/tmp/gitea-demo-user.json
import json
import os

user = os.environ['DEMO_USER']
payload = {
    'username': user,
    'email': f'{user}@example.invalid',
    'full_name': 'Demo User',
    'password': os.environ['DEMO_USER_PASSWORD'],
    'must_change_password': False,
    'send_notify': False,
    'visibility': 'public',
}
print(json.dumps(payload))
PY

$CHATTEA api /admin/users \
  --method POST \
  --url "$GITEA_API" \
  --data "$(cat /tmp/gitea-demo-user.json)"

rm -f /tmp/gitea-demo-user.json
```

把用户加入组织 team。`OWNERS_TEAM_ID` 从实际 team list 输出中读取：

```bash
$CHATTEA api /orgs/$DEMO_ORG/teams --url "$GITEA_API"

export OWNERS_TEAM_ID=<team-id>

$CHATTEA api /teams/$OWNERS_TEAM_ID/members/$DEMO_USER \
  --method PUT \
  --url "$GITEA_API"
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
mkdir -p /tmp/chattea-quickstart
cd /tmp/chattea-quickstart

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

这些不是本轮文档的主目标，但实践过程中已经明确暴露：

- 仍待补：增加一等 `org`、`user`、`team` 命令，减少 raw `chattea api`；
- 本轮已校对：`repo create --private`，让 public/private 选择更清楚；
- 本轮已校对：`set-token` 同时支持 `https://host/owner/repo` 和 `https://host/owner/repo.git` 两种 远端 形态。

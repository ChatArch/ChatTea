# 组织任务账号协作闭环实践

本文记录一条真实 Gitea 协作链路：从组织和账号准备开始，到用户在组织仓库中 `@` 任务账号，再到任务账号回复、处理问题、提交 PR 并 `@` 原用户结束。

本链路已在真实本地 Gitea 环境跑通一次：临时 private 组织、普通发起用户、普通任务账号、private 组织仓库、issue `@任务账号`、任务账号轮询 notification、自动回复 comment、Git over HTTPS push 分支、创建 PR 并 `@原用户` 均成功。

## 目标链路

```text
创建组织和用户
  -> 用户在组织下创建仓库
  -> 用户创建 issue 并 @任务账号
  -> 任务账号感知 notification
  -> 任务账号自动 comment 表示已收到
  -> 任务账号根据 issue 做改动
  -> 任务账号 push 分支并创建 PR
  -> PR 中 @原用户验收
```

## 实践账号和权限模型

第一版先使用普通 Gitea user 作为任务账号，不引入 bot 身份。

- 组织：内部协作组织，默认不对匿名用户公开。
- 普通用户：组织成员，可以在组织下创建仓库和 issue。
- 任务账号：组织成员，用于接收 `@mention`、回复 comment、提交分支和 PR。
- 仓库：默认 private，组织成员可见，非登录和非成员不可见。

账号、组织和仓库可见性的整理见 [账号、组织与可见性模型](account-organization-visibility.md)。

## 本次真实实践结果

本次实践使用临时对象，公开文档只保留脱敏结构：

```text
org: taskflow-<run>
requester: requester-<run>
task account: task-agent-<run>
repo: taskflow-<run>/sample-repo
branch: task-account/<run>
issue: #1
pull request: #2
```

完成的真实步骤：

1. 管理员创建 private 普通用户和 private 任务账号。
2. 管理员创建 private 组织、private developers team，并给 team 配置 write 权限和所有仓库访问。
3. 普通用户创建 private 组织仓库，并通过 Git over HTTPS push 初始 `main`。
4. 普通用户创建 issue，在正文中 `@任务账号`。
5. 任务账号通过 `chattea notification poll` 轮询到 unread issue notification。
6. 任务账号读取 notification thread 和 issue 内容。
7. 任务账号回复 comment：`[自动回复] 已收到，正在处理。`
8. 任务账号标记 notification 为 read。
9. 任务账号通过 Git over HTTPS clone 仓库、创建分支、修改 README、push 分支。
10. 任务账号创建 PR，并在 PR 描述中 `@` 原发起用户验收。

实践中发现并更新的 Infra：

- 新增 `chattea user create/delete`。
- 新增 `chattea org create/list/view`。
- 新增 `chattea org team create/list/member add/remove`。
- 新增 `chattea notification list/view/poll/mark-read`。
- `chattea org team create` 默认补齐常用 repo units，避免 Gitea 报 `units permission should not be empty`。

## 需要验证的问题

1. 组织和仓库的 private/internal 可见性是否满足内部协作：本次已验证组织成员和任务账号可访问 private 组织仓库；匿名/非成员访问还需单独补验证。
2. 普通任务账号被 `@` 后，是否能通过 `/notifications` 感知：已验证。
3. 任务账号是否能读取 issue/comment 并自动回复：已验证。
4. 任务账号是否能通过 Git over HTTPS clone/fetch/push：已验证 clone/push；fetch 与 pull 后续可补一条独立验证。
5. 任务账号是否能创建 PR，并在 PR 中 `@` 原用户：已验证。

## 实践步骤记录

### 1. 准备组织和账号

待实践记录：

```bash
chattea user create --username <user> --email <user@example.invalid> --password-env USER_PASSWORD --visibility private
chattea user create --username <task-account> --email <task@example.invalid> --password-env TASK_PASSWORD --visibility private
chattea org create <org> --visibility private
chattea org team create <org> --name developers --permission write --all-repos --can-create-repo
chattea org team member add <team-id> <user>
chattea org team member add <team-id> <task-account>
```

### 2. 创建组织仓库和 issue

待实践记录：

```bash
chattea repo create <repo> --owner <org> --private
chattea issue create --repo <org>/<repo> --title "<task title>" --body "@<task-account> ..."
```

### 3. 任务账号感知并回复

待实践记录：

```bash
chattea notification poll --status unread --subject issue,pull --max-wait 60
chattea notification view <thread-id>
chattea issue view --repo <org>/<repo> <issue-number>
chattea issue comment create --repo <org>/<repo> <issue-number> --body "[自动回复] 已收到，正在处理。"
chattea notification mark-read <thread-id>
```

### 4. 任务账号提交 PR

待实践记录：

```bash
git clone <org-repo-https-url>
cd <repo>
git switch -c task-account/<task-id>
# 修改代码并提交
git push origin task-account/<task-id>
chattea pr create --repo <org>/<repo> --head task-account/<task-id> --base main --title "<PR title>" --body "@<requester> 已提交，请验收。"
```

## 需要补的 Infra

实践中发现缺口再补。当前预期可能需要补：

- 组织、用户、成员管理命令。
- notification 轮询和 mark-read 命令。
- issue/PR comment 回复命令。
- PR 创建命令或现有 PR 命令补齐。
- Git over HTTPS 凭据配置和脱敏记录。

## 截图和证据

本次已保存脱敏 CLI/Git 实践记录；公开文档只引用结果，不写入本机路径、服务地址、token 或密码。

网页截图后续补充，目标位置：

```text
docs/assets/org-task-account/
```

截图要求：

- 不包含浏览器地址栏。
- 不包含 token、密码、本机路径或真实服务地址。
- 覆盖组织页、组织仓库、issue `@任务账号`、任务账号回复、PR 页面。

当前截图脚本已能通过 API/Git 跑通链路，但 headless Chrome 登录态复用还需要继续稳定化；在截图有效前不把图片作为公开证据。

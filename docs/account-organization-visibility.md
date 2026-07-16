# 账号、组织与可见性模型

本文整理 ChatTea 在内部 Gitea 服务中采用的账号、组织和可见性约定。目标是支撑组织内协作，同时避免匿名或外部用户看到内部内容。

## 第一版推荐模型

```text
一个内部 Gitea 实例
  -> 管理员创建用户和组织
  -> 所有人加入同一个组织
  -> 组织下创建仓库
  -> developers team 覆盖组织内所有仓库
  -> 一个普通任务账号接收 @mention 并提交 PR
```

第一版先不引入 bot 身份，使用普通 user 作为任务账号。这样 notification、comment、Git over HTTPS 和 PR 都沿用普通用户模型，链路更短。

## User / Organization 可见性

Gitea 的 user 和 organization 可见性有三类：

- `public`：公开可见。
- `limited`：面向登录用户可见。
- `private`：更收敛的内部可见性，适合作为内部组织和任务账号的默认值。

ChatTea 在内部协作场景中默认倾向：

```text
user visibility: private
org visibility: private
team visibility: private
```

这解决的是“账号和组织是否对外展示”的问题。它不是仓库权限本身；仓库仍然需要单独设置 private 或团队权限。

## Repository 可见性

当前 Gitea API 的创建仓库选项主要是：

```text
private: true / false
```

也就是说，仓库层面第一版先按两类处理：

- public repo：公开仓库；是否允许匿名访问还受站点级配置影响。
- private repo：只对授权用户、组织成员或团队可见。

如果要实现“内部可见但匿名不可见”的效果，有两种常见方式：

- 组织和仓库都设为 private，通过组织 team 授权成员访问。
- 站点级关闭匿名浏览，再配合 public repo 做“登录后可见”。

第一版实践采用第一种：private org + private repo + developers team。

## Team 权限

组织内共享访问用 team 来表达。第一版推荐：

```text
team: developers
permission: write
includes_all_repositories: true
can_create_org_repo: true
visibility: private
```

这样组织成员可以在组织下创建仓库，也能访问组织内已有仓库。任务账号加入同一个 team 后，可以接收 mention、读取 issue、回复 comment、push 分支和创建 PR。

实践中发现：创建 team 时 Gitea 要求 `units` 不能为空。ChatTea 因此为 `chattea org team create` 增加了默认开发单元：

```text
repo.code, repo.issues, repo.pulls, repo.releases, repo.projects, repo.actions, repo.wiki
```

## Internal / External 边界

这里的 internal / external 主要是平台使用约定：

- internal：登录用户、组织成员、内部任务账号。
- external：匿名访问者或未加入组织的账号。

第一版边界：

```text
匿名用户：看不到 private org/repo 内容
组织成员：可看到组织和授权仓库
任务账号：作为组织成员参与任务处理
非组织成员：看不到 private org/repo 内容
```

## 真实访问矩阵

本轮单独创建一组临时 private 组织、private 仓库、普通成员、任务账号和非成员账号，验证 API 与 Git over HTTPS 访问结果。公开文档只记录脱敏结论，不写入服务地址、token、密码或本机路径。

| 访问主体 | API: org | API: repo | API: issues | Git `ls-remote` | 结论 |
| --- | --- | --- | --- | --- | --- |
| 匿名用户 | 404 | 404 | 404 | 失败 | 无法看到 private 组织、仓库和 issue。 |
| 登录但非组织成员 | 404 | 404 | 404 | 失败 | 无法看到 private 组织、仓库和 issue。 |
| 组织普通成员 | 200 | 200 | 200 | 成功 | 可访问组织仓库、issue 和 Git refs。 |
| 组织任务账号 | 200 | 200 | 200 | 成功 | 具备处理任务所需的读取和 Git 访问能力。 |
| 管理员 | 200 | 200 | 200 | 成功 | 管理员可作为运维兜底访问。 |

本次验证确认：`private org + private repo + developers team` 能满足“匿名不可见、非成员不可见、组织成员和任务账号可协作”的第一版边界。

## ChatTea 命令覆盖

当前围绕这个模型补齐的最小命令：

```bash
chattea user create
chattea user delete
chattea org create
chattea org team create
chattea org team member add
chattea notification poll
chattea notification mark-read
```

这些命令服务于组织任务账号实践链路，不追求一次性覆盖所有 Gitea 管理能力。

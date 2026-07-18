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

## User / Organization / Team 的差异

Gitea 里这三层不是同一类对象：

| 对象 | 它是什么 | 主要决定什么 | 在本实践中的角色 |
| --- | --- | --- | --- |
| User | 可以登录、持有 token、收发 notification、发 issue/comment/PR、执行 Git 操作的账号主体 | “谁在操作”以及操作记录显示成谁 | 普通发起用户和公共任务账号都是普通 user。 |
| Organization | 仓库和团队的归属空间 | “仓库放在哪个协作边界内”以及组织可见性 | 内部协作组织，下面放项目仓库。 |
| Team | Organization 里面的成员和权限集合 | “哪些 user 能访问哪些仓库、具备 read/write/admin 和哪些 repo units” | `developers` team 覆盖所有组织仓库，把普通用户和任务账号授权为 write。 |

因此第一版链路的权限路径是：user 先加入 organization 内的 team，team 再把对应仓库权限授予 user。仅有 private organization 不等于仓库自动可协作；真正让成员能看仓库、改代码、发 PR 的是 team 权限。

## User / Organization / Team 可见性

Gitea 的 user、organization 和 team 可见性有三类：

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

## Owner 全局可见、普通用户相互隔离

如果目标是“一个 Owner 能管理所有受管仓库，但普通用户之间默认互相看不到”，不要把仓库建到用户个人 namespace 下，而是统一放进 Organization，再用 team 做隔离。

推荐层级：

```text
Organization: <org>
  -> Team: Owners
       members: owner / 管理账号
       repos: all repositories
       permission: owner/admin
  -> Team: user-alice
       members: alice
       repos: alice 相关仓库
       permission: write 或 admin
  -> Team: user-bob
       members: bob
       repos: bob 相关仓库
       permission: write 或 admin
  -> Team: project-xxx
       members: 多个协作者
       repos: 共享项目仓库
       permission: write
```

可视范围示例：

| 人 | 所属 Organization | 所属 Team | 能看到哪些受管仓库 | 默认看不到哪些仓库 |
| --- | --- | --- | --- | --- |
| Owner / 管理账号 | `<org>` | `Owners` | `<org>` 下所有仓库 | 无 |
| Alice | `<org>` | `user-alice` | `<org>/alice-*` | `<org>/bob-*`、其他用户仓库 |
| Bob | `<org>` | `user-bob` | `<org>/bob-*` | `<org>/alice-*`、其他用户仓库 |
| Alice + Bob 协作 | `<org>` | `project-xxx` | `<org>/project-xxx` | 各自仍看不到对方个人受管仓库 |

仓库归属规则：

| 仓库 | 归属 | Owner 是否可见 | 对应用户是否可见 | 其他用户是否可见 |
| --- | --- | ---: | ---: | ---: |
| `<org>/alice-notes` | Organization | 是 | Alice 是 | Bob 否 |
| `<org>/bob-notes` | Organization | 是 | Bob 是 | Alice 否 |
| `<org>/project-xxx` | Organization | 是 | 项目成员是 | 非项目成员否 |
| `alice/private-test` | Alice 个人账号 | 默认否，除非 site admin 或 collaborator | Alice 是 | Bob 否 |

因此，“Owner 可见所有受管内容”的前提是：受管仓库必须创建在 Organization 下。个人 namespace 的 private 仓库不属于组织权限模型，组织 Owner 默认管不到。

用户创建仓库有两种入口：

1. 允许用户直接在 Organization 下创建，然后用自动化补 team 绑定；
2. 更推荐第一版用 bot/CLI 代建：用户提出创建请求，系统创建 `<org>/<user>-<repo>`、设置 private、绑定到对应 `user-<name>` team。

第二种方式牺牲一点自由度，但更不容易把仓库误建成个人 private repo，也更容易保证 Owner 全局可见和用户之间隔离。

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

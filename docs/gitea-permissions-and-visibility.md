# Gitea 权限、可见性与访问令牌权限范围

这篇文档说明我们通过 ChatTea 实践过的 Gitea 可见性模型：匿名用户能看到什么，哪些内容需要登录或 令牌，组织、用户、团队和仓库之间如何关联。

真实验证对象和真实 URL 留在本地项目记录中。提交到仓库的文档只保留验证结论和结果形态。

## 两种权限范围不要混淆

实践中容易把两类 scope 混在一起：

1. 可见性 scope：决定对象对谁可见；
2. 访问令牌 scope：决定 令牌 能调用哪些 API。

本文主要讨论可见性 scope；令牌权限范围 在最后单独说明。

## 仓库可见性：public / private

当前 ChatTea `repo create` 和 Gitea 普通创建仓库 API 覆盖的是 public/private：

- `chattea repo create ... --public` 创建 public 仓库；
- `chattea repo create ... --private` 显式创建 private 仓库；
- 不传 `--public` 时仍默认创建 private 仓库；
- Gitea `CreateRepoOption` 和 `EditRepoOption` 暴露的是 `private` 字段；
- API response 里可能出现 `internal: false`，但当前普通 create/edit 路径没有暴露 GitHub Enterprise 风格的 `internal` 仓库 输入。

验证结果形态：

| 仓库形态 | `private` | 匿名 API | 匿名 HTML | 匿名 `git ls-remote` | 令牌 API | 令牌 `git ls-remote` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| public org 仓库 | false | 200 | 200 | 0 | 200 | 0 |
| private org 仓库 | true | 404 | 404 | 128 | 200 | 0 |
| public user 仓库 | false | 200 | 200 | 0 | 200 | 0 |
| private user 仓库 | true | 404 | 404 | 128 | 200 | 0 |

解释：

- 匿名用户可以访问 public 仓库 页面、API 元数据，也可以匿名 clone；
- 匿名用户访问 private 仓库 返回 `404`，不会暴露“对象存在但无权限”；
- 有足够权限的 令牌 可以访问 private 仓库 API，也可以通过 git transport 访问；
- 用户仓库和组织仓库在 public/private 访问行为上一致。

## 用户和组织可见性：public / limited / private

Gitea user 和 org 支持三种 visibility：

- `public`：所有人可见，包括匿名用户；
- `limited`：登录用户可见；
- `private`：只有本人、成员、管理员或其他有权限主体可见。

相关 API 字段：

- `CreateUserOption.Visibility` 支持 `public`、`limited`、`private`；
- `CreateOrgOption.Visibility` 支持 `public`、`limited`、`private`。

用户验证结果形态：

| User visibility | 匿名 API | 匿名 HTML | admin 令牌 API |
| --- | ---: | ---: | ---: |
| public | 200 | 200 | 200 |
| limited | 404 | 404 | 200 |
| private | 404 | 404 | 200 |

组织验证结果形态：

| Organization visibility | 匿名 API | 匿名 HTML | admin 令牌 API |
| --- | ---: | ---: | ---: |
| public | 200 | 200 | 200 |
| limited | 404 | 404 | 200 |
| private | 404 | 404 | 200 |

这里的 令牌 检查使用的是 admin 令牌。普通登录用户是否可见，还取决于它是否是对象本人、组织成员、team 成员或管理员。

## 组织、成员和团队

Gitea 组织权限主要通过 team 管理：

- 一个 org 可以有多个 team；
- 用户加入 team 后成为组织成员；
- team 决定成员对仓库的权限；
- team 可以包含全部仓库，也可以只包含部分仓库；
- team 可以控制成员是否能创建组织仓库；
- team 自身也有 visibility。

quick start 主要使用自动创建的 `Owners` team，它拥有 owner 权限并包含全部组织仓库。

常用 ChatTea 命令形态：

```bash
chattea org team create <demo-org> --name developers --permission write --all-repos --can-create-repo
chattea org team list <demo-org>
chattea org team member add <team-id> <demo-user>
chattea org team member remove <team-id> <demo-user>
```

对应底层 API 仍可通过 `chattea api` 兜底，但第一版实践文档优先使用上面的一等命令。

Team visibility 含义：

- `public`：任何登录用户都能 list 到该 team；
- `limited`：组织成员和组织 owner 能 list；
- `private`：team 成员和组织 owner 能 list；
- team visibility 仍受 org visibility 约束。

## 和 GitHub 的相似点与不同点

相似点：

- 都有用户仓库和组织仓库；
- 都有 public/private 仓库；
- public 仓库 可以匿名浏览和 clone；
- private 仓库 对匿名用户隐藏；
- 组织通过 member 和 team 管理权限；
- 令牌 可以用于 API 和 git transport 鉴权。

不同点和未验证点：

- GitHub Enterprise 常见 `internal` 仓库 visibility，但当前实践使用的 Gitea 普通 create/edit API 没有把它作为输入暴露；
- 当前 ChatTea `repo create` 同时暴露 `--public` 和 `--private`，不传时仍默认 private；
- Gitea user/org 的 `limited` / `private` visibility 和 仓库 visibility 不是同一个概念；
- team visibility 控制的是 team 本身能否被 list，不直接等价于 仓库 visibility。

## 访问令牌权限范围

引导 和管理员 quick start 通常使用较大的 令牌权限范围：

```text
all
```

这适合 引导 和管理员级实践。生产自动化应在确认 API 面之后使用更小 scope。

ChatTea 已支持 令牌 管理：

```bash
chattea token list
chattea token create --help
chattea token bootstrap --help
```

写文档或日志时只写 令牌名 / scope，不写 令牌 值。

## 截图规则

不要提交来自真实 Gitea 实例的截图，如果截图里包含真实域名、对象名、用户名、组织名、仓库名、令牌 或机器路径。需要截图时使用已脱敏对象名和占位域名；真实截图只放在本地项目记录中。

## 本流程暴露的基础设施校对点

权限实践暴露出的第一批管理命令已经补齐：

- `chattea org create/list/view`：避免组织创建和查询依赖 raw API；
- `chattea user create/delete`：用于受控本地 Gitea 实践环境中的管理员建号和清理；
- `chattea org team create/list/member add/member remove`：覆盖组织 team 创建和成员维护；
- `chattea notification list/view/poll/mark-read`：覆盖任务账号被 `@mention` 后的轮询入口。

后续仍需单独确认或补齐的点：

- 如果以后要支持 GitHub Enterprise 风格的 `internal` 仓库，需要先确认当前 Gitea 源码/API 是否存在稳定入口；
- 如果要让普通用户完全自助创建“受管私有仓库”，需要在 `Organization + Team` 模型上增加 bot/CLI 创建流程，避免用户误建到个人 namespace；
- 如果要管理 selected-repos team，还需要补 team 仓库绑定的增删命令。

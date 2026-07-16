# Runner 多实例第一版实现方案

这篇文档记录 Runner 独立 PR 的第一版实现边界。目标是把现有偏单实例的 `chattea runner setup`，升级为可以管理多个本机 runner、多个注册 scope、多个 service，并且能在真实 Gitea 环境里调试和验收的基础设施。

## 背景

当前已实践确认：

- host 后端可用，不必依赖 Docker；
- 同一机器、同一 Unix 用户下可以启动多个 runner root 和多个 runner daemon；
- 两个 repo-scope host runner 可以被同一个 PR workflow 的两个 job 并发调用；
- user-scope、org-scope、admin-scope runner 都能通过 workflow `runs-on` label 被调用；
- 现有 `chattea runner setup start` 只管理固定的 `chattea-runner.service`，适合默认单 runner，不适合长期维护多 runner。

因此第一版重点不是再证明 runner 能跑，而是把已经跑通的方式固化成 ChatTea CLI 和可维护的本机状态模型。

## 设计原则

- **Registry 和 Local 分层**：Gitea 服务器上的 runner 记录，和本机 runner root/service/log 是两层状态，CLI 需要分开表达。
- **兼容旧命令**：现有 `chattea runner token/list/view/edit/delete/setup ...` 保留，作为兼容入口；新功能放到更清晰的子树下。
- **按 name 管理本机实例**：每个 runner 有稳定 name、root、config、`.runner`、workdir 和 service。
- **先支持 host 后端**：第一版把已实践的 host/native 后端做扎实；Docker 后端只保留配置入口和后续验证空间。
- **真实环境调试**：接口实现后必须在真实 Gitea 服务上注册、启动、跑 workflow，并把结果回写到本地实践记录。

## 第一版目标 CLI 树

```text
chattea runner
├── registry                         # Gitea 服务器上的 runner 记录
│   ├── token                        # 获取 repo/user/org/admin 注册令牌
│   ├── list                         # 按 scope 列出服务器端 runner
│   ├── view                         # 查看 runner 详情
│   ├── enable                       # 启用 runner
│   ├── disable                      # 禁用 runner
│   └── delete                       # 删除服务器端 runner 记录
│
├── local                            # 本机 runner 实例管理
│   ├── install                      # 安装或更新 gitea-runner 二进制文件
│   ├── create                       # 创建本机 runner root 和 config，不注册
│   ├── register                     # 注册本机 runner 到 Gitea
│   ├── list                         # 列出本机已管理 runner instances
│   ├── view                         # 查看某个本机 runner 的 root/config/service 状态
│   ├── start                        # 启动某个 runner service
│   ├── stop                         # 停止某个 runner service
│   ├── restart                      # 重启某个 runner service
│   ├── status                       # 查看某个 runner service 状态
│   ├── logs                         # 查看某个 runner service 日志
│   ├── doctor                       # 检查 binary/config/.runner/workdir/API 连通性
│   ├── config                       # 查看或修改 runner config.yaml
│   │   ├── show                     # 显示脱敏后的 config 摘要
│   │   ├── set-labels               # 更新 labels
│   │   ├── set-capacity             # 更新 capacity
│   │   ├── set-workdir              # 更新 host.workdir_parent
│   │   └── set-backend              # 更新 label backend 后缀
│   ├── unregister                   # 删除服务器端注册记录，保留本地 root
│   └── remove                       # 删除本地 runner root/service，需要确认
│
├── pool                             # 多 runner 批量管理
│   ├── create                       # 创建 N 个 runner，适合同机并发
│   ├── scale                        # 调整 pool runner 数量
│   ├── start                        # 启动整个 pool
│   ├── stop                         # 停止整个 pool
│   ├── status                       # 查看 pool 状态
│   ├── logs                         # 查看或聚合 pool 日志
│   └── remove                       # 删除整个 pool，需要确认
│
└── workflow                         # workflow 与 runner label 辅助
    ├── labels                       # 列出当前可用于 runs-on 的 labels
    ├── example                      # 输出 runs-on 示例
    └── check                        # 检查 workflow runs-on 是否有匹配 runner
```

兼容入口保留为：

```text
chattea runner token    -> chattea runner registry token
chattea runner list     -> chattea runner registry list
chattea runner view     -> chattea runner registry view
chattea runner edit     -> chattea runner registry enable/disable
chattea runner delete   -> chattea runner registry delete
chattea runner setup    -> 默认单 runner 的兼容入口
```

## 本机状态模型

第一版使用每个 runner 独立 root：

```text
<chattea-home>/runners/<runner-name>/
├── bin/gitea-runner
├── config/config.yaml
├── .runner
└── work/
```

service 名使用 runner name：

```text
chattea-runner@<runner-name>.service
```

这样同一机器上可以明确管理多个 runner：

```bash
chattea runner local create lean-a --label lean-a --backend host
chattea runner local register lean-a --scope repo --repo OWNER/REPO
chattea runner local start lean-a
chattea runner local status lean-a
chattea runner local logs lean-a
```

## 注册 scope

第一版 `local register` 要显式支持四种 scope：

```bash
chattea runner local register repo-a \
  --scope repo \
  --repo OWNER/REPO \
  --label repo-a \
  --backend host

chattea runner local register user-a \
  --scope user \
  --label user-a \
  --backend host

chattea runner local register org-a \
  --scope org \
  --org ORG \
  --label org-a \
  --backend host

chattea runner local register admin-a \
  --scope admin \
  --label admin-a \
  --backend host
```

workflow 能否调用 runner，取决于两件事：

```text
1. runner scope 是否覆盖当前仓库；
2. workflow 的 runs-on 是否匹配 runner label。
```

## Host 后端约定

CLI 中用户传入的 label 不带 backend 后缀：

```bash
chattea runner local create lean-native --label lean-native --backend host
```

写入 runner config 时变成：

```yaml
runner:
  labels:
    - "lean-native:host"
host:
  workdir_parent: <runner-root>/work
```

workflow 中仍然只写 label：

```yaml
jobs:
  prove:
    runs-on: lean-native
    steps:
      - run: echo ok
```

## Pool 第一版

Pool 是多个本机 runner instance 的薄封装。第一版先支持固定命名：

```text
<pool-name>-1
<pool-name>-2
<pool-name>-3
```

示例：

```bash
chattea runner pool create lean --count 3 \
  --scope repo \
  --repo OWNER/REPO \
  --label lean-native \
  --backend host

chattea runner pool start lean
chattea runner pool status lean
chattea runner pool stop lean
```

第一版的 pool 可以先做 create/start/stop/status/remove；`scale` 可以作为本 PR 的第二步实现，避免一次性引入太多删除和迁移逻辑。

## 验收计划

第一版实现后按下面顺序验证：

1. 本地单元测试：覆盖 runner root 计算、config 生成、service 名、registry alias、pool name 生成。
2. 文档构建：`mkdocs build --strict`。
3. 真实 Gitea 调试：
   - 创建两个 repo-scope host runner；
   - 用不同 label 注册并启动；
   - 在实践仓库里提交 workflow；
   - 触发 PR workflow；
   - 确认两个 job 分别被不同 runner 接走且成功。
4. Scope 回归：至少抽查 user/org/admin 中一类，确认新 CLI 注册路径可用。
5. 记录回写：本地 project progress 记录命令、结果、失败点和后续 infra 缺口；公开 PR 文档只保留脱敏命令和结论。

## 非目标

第一版不解决以下问题：

- 不把 Docker 后端作为已验证事实；
- 不承诺不可信 workflow 的隔离安全；
- 不把 token、`.runner`、真实服务 URL、机器本地路径写入公开文档；
- 不移除旧的 `chattea runner setup` 命令；
- 不一次性实现所有 org/user/team CLI 封装。

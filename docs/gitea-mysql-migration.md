# Gitea MySQL 后端安装与迁移

ChatTea 现在支持两种 Gitea 数据库后端：

- `sqlite3`：默认值，最轻量，适合本机开发和临时实践。
- `mysql`：通过 ChatData 管理 MySQL 二进制 runtime，不使用 Docker，适合需要长期运行和后续扩展的实例。

新实例推荐在安装/初始化时直接选择 MySQL；已有 SQLite 实例再使用迁移命令切换。

## 新装时直接选择 MySQL

最短路径是用 `server bootstrap` 一次完成 Gitea binary、MySQL runtime、app.ini、管理员和 token 初始化：

```bash
export GITEA_ADMIN_PASSWORD='[REDACTED]'

chattea server bootstrap \
  --database-backend mysql \
  --mysql-instance default \
  --mysql-version 8.4.6 \
  --mysql-database gitea \
  --admin-password-env GITEA_ADMIN_PASSWORD \
  --start-service \
  -I
```

这个流程会做这些事：

1. 下载或复用 ChatArch Gitea binary。
2. 通过 ChatData 下载或复用 MySQL 官方二进制 tarball。
3. 初始化 `default` MySQL 实例，写入 user-level systemd unit。
4. 启动 `chatdata-mysql-default.service`，等待 `mysqladmin ping` 通过。
5. 创建 `gitea` database，默认 `CHARACTER SET utf8mb4 COLLATE utf8mb4_bin`。
6. 生成 MySQL 版 Gitea `app.ini`。
7. 运行 `gitea migrate` 初始化 schema。
8. 创建初始管理员和 token，并写入 ChatTea 凭据。
9. 启动 `chattea-gitea.service`。

生成的 Gitea service 会自动依赖 ChatData MySQL service：

```ini
After=network.target chatdata-mysql-default.service
Requires=chatdata-mysql-default.service
```

这样重启机器后，Gitea 会等本机 MySQL service 先起来。

## 分步安装

如果不想一次 bootstrap，可以先准备二进制和数据库后端：

```bash
chattea server install \
  --database-backend mysql \
  --mysql-instance default \
  --mysql-version 8.4.6 \
  -I
```

再初始化 Gitea 配置：

```bash
chattea server init \
  --database-backend mysql \
  --mysql-instance default \
  --mysql-version 8.4.6 \
  --mysql-database gitea \
  -I
```

最后按需创建管理员和 token，或直接使用 `server bootstrap`。

## 默认路径

ChatData-managed MySQL 不写系统目录，默认都在 ChatArch home 下：

```text
~/.chatarch/chatdata/runtimes/mysql/8.4.6/
~/.chatarch/chatdata/instances/mysql/default/
~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
```

ChatTea 写入 Gitea `app.ini` 的数据库段类似：

```ini
[database]
DB_TYPE = mysql
HOST = ~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
NAME = gitea
USER = root
PASSWD =
SSL_MODE = disable
LOG_SQL = false
```

默认本机 ChatData MySQL 用 Unix socket 和本机 root 用户；如果需要密码，通过 `--mysql-password-env` 传入环境变量名，不要把密码写进命令行或文档。

## 已有 SQLite 实例的备份能力

Gitea binary 自带这些相关命令：

```bash
gitea dump          # 整站 dump：数据库、仓库、custom、data 等
gitea dump-repo     # 仓库级导出
gitea restore-repo  # 仓库级导入
gitea migrate       # 对当前 app.ini 指向的 DB 执行 schema migration
```

当前没有一条对称的整站 `gitea restore` 命令。因此 ChatTea 的 SQLite -> MySQL 第一版迁移不走“整站 restore”，而是利用：

```bash
gitea dump --database mysql --skip-repository ...
```

Gitea 会把 SQLite 数据库导出成 MySQL SQL，dump 包里包含 `gitea-db.sql`。ChatTea 再把这个 SQL 导入 MySQL，然后切换 `app.ini` 的 `[database]`。

ChatTea 封装了备份命令：

```bash
chattea server backup dump --database sqlite3
chattea server backup dump --database mysql --db-only
```

`--db-only` 会跳过仓库、日志、custom、LFS、附件、packages 和 index，适合生成迁移 SQL；完整备份不要加 `--db-only`。

## 已有 SQLite 实例迁移

先建议做完整备份：

```bash
chattea server stop
chattea server backup dump \
  --database sqlite3 \
  --output /path/to/gitea-pre-mysql-full.zip
```

然后迁移：

```bash
chattea server migrate mysql \
  --yes \
  --mysql-instance default \
  --mysql-version 8.4.6 \
  --database gitea \
  --stop-service \
  --restart-service
```

迁移命令做这些事：

1. 可选停止 `chattea-gitea.service`。
2. 运行 `gitea dump --database mysql --db-only` 生成 MySQL SQL。
3. 从 dump zip 里抽取 `gitea-db.sql`。
4. 通过 ChatData 创建 MySQL database。
5. 导入 `gitea-db.sql`。
6. 备份 `app.ini` 为 `app.ini.backup-<timestamp>`。
7. 更新 `[database]` 为 MySQL。
8. 运行 `gitea migrate` 验证并补齐 schema。
9. 可选重启 `chattea-gitea.service`。

命令默认要求 `--yes`，避免误切当前服务后端。

## 迁移后检查

```bash
chattea server config get --section database --key DB_TYPE -I
chattea server health
chattea repo list --limit 5
chatdata mysql client query \
  --name default \
  --version 8.4.6 \
  --database gitea \
  --sql 'SELECT COUNT(*) AS repos FROM repository;'
```

期望：

- `DB_TYPE` 是 `mysql`；
- `chattea server health` 返回 ok；
- `chattea repo list` 能列出原有仓库；
- MySQL 中 `repository`、`user` 等表有数据。

## 回滚

迁移不会删除原来的 SQLite 文件。回滚时：

1. 停 Gitea：`chattea server stop`。
2. 把 `app.ini.backup-<timestamp>` 复制回 `app.ini`。
3. 启动 Gitea：`chattea server start`。
4. 检查 `DB_TYPE` 是否回到 `sqlite3`。

MySQL database 可以保留作为迁移证据，确认不再需要后再手动删除。

# Gitea MySQL 后端迁移

ChatTea 默认初始化的 Gitea 后端是 SQLite：`[database] DB_TYPE = sqlite3`，数据库文件在 `CHATTEA_WORK_PATH/data/gitea.db`。本页记录第一版把现有 ChatTea-managed Gitea 从 SQLite 迁移到 ChatData-managed MySQL 的流程。

## 当前备份和导入能力

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

## 准备 MySQL

MySQL 由 ChatData 管理，不使用 Docker，不写系统目录：

```bash
chatdata mysql doctor
chatdata mysql install --version 8.4.6
chatdata mysql instance init --name default --version 8.4.6 --port 3307
chatdata mysql service install --name default --version 8.4.6
chatdata mysql service start --name default
chatdata mysql client ping --name default --version 8.4.6
```

默认路径：

```text
~/.chatarch/chatdata/runtimes/mysql/8.4.6/
~/.chatarch/chatdata/instances/mysql/default/
~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
```

ChatData 创建 database 时默认使用：

```sql
CHARACTER SET utf8mb4 COLLATE utf8mb4_bin
```

这是为了避免 Gitea 对大小写不敏感 collation 的 warning。

## 迁移命令

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
7. 更新 `[database]`：

```ini
DB_TYPE = mysql
HOST = ~/.chatarch/chatdata/instances/mysql/default/run/mysql.sock
NAME = gitea
USER = root
PASSWD =
SSL_MODE = disable
LOG_SQL = false
```

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

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
6. 如果传了 `--mysql-user` / `--mysql-password-env`，创建对应 MySQL 用户并授权该 database。
7. 生成 MySQL 版 Gitea `app.ini`。
8. 运行 `gitea migrate` 初始化 schema。
9. 创建初始管理员和 token，并写入 ChatTea 凭据。
10. 启动 `chattea-gitea.service`。

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

默认本机 ChatData MySQL 用 Unix socket 和无密码的本机 root 用户。需要 service user 时，请同时传 `--mysql-user gitea --mysql-password-env MYSQL_PASSWORD`；不要给默认 root 用户配置密码，因为 ChatData 本地开发实例的 root 用户已经存在，ChatTea 不会隐式修改 root 密码。

MySQL backend 需要 ChatData `0.1.1` 或更新版本；`0.1.1` 提供了 ChatTea 依赖的 database user 创建/授权能力。

## 真实用例：本机 Gitea 切到 MySQL

本轮真实环境使用的是已有 ChatTea-managed Gitea，所以走的是“先迁移，再把安装流程补进 CLI”的路线。最终状态可用以下证据复现：

```bash
chattea server config get --section database --key DB_TYPE -I
# mysql

chattea server health
# ok: http://127.0.0.1:3000 (1.0.0)

systemctl --user is-active chatdata-mysql-default.service
# active

systemctl --user is-active chattea-gitea.service
# active
```

Gitea user service 已经能识别 MySQL socket，并依赖 ChatData MySQL service：

```ini
[Unit]
Description=ChatTea managed Gitea service
After=network.target chatdata-mysql-default.service
Requires=chatdata-mysql-default.service
```

这个改动只影响后端和 service 依赖，Gitea Web 页面本身没有视觉变化，所以当前文档不放页面截图；验证以后端配置、服务依赖、health 和 MySQL 表数据为准。

完整流程记录在 project 笔记中：

```text
/home/zhihong/Playground/projects/07-18-chattea-mysql-backend/progress.md
```

## 低停机 side-by-side 迁移

更稳的生产迁移不是直接改当前 `app.ini`，而是在独立目录先起一个 shadow Gitea：

```text
旧服务：127.0.0.1:3000 / chattea-gitea.service / 当前 work path
新服务：127.0.0.1:3001 / chattea-gitea-shadow.service / 独立 work path
入口：nginx proxy_pass 最后从 3000 切到 3001
```

第一轮可以在线预热：

```bash
export NEW_HOME="$HOME/.chatarch/chattea-shadow"
export NEW_WORK="$NEW_HOME/gitea"
export NEW_CONFIG="$NEW_WORK/custom/conf/app.ini"
export NEW_SERVICE="chattea-gitea-shadow.service"
export NEW_DB="gitea_shadow"
export MYSQL_PASSWORD='[REDACTED]'

# 先写 shadow app.ini 和 MySQL database/user，但暂不跑 gitea migrate，避免导入 dump 前创建空 schema。
chattea server init \
  --work-path "$NEW_WORK" \
  --config "$NEW_CONFIG" \
  --base-url https://gitea.local.wzhecnu.cn \
  --http-port 3001 \
  --database-backend mysql \
  --mysql-database "$NEW_DB" \
  --mysql-user gitea \
  --mysql-password-env MYSQL_PASSWORD \
  --skip-gitea-migrate \
  --force \
  -I

# 复制仓库和附件类文件。保留 shadow app.ini，不复制旧 SQLite DB、日志和备份。
rsync -a --delete \
  --exclude 'custom/conf/app.ini' \
  --exclude 'data/gitea.db' \
  --exclude 'log/' \
  --exclude 'backups/' \
  "$CHATTEA_WORK_PATH/" "$NEW_WORK/"

# 导出当前 DB 为 MySQL SQL，并导入 shadow database。
chattea server backup dump --database mysql --db-only --output "$NEW_WORK/backups/preheat-db.zip"
unzip -p "$NEW_WORK/backups/preheat-db.zip" '*gitea-db.sql' > "$NEW_WORK/backups/gitea-db.sql"
chatdata mysql client import --database "$NEW_DB" --file "$NEW_WORK/backups/gitea-db.sql"

# 对 shadow config 指向的新库跑 schema migration，然后启动 shadow service。
"$CHATTEA_BINARY" --config "$NEW_CONFIG" --work-path "$NEW_WORK" migrate
chattea server start --config "$NEW_CONFIG" --work-path "$NEW_WORK" --service-name "$NEW_SERVICE"
chattea server health --url http://127.0.0.1:3001
```

最终切换窗口只做增量和入口切换：

1. 停旧服务或进入维护窗口，阻止新写入。
2. 对旧 work path 再做一次 `rsync -a --delete` 到 shadow work path。
3. 对旧实例再做一次最新 `chattea server backup dump --database mysql --db-only`。
4. 导入到一个新的空目标库，或清空 shadow 目标库后重新导入。
5. 对 shadow 跑 `gitea migrate`，确认 `chattea server health --url http://127.0.0.1:3001` 正常。
6. 修改 nginx `proxy_pass`，把 `127.0.0.1:3000` 切到 `127.0.0.1:3001`，`nginx -t` 后 reload。
7. 保留旧服务、旧目录和旧数据库一段时间；回滚就是把 nginx upstream 切回 3000。

这个方案不能保证真正 0 停机，因为 SQLite 或旧 Gitea 写入期间没有可靠双写到新 MySQL 的链路；但可以把停写窗口压缩到“最终增量 rsync + 最新 DB dump/import + nginx reload”的时间。

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
5. 创建并授权目标 MySQL 用户；默认 root 用户必须保持无密码，带密码时请使用非 root service user。
6. 导入 `gitea-db.sql`。
7. 备份 `app.ini` 为 `app.ini.backup-<timestamp>`。
8. 更新 `[database]` 为 MySQL。
9. 运行 `gitea migrate` 验证并补齐 schema。
10. 可选重启 `chattea-gitea.service`。

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

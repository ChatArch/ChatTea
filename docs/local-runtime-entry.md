# 本地运行时统一入口

这篇文档定义 ChatTea 在只有一个对外域名或一个对外端口时，如何用内部入口层把 Git、Pages、备份控制面和后续 Bot 管理面整合到同一个 URI 空间。它记录的是可复用的运行时设计和当前机器的脱敏实践，不包含令牌、密码、证书私钥或真实凭据内容。

## 目标

生产环境有时只能暴露一个公网端口，或者只希望用户记住一个入口。在这种约束下，ChatTea 仍然把内部服务拆清楚，但在入口层统一路由：

```text
https://<public-host>/git/      -> Git service
https://<public-host>/pages/    -> Pages service
https://<public-host>/control/  -> backup/control service
https://<public-host>/-/status  -> runtime aggregate status
```

内部可以有多个 loopback 端口，外部只需要一个 host/port。系统 nginx 或公网网关只做一层很薄的转发，真正的服务整合由 ChatTea 内部 entry 完成。

## 组件边界

```text
system nginx / public gateway
  listen: 80/443 或生产环境允许暴露的唯一端口
  role: TLS、公网入口、转发到 ChatTea entry

chattea-entry.service
  listen: 127.0.0.1:<entry-port>
  role: 内部 nginx，统一 /git /pages /control /-/status

chattea-gitea.service
  listen: 127.0.0.1:3000
  role: Gitea Git service、API、Actions 调度、runner registry

chattea-pages.service
  listen: 127.0.0.1:3001
  role: 静态 Pages service，serve 已发布站点

chattea-control.service
  listen: 127.0.0.1:3002
  role: backup/control/status，本地机器侧管理能力

chattea-runner@<name>.service
  role: Actions worker，不是对外 Web 服务
```

Runner 不需要独立公网端口。它通过 Gitea 获取 job、在本机执行 build/publish，再把日志和状态回写到 Gitea。Runner 状态应在 `/control/` 或 `/-/status` 里展示，而不是单独暴露成一个网站。

## ChatUp、ChatTea、ChatData 的关系

这套实践至少涉及两个用户可见包：

- **ChatUp**：适合做安装、bootstrap、system/user service 编排和机器初始化入口。
- **ChatTea**：负责 Gitea、Pages、runner、backup/control 和 entry 的运行时语义。

如果 MySQL 由 ChatUp 安装并托管，用户不一定需要直接感知 ChatData。但实现上可以继续复用 ChatData 的 MySQL runtime 能力：

```text
user command: ChatUp bootstrap/install
  -> prepares MySQL runtime, if requested
  -> installs or starts ChatTea runtime stack
  -> ChatTea consumes the resulting DB/socket/config
```

因此文档和 CLI 可以把 MySQL 描述为 ChatTea stack 的一个 backend，而不是要求用户单独操作 ChatData。ChatData 是否参与是实现细节；用户视角是“ChatUp 起环境，ChatTea 管 Git/Pages/control runtime”。

## URI 路由表

第一版 path-based 路由：

| URI | Upstream | 说明 |
| --- | --- | --- |
| `/` | entry landing | 显示 Git、Pages、Control 入口 |
| `/-/health` | entry local | entry 自身健康检查 |
| `/-/status` | control | 汇总 Git、Pages、Control、Runner 状态 |
| `/git/` | `127.0.0.1:3000` | Gitea Web/API/Git HTTP |
| `/pages/` | `127.0.0.1:3001` | Pages service root |
| `/pages/<owner>/<repo>/` | `127.0.0.1:3001/<owner>/<repo>/` | 已发布静态站点 |
| `/control/` | `127.0.0.1:3002` | backup/control API |
| `/control/backups` | `127.0.0.1:3002/control/backups` | 备份列表和受控创建入口 |
| `/bot/` | future upstream | 后续 Bot webhook/control surface |

如果后续需要非可信多租户 Pages，仍建议使用不同 host 隔离 origin，例如 `git.<domain>` 和 `pages.<domain>`。单 host path mode 更适合内网可信环境或生产入口受限场景。

## 内部 entry nginx

内部 entry 是 user-level nginx，不直接监听 80/443。示例监听端口为 `<entry-port>`，实际部署应选择一个空闲 loopback 端口：

```nginx
server {
    listen 127.0.0.1:<entry-port>;
    server_name _;

    location = /-/health {
        default_type text/plain;
        return 200 "ok\n";
    }

    location = /-/status {
        proxy_pass http://127.0.0.1:3002/control/status;
    }

    location = /git {
        return 308 /git/;
    }

    location /git/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header X-Forwarded-Prefix /git;
        proxy_set_header X-Forwarded-Host $host;
        proxy_redirect / /git/;
        proxy_cookie_path / /git/;
    }

    location = /pages {
        return 308 /pages/;
    }

    location /pages/ {
        proxy_pass http://127.0.0.1:3001/;
    }

    location = /control {
        return 308 /control/;
    }

    location /control/ {
        proxy_pass http://127.0.0.1:3002/control/;
    }
}
```

Gitea 原生子路径部署最好让 Gitea 自己的 `ROOT_URL` 带上 `/git/`。如果当前机器还要保留已有 direct Gitea vhost，可以先用 entry nginx 的 `proxy_redirect`、`proxy_cookie_path` 和 HTML asset rewrite 作为实践兼容层；正式产品化时再决定是否切换 Gitea 的 canonical root。

## 外部 nginx

系统 nginx 或公网网关只需要把一个 host 转到 entry：

```nginx
server {
    listen 443 ssl;
    server_name <public-host>;

    location / {
        proxy_pass http://127.0.0.1:<entry-port>;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
    }
}
```

这样外部仍然只暴露一个域名和一个端口，内部可以继续演进 Git、Pages、Control、Bot 等服务。

## Control service 最小能力

`chattea-control.service` 第一版只做安全的本地管理入口：

```text
GET  /control/health   -> control health
GET  /control/status   -> service + HTTP aggregate status
GET  /control/backups  -> backup manifest list
POST /control/backups  -> dry-run backup manifest, guarded by confirmation header
```

完整备份仍然需要机器侧能力，不能只靠 Gitea Web API 完成。Control service 只是把本地 backend 包装成可管理任务：

```text
control API
  -> local backup job
  -> gitea dump / database dump / file archive / checksums
  -> <chattea-home>/backups/<backup-id>/manifest.json
```

第一版不要开放无确认的 restore API。恢复流程应保留 CLI 或本地显式确认门槛。

## 当前机器实践结果

当前机器已经完成最小实践：

```text
chattea-gitea.service    active, 127.0.0.1:3000
chattea-pages.service    active, 127.0.0.1:3001
chattea-control.service  active, 127.0.0.1:3002
chattea-entry.service    active, 127.0.0.1:<entry-port>
```

当前机器的 `3080` 已被其他服务占用，因此 entry 选择了另一个空闲 loopback 端口。系统 nginx 把集成入口 host 转发到 entry 后，以下路径均已验证：

```text
/                  -> ChatTea Runtime Entry landing
/-/health          -> 200 ok
/-/status          -> Git / Pages / Control / Runner aggregate JSON
/control/          -> control service routes
/control/backups   -> backup manifest list
/pages/<owner>/<repo>/ -> 已发布 ChatTea 文档站点
/git/              -> Gitea Web UI through entry
/git/<owner>/<repo>.git/info/refs?service=git-upload-pack -> Git smart HTTP
```

并创建过一个 dry-run backup manifest，用来证明 control plane 可以通过统一入口创建受控备份记录。它不是完整实例备份，只是后续 real backup job 的接口占位和权限检查。

## 验证清单

```bash
systemctl --user is-active \
  chattea-gitea.service \
  chattea-pages.service \
  chattea-control.service \
  chattea-entry.service

curl -I http://127.0.0.1:<entry-port>/-/health
curl http://127.0.0.1:<entry-port>/-/status
curl http://127.0.0.1:<entry-port>/control/backups
curl -I http://127.0.0.1:<entry-port>/pages/<owner>/<repo>/
curl -I 'http://127.0.0.1:<entry-port>/git/<owner>/<repo>.git/info/refs?service=git-upload-pack'

sudo nginx -t
```

如果外部 host 已经转发到 entry，再验证：

```bash
curl -I https://<public-host>/-/health
curl https://<public-host>/-/status
curl -I https://<public-host>/pages/<owner>/<repo>/
curl -I 'https://<public-host>/git/<owner>/<repo>.git/info/refs?service=git-upload-pack'
```

## 后续产品化

- 将 control service 和 entry nginx 配置生成纳入 `chattea` CLI。
- 由 ChatUp 提供更高层的 bootstrap 命令，按需安装 MySQL backend 并拉起 ChatTea stack。
- 把 backup dry-run 替换为真实 `gitea dump`、DB dump 和文件归档 job。
- 为 restore 增加 maintenance mode、完整性校验和本地确认门槛。
- 决定 Gitea 是否正式切到 `/git/` canonical root，或继续保留 direct host 兼容入口。
- 规划 `/bot/` 的 webhook/control surface，但不要让它影响 Git/Pages/Control 的第一版验收。

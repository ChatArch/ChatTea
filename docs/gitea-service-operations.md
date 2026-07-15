# ChatTea 管理的 Gitea 服务运维

这篇文档记录 ChatTea 管理 Gitea 服务时的运维模式。正文面向公开仓库，因此只使用占位符，不写真实域名、机器路径、账号、密码、令牌、证书私钥路径或内部部署地址。

真实值应保存在机器本地项目记录或受限环境文件中，不应进入仓库文档、截图、PR 描述或 CI 日志。

## 占位符约定

| 占位符 | 含义 |
| --- | --- |
| `<workspace>` | 服务机器上的本地工作区根目录 |
| `<chatarch-home>` | ChatTea 管理运行时文件的 ChatArch home |
| `<chatarch-venv>` | 提供 `chattea` / `chatenv` 的 Python 环境 |
| `<gitea-public-base-url>` | 对浏览器、API、git 访问暴露的公网 HTTPS 地址 |
| `<gitea-local-base-url>` | local nginx 暴露的本地 HTTPS 地址 |
| `<gitea-loopback-base-url>` | Gitea 本地 upstream，通常是 `http://127.0.0.1:<port>` |
| `<service>.local.example.invalid` | 示例 local 服务域名 |
| `<service>.public.example.invalid` | 示例 public 服务域名 |
| `<restricted-env-file>` | 机器本地的受限环境文件，保存服务凭据 |
| `<gitea-bootstrap-project>` | 本次服务搭建对应的本地项目记录 |

## 访问入口形态

提交到仓库的文档只写占位符：

```text
公网 HTTPS:      <gitea-public-base-url>
本地 HTTPS:      <gitea-local-base-url>
本机 upstream:   <gitea-loopback-base-url>
版本检查:        <gitea-public-base-url>/api/v1/version
```

版本检查的返回形态应类似：

```json
{"version":"<gitea-version>"}
```

## 托管文件位置

公开文档中只写路径形态，不写真实机器路径：

```text
Gitea binary:          <chatarch-home>/chattea/bin/gitea
Gitea work path:       <chatarch-home>/chattea/gitea
Gitea config:          <chatarch-home>/chattea/gitea/custom/conf/app.ini
Runner binary:         <chatarch-home>/chattea/runner/bin/gitea-runner
Runner config:         <chatarch-home>/chattea/runner/config/config.yaml
Credential env file:   <restricted-env-file>
Bootstrap project log: <workspace>/projects/<gitea-bootstrap-project>/
```

受限环境文件应使用 `0600` 权限。不要把密码、令牌、证书私钥、`git config http.*.extraHeader` 写进文档或截图。

## 启动和管理服务

只在服务机器的私有终端加载受限环境：

```bash
set -a
source <restricted-env-file>
set +a
```

使用 ChatTea 管理 Gitea 生命周期：

```bash
<chatarch-venv>/bin/chattea server status
<chatarch-venv>/bin/chattea server start
<chatarch-venv>/bin/chattea server restart
<chatarch-venv>/bin/chattea server logs --lines 100
<chatarch-venv>/bin/chattea server health --url <gitea-loopback-base-url>
```

服务以 user-level systemd 运行：

```bash
systemctl --user status chattea-gitea.service
systemctl --user status chattea-runner.service
systemctl --user restart chattea-gitea.service
systemctl --user restart chattea-runner.service
```

Gitea 进程形态：

```bash
<chatarch-home>/chattea/bin/gitea web \
  --config <chatarch-home>/chattea/gitea/custom/conf/app.ini \
  --work-path <chatarch-home>/chattea/gitea
```

运行器进程形态：

```bash
<chatarch-home>/chattea/runner/bin/gitea-runner daemon \
  -c <chatarch-home>/chattea/runner/config/config.yaml
```

默认 ChatTea 运维面管理的是一个 `chattea-runner.service`。本轮实践证明，同一台机器、同一 Unix 用户下可以运行多个 host runner；做法是为每个 runner 使用独立 `<runner-root>`、独立 `.runner`、独立 `config.yaml` 和独立 `work/`，再分别启动 `gitea-runner daemon -c <config>`。当前 CLI 还没有为多 runner 生成多个长期 systemd service 名，这是后续 infra 项。

如果 `chattea-gitea.service` 已经占用端口，不要再在同一端口前台运行 `gitea web`。

## 管理员凭据

管理员用户名、密码和 访问令牌 位于受限环境文件和 ChatEnv 中。先查看脱敏状态：

```bash
<chatarch-venv>/bin/chatenv cat -t chattea
<chatarch-venv>/bin/chattea auth status
```

如果人工登录浏览器需要账号密码，只能在服务机器的私有终端读取：

```bash
set -a
source <restricted-env-file>
set +a

printf 'Gitea URL: %s\n' "$GITEA_BASE_URL"
printf 'Username: %s\n' "$GITEA_USERNAME"
printf 'Password: %s\n' "$GITEA_PASSWORD"
```

`GITEA_TOKEN` 和 `CHATTEA_TOKEN` 同样是敏感值，只用于 API、ChatTea 和 git transport 鉴权。

如果需要重置或重新对齐凭据，优先使用 引导 项目里的脚本，不手工编辑 env 文件：

```bash
python3 <workspace>/projects/<gitea-bootstrap-project>/scripts/configure_gitea_account_env.py
bash <workspace>/projects/<gitea-bootstrap-project>/scripts/verify_gitea_env.sh
```

## 本地 Nginx 和公网入口

Gitea 自身应只监听 loopback upstream：

```text
127.0.0.1:<gitea-http-port>
```

local nginx 负责暴露本地域名：

```text
nginx site file: <nginx-single-sites-dir>/<service>-local.conf
server_name:     <service>.local.example.invalid
upstream:        <gitea-loopback-base-url>
```

SSL 使用共享通配证书：

```text
certificate: <nginx-cert-dir>/<wildcard-cert-name>/fullchain.pem
private key: <nginx-cert-dir>/<wildcard-cert-name>/privkey.pem
```

证书应覆盖 local 和 public 两类通配域名，例如：

```text
*.local.example.invalid
*.public.example.invalid
```

普通服务不需要额外配置 public Gitea nginx `server_name`。约定模式是：

1. local nginx 显式服务 `<service>.local.example.invalid`；
2. wildcard DNS 覆盖 `<service>.public.example.invalid`；
3. 已有 public-entry 层把公网 HTTPS 转回 local nginx；
4. 运维只验证 public URL，不为每个服务新增 DNS、证书或 tunnel 配置。

验证命令形态：

```bash
curl --noproxy '*' -sS \
  --resolve <service>.local.example.invalid:443:127.0.0.1 \
  https://<service>.local.example.invalid/api/v1/version

curl -sS https://<service>.public.example.invalid/api/v1/version
```

## 截图和日志规则

不要提交暴露真实域名、仓库名、用户名、组织名、令牌 或机器路径的截图。需要 review 页面效果时，使用已脱敏数据和占位域名；真实截图只保存在本地项目记录中。

## 运维规则

- 公开文档不写私有或内部服务的真实 URL，使用占位符。
- 不提交密码、令牌、git extraHeader、DNS secret 或证书私钥内容。
- 普通 Gitea 服务接入不修改 public-entry / tunnel 配置，除非任务明确要求。
- wildcard DNS 已覆盖时，不为单个服务新增 DNS 记录。
- 共享 wildcard 证书已覆盖时，不为单个服务申请证书。
- 修改 `ROOT_URL` 和 `CHATTEA_BASE_URL` 要谨慎，因为它们会影响 clone URL 和 API client。

# ChatTea From Scratch Quick Start

This document explains the full bootstrap model from a blank machine to a usable ChatArch Gitea instance managed by ChatTea.

The key idea is that there are two phases:

```text
A. Blank machine -> local Gitea service, initial admin, initial token
B. Token configured -> ChatTea manages repositories, projects, PRs, issues, releases, and Actions through Gitea REST APIs
```

Do not assume an existing Gitea service for the from-scratch path. Existing-Gitea flows are secondary.

## Command Roles

```text
chattea server bootstrap
  Blank machine path. Install/init/start local ChatArch Gitea, create initial admin, generate initial token, configure ChatTea, and verify the API.

chattea token bootstrap
  Existing Gitea path. Given an existing Gitea service and username/password, create an access token through REST and configure ChatTea.

chattea set-token
  Existing token path. Given an already-created token, save it into ChatTea/ChatEnv and optionally repo-local git config.
```

Current implementation status:

```text
Implemented in PR #5:
  chattea set-token
  chattea token create/list/delete/bootstrap
  chattea server bootstrap
  centralized token resolution

First-phase server bootstrap status:
  local install/init/admin/token/credential chain implemented
  service start is optional with --start-service
  rerun hardening reuses an existing configured token when the local admin token name already exists
```

## Server vs Client Boundary

ChatTea has two roles in the full workflow.

```text
Server side
  The machine that runs the managed ChatArch Gitea service.
  It owns the Gitea binary, app.ini, database, repositories, logs, initial admin, and generated access token.

Client side
  Any machine that wants to manage that Gitea service through ChatTea.
  It does not need the Gitea binary or app.ini. It only needs ChatTea, a base URL, and an access token.
```

From-scratch bootstrap is server-side:

```text
chattea server bootstrap
  Runs on the server machine.
  Creates the local Gitea service, initial admin, and initial access token.
  Writes the generated token to the server machine's ChatEnv profile.
```

Client setup starts after a token exists:

```text
chattea set-token
  Runs on a client machine when a token is already available.
  Writes CHATTEA_BASE_URL and CHATTEA_TOKEN to that client's ChatEnv profile.

chattea token bootstrap
  Runs on a client machine when the Gitea service and username/password already exist.
  Uses BasicAuth to create a token through REST, then writes it to that client's ChatEnv profile.
```

This means a blank server does not begin as a client. It first bootstraps the service locally with `server bootstrap`. After that, the same machine can also act as a client because it has `CHATTEA_BASE_URL` and `CHATTEA_TOKEN` configured. Other developer or CI machines become clients by running `set-token` or `token bootstrap` against the server URL.

First-phase scope is one target Gitea instance:

```text
In scope:
  One server-side Gitea instance.
  One active client target per machine/profile.
  Same-machine server+client and remote-client-to-server flows.

Out of scope for now:
  Managing multiple Gitea instances from one active ChatTea profile.
  Instance switching UX.
  Multi-service naming and lifecycle isolation.
```

## A. Blank Machine To Local Gitea

Target one-command entry:

```bash
export GITEA_ADMIN_PASSWORD='[REDACTED]'

chattea server bootstrap \
  --base-url http://127.0.0.1:3000 \
  --admin-user gitea_admin \
  --admin-email admin@example.com \
  --admin-password-env GITEA_ADMIN_PASSWORD
```

`server bootstrap` should compose these steps.

### A1. Install ChatArch Gitea

Backed by ChatTea local install logic:

```text
chattea server install
```

Expected behavior:

```text
Download latest ChatArch internal Gitea release
Verify .sha256 checksum
Install binary under CHATTEA_HOME/bin/gitea
```

Default paths come from ChatEnv or built-in defaults:

```text
CHATTEA_HOME      -> ~/.chatarch/chattea
CHATTEA_BINARY    -> ~/.chatarch/chattea/bin/gitea
```

### A2. Create app.ini

Backed by:

```text
chattea server init
```

Expected output file:

```text
CHATTEA_CONFIG
```

Default path:

```text
~/.chatarch/chattea/gitea/custom/conf/app.ini
```

Important config defaults:

```text
[server]
ROOT_URL = http://127.0.0.1:3000/
HTTP_ADDR = 127.0.0.1
HTTP_PORT = 3000

[database]
DB_TYPE = sqlite3

[security]
INSTALL_LOCK = true

[service]
DISABLE_REGISTRATION = true
REGISTER_EMAIL_CONFIRM = false
```

Registration is disabled by default. The initial admin is created by local Gitea admin CLI, not by open registration.

### A3. Initialize Database

Backed by local Gitea binary:

```text
gitea migrate --config app.ini --work-path ...
```

This does not require an existing account or token.

### A4. Create Initial Admin

This solves the chicken-and-egg problem.

The first admin user cannot be created by a normal REST API call because REST admin APIs require existing admin authentication. Therefore the from-scratch path must use local Gitea admin CLI:

```bash
gitea admin user create \
  --config app.ini \
  --work-path ... \
  --username gitea_admin \
  --password '[REDACTED]' \
  --email admin@example.com \
  --admin \
  --must-change-password=false
```

In ChatTea, the password should come from:

```text
--admin-password-env GITEA_ADMIN_PASSWORD
```

The password must not be saved into ChatEnv and must not be printed.

### A5. Generate Initial Access Token

The first token should also be generated through local Gitea admin CLI:

```bash
gitea admin user generate-access-token \
  --config app.ini \
  --work-path ... \
  --username gitea_admin \
  --token-name default \
  --scopes all \
  --raw
```

Initial bootstrap uses the highest built-in Gitea token scope by default:

```text
all
```

Default token name:

```text
default
```

After the full chain is stable, scopes can be tightened.

If a rerun sees the same local admin token name already exists, `server bootstrap` reuses the currently configured `CHATTEA_TOKEN` for the same base URL instead of printing or requiring the raw token again. If no matching configured token exists, it fails with a clear instruction to use a different `--token-name` or run `chattea set-token` with the existing token.

### A6. Configure ChatTea Credentials

This is the `set-token` step.

Conceptually:

```bash
chattea set-token \
  --base-url http://127.0.0.1:3000 \
  --token '[REDACTED]'
```

In implementation, `server bootstrap` should call the same Python credential function directly instead of shelling out.

### A7. Start And Verify

Start local Gitea using the supported local mode:

```text
server start on Linux user-level systemd
server serve or managed foreground process for local smoke tests
```

Then verify:

```text
GET /api/v1/version
GET /api/v1/user
```

`/version` proves the service is reachable. `/user` proves the generated token is valid.

## B. After Token Configuration

After `set-token` or `server bootstrap`, subsequent commands should not use username/password. They should use the configured token.

Examples:

```bash
chattea repo list
chattea repo create --name demo
chattea project list --repo gitea_admin/demo
chattea api /user
```

Token resolution order:

```text
1. Explicit CLI token argument, if provided
2. Current repo-local git config, if available
3. ChatTea ChatEnv active profile
4. Clear failure if authentication is required and no token exists
```

## set-token And ChatEnv Relationship

`set-token` and ChatEnv are connected. They are not two independent config systems.

Current ChatTea flow:

```text
chattea set-token
  -> chattea.commands.auth.configure_token
  -> chattea.credentials.configure_token
  -> chattea.config.set_token / save_config
  -> chatenv EnvStore active ChatTea profile
```

So the long-lived ChatTea config is stored through ChatEnv fields:

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

`set-token` additionally configures repo-local git authentication when it can detect the current Gitea git remote:

```text
git config --local http.<gitea-repo-url>.extraHeader "Authorization: Basic ..."
```

This git config part is extra convenience for git transport. It does not replace ChatEnv.

Summary:

```text
ChatEnv stores stable ChatTea config.
set-token writes into ChatEnv and optionally writes repo-local git config.
repo-local git config helps git pull/push.
Gitea API commands read the token through the centralized token resolution path.
```

## What Should Not Go Into ChatEnv

Do not store these as stable ChatEnv fields:

```text
admin password
one-time bootstrap password
repo id
project id
issue id
runner id
default admin token raw output before set-token
```

Admin password is only a bootstrap input. Access token becomes long-lived only after it is written as `CHATTEA_TOKEN`.

## Existing Remote Gitea Flow

If a Gitea service and user already exist, use:

```bash
export GITEA_PASSWORD='[REDACTED]'

chattea token bootstrap \
  --base-url https://gitea.example.com \
  --username gitea_admin \
  --password-env GITEA_PASSWORD
```

By default, `token bootstrap` is rerunnable for the managed token name. If `default` already exists, it deletes that named token and creates a new one before calling `set-token`. Use `--if-exists error` when rotation should be blocked.

This uses Gitea REST API:

```text
POST /api/v1/users/{username}/tokens
```

Then it calls the same credential path as `set-token`.

This is not the blank-machine path; it is the existing-Gitea path.

## Existing Token Flow

If the user already has a token from Gitea Web UI:

```bash
chattea set-token \
  --base-url https://gitea.example.com \
  --token '[REDACTED]'
```

This is the shortest path, but it assumes the token already exists.

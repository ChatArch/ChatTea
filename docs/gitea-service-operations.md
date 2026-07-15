# ChatTea-managed Gitea Service Operations

This page records the operating pattern for a ChatTea-managed Gitea service. It is written for public repository docs, so it uses placeholders instead of real hostnames, machine paths, account names, passwords, tokens, private keys, or internal deployment URLs.

Keep concrete values in the machine-local project record or restricted env files. Do not commit them to repository documentation, screenshots, PR descriptions, or CI logs.

## Placeholder Convention

| Placeholder | Meaning |
| --- | --- |
| `<workspace>` | Local workspace root on the service host |
| `<chatarch-home>` | Local ChatArch runtime home for ChatTea-managed files |
| `<chatarch-venv>` | Python environment that provides `chattea` and `chatenv` |
| `<gitea-public-base-url>` | Public HTTPS browser/API base URL |
| `<gitea-local-base-url>` | Local HTTPS base URL served by local nginx |
| `<gitea-loopback-base-url>` | Loopback upstream URL, usually `http://127.0.0.1:<port>` |
| `<service>.local.example.invalid` | Mock local service hostname |
| `<service>.public.example.invalid` | Mock public service hostname |
| `<restricted-env-file>` | Machine-local env file that stores private service credentials |
| `<gitea-bootstrap-project>` | Local project record for this service setup |

## Endpoint Shape

Committed docs should use placeholder URLs:

```text
Public HTTPS:      <gitea-public-base-url>
Local HTTPS:       <gitea-local-base-url>
Loopback upstream: <gitea-loopback-base-url>
Version check:     <gitea-public-base-url>/api/v1/version
```

Expected version check response shape:

```json
{"version":"<gitea-version>"}
```

## Managed Paths

Use placeholders for concrete paths:

```text
Gitea binary:          <chatarch-home>/chattea/bin/gitea
Gitea work path:       <chatarch-home>/chattea/gitea
Gitea config:          <chatarch-home>/chattea/gitea/custom/conf/app.ini
Runner binary:         <chatarch-home>/chattea/runner/bin/gitea-runner
Runner config:         <chatarch-home>/chattea/runner/config/config.yaml
Credential env file:   <restricted-env-file>
Bootstrap project log: <workspace>/projects/<gitea-bootstrap-project>/
```

The credential env file should be mode `0600`. Never copy passwords, tokens, certificate private keys, or `git config http.*.extraHeader` values into docs or screenshots.

## Start And Manage The Service

Load the restricted environment only on the service host:

```bash
set -a
source <restricted-env-file>
set +a
```

Use ChatTea for the managed Gitea lifecycle:

```bash
<chatarch-venv>/bin/chattea server status
<chatarch-venv>/bin/chattea server start
<chatarch-venv>/bin/chattea server restart
<chatarch-venv>/bin/chattea server logs --lines 100
<chatarch-venv>/bin/chattea server health --url <gitea-loopback-base-url>
```

The service uses user-level systemd units:

```bash
systemctl --user status chattea-gitea.service
systemctl --user status chattea-runner.service
systemctl --user restart chattea-gitea.service
systemctl --user restart chattea-runner.service
```

Expected Gitea process shape:

```bash
<chatarch-home>/chattea/bin/gitea web \
  --config <chatarch-home>/chattea/gitea/custom/conf/app.ini \
  --work-path <chatarch-home>/chattea/gitea
```

Expected runner process shape:

```bash
<chatarch-home>/chattea/runner/bin/gitea-runner daemon \
  -c <chatarch-home>/chattea/runner/config/config.yaml
```

Do not run a foreground `gitea web` process on the same port while `chattea-gitea.service` is already running.

## Admin Credentials

The admin username, password, and access token live in restricted env files and ChatEnv. Inspect masked state first:

```bash
<chatarch-venv>/bin/chatenv cat -t chattea
<chatarch-venv>/bin/chattea auth status
```

If a human needs browser login credentials, read them only in a private terminal on the service host:

```bash
set -a
source <restricted-env-file>
set +a

printf 'Gitea URL: %s\n' "$GITEA_BASE_URL"
printf 'Username: %s\n' "$GITEA_USERNAME"
printf 'Password: %s\n' "$GITEA_PASSWORD"
```

`GITEA_TOKEN` and `CHATTEA_TOKEN` are also stored there for API and ChatTea access. Treat them as secrets.

If credentials need to be reset or re-aligned with ChatEnv, use the bootstrap project scripts rather than editing env files by hand:

```bash
python3 <workspace>/projects/<gitea-bootstrap-project>/scripts/configure_gitea_account_env.py
bash <workspace>/projects/<gitea-bootstrap-project>/scripts/verify_gitea_env.sh
```

## Local Nginx And Public Exposure

Gitea should listen only on a loopback upstream:

```text
127.0.0.1:<gitea-http-port>
```

Local nginx exposes it through a local hostname:

```text
nginx site file: <nginx-single-sites-dir>/<service>-local.conf
server_name:     <service>.local.example.invalid
upstream:        <gitea-loopback-base-url>
```

SSL should use a shared wildcard certificate:

```text
certificate: <nginx-cert-dir>/<wildcard-cert-name>/fullchain.pem
private key: <nginx-cert-dir>/<wildcard-cert-name>/privkey.pem
```

The certificate should cover both local and public wildcard zones, for example:

```text
*.local.example.invalid
*.public.example.invalid
```

For ordinary services, do not add a separate public Gitea nginx `server_name`. The pattern is:

1. local nginx explicitly serves `<service>.local.example.invalid`;
2. wildcard DNS covers `<service>.public.example.invalid`;
3. the existing public-entry layer routes public HTTPS back to local nginx;
4. operators verify the public URL instead of adding per-service DNS records or per-service certificates.

Verification command shape:

```bash
curl --noproxy '*' -sS \
  --resolve <service>.local.example.invalid:443:127.0.0.1 \
  https://<service>.local.example.invalid/api/v1/version

curl -sS https://<service>.public.example.invalid/api/v1/version
```

## Screenshot And Log Policy

Do not commit screenshots that expose real hostnames, repository names, usernames, organization names, tokens, or machine paths. If screenshots are useful for review, create mock screenshots or keep real captures in a local project record outside the repository.

## Operational Rules

- Do not commit real URLs for private or internal infrastructure; use placeholders.
- Do not commit passwords, tokens, git extraHeader values, DNS secrets, or private key contents.
- Do not edit public-entry or tunnel configuration for ordinary service operations unless the task explicitly targets that infrastructure.
- Do not create per-service DNS records when wildcard DNS covers the service hostnames.
- Do not create per-service certificates when a shared wildcard certificate covers the service hostnames.
- Keep `ROOT_URL` and `CHATTEA_BASE_URL` changes deliberate because they affect generated clone URLs and API clients.

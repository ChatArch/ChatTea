# Agent Notes

## Network / GitHub Proxy

- GitHub operations on this machine must use the local authenticated proxy; do not try repeated bare `git push` / `git fetch` first.
- Do not commit the real proxy URL or credentials. The secret proxy value lives in the machine-local shell config.
- For non-interactive shells, `proxy_on` is an alias and will not expand if it is defined after the shell command is parsed. Export the proxy once at the start of the task:

```bash
set +x
source /etc/universal_rc >/dev/null 2>&1 || true
body=$(alias proxy_on 2>/dev/null | sed -E "s/^alias proxy_on=//; s/^'\\''//; s/'\\''$//")
eval "$body"
```

- Verify without printing the proxy value:

```bash
git ls-remote origin HEAD >/dev/null
```

## Real Practice Requirement

- ChatTea/Gitea CLI work must not stop at planning docs. Pair infra changes with real Gitea practice.
- Capture redacted command logs, `summary.json`, and web UI screenshots for meaningful flows.
- Copy safe screenshots into `docs/assets/<topic>/` and update the relevant Markdown chapter.
- Keep public docs free of real Gitea URLs, local home paths, env file names, tokens, passwords, and proxy credentials.

## Development Expectations

- Keep changes minimal and reviewable.
- Prefer doc-first CLI tests.
- Sync docs and changelog with user-facing behavior.
- Use interactive prompts only when arguments are missing and recoverable.

# Changelog

## Unreleased

## 0.3.0

- Changed the Runner CLI surface to the first-version structured tree: `runner registry`, `runner local`, `runner pool`, and `runner workflow`.
- Removed the earlier duplicate Runner entry points (`runner token/list/view/edit/delete/setup`) so the initial API does not carry stale aliases.
- Added local multi-runner instance management with per-runner roots, config files, workdirs, and `chattea-runner@<runner-name>.service` user services.
- Added host-backend Runner practice documentation, real Gitea Web UI screenshots, and tests for local runner config, service naming, workflow `runs-on` parsing, and removed legacy commands.

## 0.2.3

- Added `auth` as a GitHub-familiar authentication namespace while keeping `set-token` as a ChatTea quick configuration command.
- Added `chattea api` for raw Gitea API passthrough to support routes not yet wrapped by first-class commands.
- Hardened bootstrap reruns: `token bootstrap` rotates an existing managed token by default, and `server bootstrap` can reuse the configured token when the local admin token name already exists.
- Added repo-level collaboration commands: `issue`, `label`, `milestone`, `pr`, and `release`, backed by Gitea repository REST routes and importable Python functions.
- Added Actions/Flow MVP commands: `runner`, `run`, `job`, and `artifact`, including runner registration/local service setup and PR-triggered run/job/log inspection.
- Added `chattea project card` as the primary Project board card command group while keeping `chattea project issue` as a compatibility alias.
- Changed `chattea server install` to default to the latest ChatArch internal Gitea release instead of requiring a community Gitea version.
- Documented the GitHub-aligned ChatTea target CLI tree and added a visual CLI guide covering Project boards, PRs, Runner setup, Actions runs, jobs, and logs.

## 0.2.2

- Added `chattea project` for repository-scoped Gitea Project board automation, including project CRUD, column CRUD, and issue/PR card list/add/remove/move commands.
- Added reusable `GiteaClient` methods for the ChatArch Gitea repository Project API.
- Added unit tests for Project API paths, CLI command registration, destructive-operation confirmation, and `sorting=0` handling.
- Tightened release-reviewed runtime dependency windows, including `chatenv>=0.2.2,<0.3.0` and bounded `click`/`chatstyle` ranges.

## 0.2.1

Patch release for the ChatTea Gitea lifecycle workflow.

- Simplified official ChatEnv names to short `CHATTEA_*` fields.
- Kept legacy `CHATTEA_URL` and old `CHATTEA_GITEA_*` names as read-only compatibility fallbacks.
- Moved listen address and HTTP port out of ChatEnv and into `chattea server init` parameters backed by Gitea `app.ini`.
- Added `chattea server config path/show/get/set` for managed Gitea `app.ini` inspection and small edits.
- Documented new-machine setup, update/upgrade steps, user systemd autostart, and app.ini boundaries.
- Expanded tests for ChatEnv validation, ChatStyle fail-fast behavior, and app.ini config commands.

## 0.2.0

Initial ChatEnv-backed ChatTea release line.

- Added local Gitea binary installation and managed service lifecycle commands.
- Added token configuration and basic repository operations.
- Registered the ChatTea ChatEnv provider.

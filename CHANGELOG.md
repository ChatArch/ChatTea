# Changelog

## Unreleased

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

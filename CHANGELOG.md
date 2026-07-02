# Changelog

## 2026-07-02 - 0.2.0

### Changed

- Registered ChatTea as a ChatEnv provider with the `ChatTea` typed profile.
- Changed `chattea set-token` to write `$CHATARCH_HOME/envs/ChatTea/.env` instead of the legacy JSON config.
- Normalized default Gitea paths under `$CHATARCH_HOME/chattea` while keeping CLI options for explicit overrides.
- Kept legacy `~/.config/chattea/config.json` as a read-only fallback for URL/token compatibility.

## 2026-07-02 - 0.1.1

### Added

- Added first-version Gitea lifecycle CLI: `chattea server install/init/serve/start/stop/restart/status/logs/version/health`.
- Added top-level `chattea set-token` for default Gitea URL and API token configuration.
- Added basic repository CLI: `chattea repo list/view/create/clone/migrate`.
- Added reusable Python modules so callers can use the bare API without shelling out to the CLI: `chattea.config`, `chattea.api`, `chattea.git`, and `chattea.server`.
- Added `docs/interface-tree.md` to document the P0 interface tree and deferred surface.

## 2026-06-24 - 0.1.0

### Added

- Initial ChatArch Python package scaffold for `ChatTea`.
- Added `chattea` CLI entry point scaffold.
- Added tests, documentation, GitHub Actions CI/preview/deploy workflows, and PyPI Trusted Publishing workflow.

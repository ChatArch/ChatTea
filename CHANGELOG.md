# Changelog

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

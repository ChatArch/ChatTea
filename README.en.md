<div align="center">
    <a href="https://pypi.python.org/pypi/ChatTea">
        <img src="https://img.shields.io/pypi/v/ChatTea.svg" alt="PyPI version" />
    </a>
    <a href="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml">
        <img src="https://github.com/ChatArch/ChatTea/actions/workflows/ci.yml/badge.svg" alt="Tests" />
    </a>
    <a href="https://ChatArch.github.io/ChatTea">
        <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# ChatTea

ChatTea is ChatArch's Gitea management CLI/API package for local Gitea installation, initialization, service management, token configuration, and basic repository operations. Since `0.2.0`, ChatTea uses ChatEnv and stores runtime files under `~/.chatarch/chattea` by default.

## Quick Start

```bash
pip install -e ".[dev]"
chattea --help
python -m pytest -q
```

## Common Flow

```bash
chattea server install
chattea server init
chattea server start
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea repo list
```

`set-token` writes the active ChatEnv profile at `$CHATARCH_HOME/envs/ChatTea/.env`. Legacy `~/.config/chattea/config.json` is read only as a compatibility fallback.

Default paths:

```text
$CHATARCH_HOME/chattea/bin/gitea
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
$CHATARCH_HOME/chattea/gitea/data/gitea.db
~/.config/systemd/user/chattea-gitea.service
```

## CLI Tree

```text
chattea
├── set-token
├── server
│   ├── install
│   ├── init
│   ├── serve
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   ├── logs
│   ├── version
│   └── health
└── repo
    ├── list
    ├── view
    ├── create
    ├── clone
    └── migrate
```

## Development Notes

The CLI is a thin wrapper over importable Python modules: `chattea.config`, `chattea.api`, `chattea.git`, and `chattea.server`. See `DEVELOP.md`, `AGENTS.md`, and `docs/interface-tree.md` before expanding the surface.

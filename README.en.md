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

ChatTea is ChatArch's Gitea management CLI/API package. The first version focuses on local Gitea installation, initialization, service management, token configuration, and basic repository operations.

## Quick Start

```bash
pip install -e ".[dev]"
chattea --help
python -m pytest -q
```

## Common Flow

```bash
chattea server install --version 1.26.4
chattea server init --work-path ~/gitea --http-port 3000
chattea server start --work-path ~/gitea --config ~/gitea/custom/conf/app.ini
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea repo list
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

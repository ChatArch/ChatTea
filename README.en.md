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

ChatTea is ChatArch's Gitea management CLI/API package for local Gitea installation, initialization, service management, app.ini inspection/editing, token configuration, and basic repository operations. Since `0.2.1`, ChatTea uses ChatEnv and stores runtime files under `$CHATARCH_HOME/chattea` by default.

## Quick Start

```bash
python -m pip install -U ChatTea
chattea --version
chattea --help
```

For source development:

```bash
git clone https://github.com/ChatArch/ChatTea.git
cd ChatTea
python -m pip install -e ".[dev,docs]"
python -m pytest -q
```

## New Machine Setup

```bash
python -m chatenv.cli init -t chattea -I
python -m chatenv.cli set CHATTEA_BASE_URL=http://127.0.0.1:3000
python -m chatenv.cli test -t chattea -I

chattea server install --version 1.26.4
chattea server init --base-url http://127.0.0.1:3000 --listen-addr 127.0.0.1 --http-port 3000
chattea server start
chattea server health
```

For LAN access:

```bash
chattea server init --base-url http://172.25.52.106:3000 --listen-addr 0.0.0.0 --http-port 3000
```

`--listen-addr` and `--http-port` are written to Gitea `app.ini`; they are not ChatEnv fields.

## Update and Autostart

Update ChatTea:

```bash
python -m pip install -U ChatTea
python -m chatenv.cli test -t chattea -I
chattea --version
```

Update the managed Gitea binary:

```bash
chattea server stop
chattea server install --version 1.26.5 --force
chattea server start
chattea server health
```

Enable user systemd autostart:

```bash
chattea server start
chattea server status
loginctl enable-linger "$USER"
```

Some systems require administrator policy for `loginctl enable-linger`. Without lingering, the user service may not survive logout.

## ChatEnv Fields

Official fields:

```text
CHATTEA_BASE_URL
CHATTEA_TOKEN
CHATTEA_HOME
CHATTEA_BINARY
CHATTEA_WORK_PATH
CHATTEA_CONFIG
```

`CHATTEA_URL` and old `CHATTEA_GITEA_*` names are legacy read-only fallbacks. Listen address, HTTP port, domain, service name, and install version are not official Env fields.

## Gitea app.ini Flow

```bash
chattea server config path
chattea server config show
chattea server config get --section server --key HTTP_PORT
chattea server config set --section server --key HTTP_PORT --value 3001
chattea server restart
```

`server config show` masks known sensitive keys by default.

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
│   ├── health
│   └── config
│       ├── path
│       ├── show
│       ├── get
│       └── set
├── repo
│   ├── list
│   ├── view
│   ├── create
│   ├── clone
│   └── migrate
└── project
    ├── list
    ├── view
    ├── create
    ├── edit
    ├── delete
    ├── column
    │   ├── list
    │   ├── create
    │   ├── edit
    │   └── delete
    └── issue
        ├── list
        ├── add
        ├── remove
        └── move
```

## Development Notes

The CLI is a thin wrapper over importable Python functions. See `DEVELOP.md`, `AGENTS.md`, and `docs/interface-tree.md` before expanding the surface.

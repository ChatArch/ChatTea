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

ChatTea 是 ChatArch 的 Gitea 管理 CLI/API 包，聚焦本地 Gitea 的安装、初始化、启动、token 配置和基础仓库操作。`0.2.0` 起配置接入 ChatEnv，默认运行目录收敛到 `~/.chatarch/chattea`。

## 快速开始

```bash
pip install -e ".[dev]"
chattea --help
python -m pytest -q
```

## 常用流程

### 安装并初始化 Gitea

```bash
chattea server install
chattea server init
chattea server serve
```

### 使用 user systemd 管理服务

```bash
chattea server start
chattea server status
chattea server logs --lines 100
chattea server stop
```

### 配置 API token

```bash
chattea set-token --url http://127.0.0.1:3000 --token "$GITEA_TOKEN"
chattea server health
```

`set-token` 写入 ChatEnv active profile：`$CHATARCH_HOME/envs/ChatTea/.env`，不会继续写旧的 `~/.config/chattea/config.json`。旧 JSON 仅保留只读兼容。

### 默认路径

```text
$CHATARCH_HOME/chattea/bin/gitea
$CHATARCH_HOME/chattea/gitea/custom/conf/app.ini
$CHATARCH_HOME/chattea/gitea/data/gitea.db
~/.config/systemd/user/chattea-gitea.service
```

`CHATARCH_HOME` 由 ChatEnv 解析，默认是 `~/.chatarch`。ChatTea 自己只定义 `CHATTEA_*` 配置。

### 仓库操作

```bash
chattea repo list
chattea repo view gitea_admin/demo
chattea repo create --owner gitea_admin --name demo
chattea repo clone gitea_admin/demo
chattea repo migrate --clone-url https://github.com/ChatArch/ChatTea.git --owner gitea_admin --name ChatTea
```

## CLI 结构

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

## 目录结构

- `src/`：包源码
- `tests/code-tests/`：代码测试和历史测试迁移
- `tests/cli-tests/`：真实 CLI 测试，doc-first
- `tests/mock-cli-tests/`：mock/fake CLI 测试，doc-first
- `docs/`：长期维护文档，由 mkdocs 构建

## 开发说明

扩展脚手架前，先阅读 `DEVELOP.md` 和 `AGENTS.md`。接口树见 `docs/interface-tree.md`。

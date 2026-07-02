from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chatenv import BaseEnvConfig, EnvField, EnvStore, get_paths

DEFAULT_URL = "http://127.0.0.1:3000"
DEFAULT_GITEA_VERSION = "1.26.4"
DEFAULT_SERVICE_NAME = "chattea-gitea.service"


class ChatTeaEnvConfig(BaseEnvConfig):
    """Typed ChatEnv configuration for ChatTea."""

    _title = "ChatTea Configuration"
    _aliases = ["chattea", "tea"]
    _storage_dir = "ChatTea"

    CHATTEA_URL = EnvField(
        "CHATTEA_URL",
        default=DEFAULT_URL,
        desc="Gitea base URL used by ChatTea API commands.",
    )
    CHATTEA_TOKEN = EnvField(
        "CHATTEA_TOKEN",
        desc="Gitea API token used by ChatTea API commands.",
        is_sensitive=True,
    )
    CHATTEA_HOME = EnvField(
        "CHATTEA_HOME",
        desc="ChatTea data root. Defaults to CHATARCH_HOME/chattea.",
    )
    CHATTEA_GITEA_VERSION = EnvField(
        "CHATTEA_GITEA_VERSION",
        default=DEFAULT_GITEA_VERSION,
        desc="Default Gitea binary version for server install.",
    )
    CHATTEA_GITEA_BINARY = EnvField(
        "CHATTEA_GITEA_BINARY",
        desc="Gitea binary path. Defaults to CHATTEA_HOME/bin/gitea.",
    )
    CHATTEA_GITEA_WORK_PATH = EnvField(
        "CHATTEA_GITEA_WORK_PATH",
        desc="Gitea work path. Defaults to CHATTEA_HOME/gitea.",
    )
    CHATTEA_GITEA_CONFIG = EnvField(
        "CHATTEA_GITEA_CONFIG",
        desc="Gitea app.ini path. Defaults to CHATTEA_GITEA_WORK_PATH/custom/conf/app.ini.",
    )
    CHATTEA_GITEA_HTTP_PORT = EnvField(
        "CHATTEA_GITEA_HTTP_PORT",
        default="3000",
        desc="Local Gitea HTTP port used by server init.",
    )
    CHATTEA_GITEA_DOMAIN = EnvField(
        "CHATTEA_GITEA_DOMAIN",
        default="127.0.0.1",
        desc="Local Gitea domain used by server init.",
    )
    CHATTEA_GITEA_SERVICE_NAME = EnvField(
        "CHATTEA_GITEA_SERVICE_NAME",
        default=DEFAULT_SERVICE_NAME,
        desc="User systemd service name for ChatTea-managed Gitea.",
    )


@dataclass
class ChatTeaConfig:
    url: str = DEFAULT_URL
    token: str | None = None
    home: Path | None = None
    gitea_version: str = DEFAULT_GITEA_VERSION
    gitea_binary: Path | None = None
    gitea_work_path: Path | None = None
    gitea_config: Path | None = None
    gitea_http_port: int = 3000
    gitea_domain: str = "127.0.0.1"
    gitea_service_name: str = DEFAULT_SERVICE_NAME

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ChatTeaConfig":
        return cls(url=str(data.get("url") or DEFAULT_URL).rstrip("/"), token=data.get("token") or None)

    def to_mapping(self) -> dict[str, Any]:
        data: dict[str, Any] = {"url": self.url.rstrip("/")}
        if self.token:
            data["token"] = self.token
        return data


def default_chattea_home() -> Path:
    return get_paths().home_dir / "chattea"


def default_gitea_binary(home: Path | None = None) -> Path:
    root = home or default_chattea_home()
    return root / "bin" / "gitea"


def default_gitea_work_path(home: Path | None = None) -> Path:
    root = home or default_chattea_home()
    return root / "gitea"


def default_gitea_config(work_path: Path | None = None, home: Path | None = None) -> Path:
    work = work_path or default_gitea_work_path(home)
    return work / "custom" / "conf" / "app.ini"


def get_config_path() -> Path:
    """Return the legacy JSON config path kept for read-only compatibility."""
    override = os.environ.get("CHATTEA_CONFIG")
    if override:
        return Path(override).expanduser()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "chattea" / "config.json"


def _load_legacy_config(path: Path | None = None) -> ChatTeaConfig:
    config_path = path or get_config_path()
    if not config_path.exists():
        return ChatTeaConfig()
    try:
        return ChatTeaConfig.from_mapping(json.loads(config_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return ChatTeaConfig()


def _active_env_values() -> dict[str, str]:
    return EnvStore(get_paths().envs_dir).load_active(ChatTeaEnvConfig)


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser()


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config(path: Path | None = None) -> ChatTeaConfig:
    """Load ChatTea config from ChatEnv, with legacy JSON read fallback."""
    active_values = _active_env_values()
    BaseEnvConfig.load_all(get_paths().envs_dir)
    legacy = _load_legacy_config(path)

    explicit_url = os.getenv("CHATTEA_URL") or active_values.get("CHATTEA_URL")
    explicit_token = os.getenv("CHATTEA_TOKEN") or active_values.get("CHATTEA_TOKEN")

    home = _optional_path(ChatTeaEnvConfig.CHATTEA_HOME.value) or default_chattea_home()
    work_path = _optional_path(ChatTeaEnvConfig.CHATTEA_GITEA_WORK_PATH.value) or default_gitea_work_path(home)

    return ChatTeaConfig(
        url=str(explicit_url or legacy.url or DEFAULT_URL).rstrip("/"),
        token=explicit_token if explicit_token is not None else legacy.token,
        home=home,
        gitea_version=str(ChatTeaEnvConfig.CHATTEA_GITEA_VERSION.value or DEFAULT_GITEA_VERSION),
        gitea_binary=_optional_path(ChatTeaEnvConfig.CHATTEA_GITEA_BINARY.value) or default_gitea_binary(home),
        gitea_work_path=work_path,
        gitea_config=_optional_path(ChatTeaEnvConfig.CHATTEA_GITEA_CONFIG.value) or default_gitea_config(work_path),
        gitea_http_port=_int_value(ChatTeaEnvConfig.CHATTEA_GITEA_HTTP_PORT.value, 3000),
        gitea_domain=str(ChatTeaEnvConfig.CHATTEA_GITEA_DOMAIN.value or "127.0.0.1"),
        gitea_service_name=str(ChatTeaEnvConfig.CHATTEA_GITEA_SERVICE_NAME.value or DEFAULT_SERVICE_NAME),
    )


def save_config(config: ChatTeaConfig, path: Path | None = None) -> Path:
    """Save URL/token to the active ChatTea ChatEnv profile."""
    store = EnvStore(get_paths().envs_dir)
    values = store.load_active(ChatTeaEnvConfig)
    values["CHATTEA_URL"] = config.url.rstrip("/")
    if config.token:
        values["CHATTEA_TOKEN"] = config.token
    return store.save_active(ChatTeaEnvConfig, values)


def set_token(url: str, token: str, path: Path | None = None) -> Path:
    config = load_config(path)
    config.url = url.rstrip("/")
    config.token = token
    return save_config(config, path)


def mask_token(token: str | None) -> str:
    if not token:
        return "<none>"
    if len(token) <= 12:
        return token[:2] + "..." + token[-2:]
    return token[:7] + "..." + token[-5:]


__all__ = [
    "ChatTeaConfig",
    "ChatTeaEnvConfig",
    "DEFAULT_GITEA_VERSION",
    "DEFAULT_SERVICE_NAME",
    "DEFAULT_URL",
    "default_chattea_home",
    "default_gitea_binary",
    "default_gitea_config",
    "default_gitea_work_path",
    "get_config_path",
    "load_config",
    "mask_token",
    "save_config",
    "set_token",
]

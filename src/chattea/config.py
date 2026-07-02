from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_URL = "http://127.0.0.1:3000"


@dataclass
class ChatTeaConfig:
    url: str = DEFAULT_URL
    token: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ChatTeaConfig":
        return cls(url=str(data.get("url") or DEFAULT_URL).rstrip("/"), token=data.get("token") or None)

    def to_mapping(self) -> dict[str, Any]:
        data: dict[str, Any] = {"url": self.url.rstrip("/")}
        if self.token:
            data["token"] = self.token
        return data


def get_config_path() -> Path:
    override = os.environ.get("CHATTEA_CONFIG")
    if override:
        return Path(override).expanduser()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return config_home / "chattea" / "config.json"


def load_config(path: Path | None = None) -> ChatTeaConfig:
    config_path = path or get_config_path()
    if not config_path.exists():
        return ChatTeaConfig()
    try:
        return ChatTeaConfig.from_mapping(json.loads(config_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return ChatTeaConfig()


def save_config(config: ChatTeaConfig, path: Path | None = None) -> Path:
    config_path = path or get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config.to_mapping(), indent=2) + "\n", encoding="utf-8")
    config_path.chmod(0o600)
    return config_path


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

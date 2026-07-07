from __future__ import annotations

from typing import Any


def list_payload_items(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in (*keys, "entries", "workflow_runs", "runs", "jobs", "artifacts", "runners"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []

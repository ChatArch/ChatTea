from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl

import click

from chattea.api import GiteaAPIError, GiteaClient


def parse_query_params(values: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated KEY=VALUE CLI parameters for raw API requests."""
    params: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Query parameter must be KEY=VALUE: {value}")
        key, parsed_value = value.split("=", 1)
        if not key:
            raise ValueError(f"Query parameter key is empty: {value}")
        params[key] = parsed_value
    return params


def parse_json_data(data: str | None) -> dict[str, Any] | None:
    """Parse an optional JSON object body."""
    if data is None:
        return None
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("--data must be a JSON object")
    return payload


def call_api(
    method: str,
    path: str,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    url: str | None = None,
    token: str | None = None,
) -> Any:
    """Call one raw Gitea API route through the configured client."""
    route = path if path.startswith("/") else f"/{path}"
    return GiteaClient(url=url, token=token).request(method.upper(), route, data=data, params=params)


@click.command(name="api")
@click.argument("path")
@click.option("--method", default="GET", show_default=True, help="HTTP method.")
@click.option("--data", default=None, help="JSON object request body.")
@click.option("--param", "params", multiple=True, help="Query parameter as KEY=VALUE. Repeatable.")
@click.option("--url", default=None, help="Gitea base URL override. Defaults to CHATTEA_BASE_URL.")
@click.option("--token", default=None, help="Gitea API token override. Defaults to CHATTEA_TOKEN.")
def api_command(path: str, method: str, data: str | None, params: tuple[str, ...], url: str | None, token: str | None) -> None:
    """Call a raw Gitea API path for routes not yet wrapped by ChatTea."""
    try:
        query_params = dict(parse_qsl(path.split("?", 1)[1])) if "?" in path else {}
        route = path.split("?", 1)[0]
        query_params.update(parse_query_params(params))
        payload = call_api(method, route, data=parse_json_data(data), params=query_params or None, url=url, token=token)
    except (ValueError, json.JSONDecodeError, GiteaAPIError) as exc:
        raise click.ClickException(str(exc)) from exc
    if payload is None:
        return
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2))

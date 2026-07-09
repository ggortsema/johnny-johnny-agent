from dataclasses import asdict, is_dataclass
from typing import Any

import json


def render_json_backlog_resource(resource: Any) -> str:
    return json.dumps(
        _to_serializable(resource),
        indent=2,
    )


def _to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, list):
        return [
            _to_serializable(item)
            for item in value
        ]

    return value
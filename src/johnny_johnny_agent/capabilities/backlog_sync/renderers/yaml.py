from dataclasses import asdict, is_dataclass
from typing import Any

import yaml


def render_yaml_backlog_resource(resource: Any) -> str:
    return yaml.safe_dump(
        _to_serializable(resource),
        sort_keys=False,
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
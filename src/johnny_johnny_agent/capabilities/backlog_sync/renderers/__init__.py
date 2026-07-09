from collections.abc import Callable

from johnny_johnny_agent.capabilities.backlog_sync.renderers.human import (
    render_human_backlog_item,
    render_human_backlog_items,
)
from johnny_johnny_agent.capabilities.backlog_sync.renderers.json import (
    render_json_backlog_resource,
)
from johnny_johnny_agent.capabilities.backlog_sync.renderers.yaml import (
    render_yaml_backlog_resource,
)
from johnny_johnny_agent.domain.backlog import Backlog, Epic, Issue


BacklogItem = Epic | Issue
BacklogResource = BacklogItem | list[BacklogItem]
BacklogResourceRenderer = Callable[[Backlog, BacklogResource], str]


def get_backlog_resource_renderer(output: str) -> BacklogResourceRenderer:
    normalized_output = output.strip().lower()

    renderers = {
        "human": _render_human_backlog_resource,
        "yaml": _render_yaml_backlog_resource,
        "yml": _render_yaml_backlog_resource,
        "json": _render_json_backlog_resource,
    }

    if normalized_output not in renderers:
        raise RuntimeError(f"Unsupported output format: {output}")

    return renderers[normalized_output]


def get_backlog_item_renderer(output: str) -> BacklogResourceRenderer:
    return get_backlog_resource_renderer(output)


def _render_human_backlog_resource(
        backlog: Backlog,
        resource: BacklogResource,
) -> str:
    if isinstance(resource, list):
        return render_human_backlog_items(resource)

    return render_human_backlog_item(backlog, resource)


def _render_yaml_backlog_resource(
        backlog: Backlog,
        resource: BacklogResource,
) -> str:
    return render_yaml_backlog_resource(resource)


def _render_json_backlog_resource(
        backlog: Backlog,
        resource: BacklogResource,
) -> str:
    return render_json_backlog_resource(resource)
from dataclasses import dataclass


@dataclass
class JohnnyMetadata:
    id: str
    schema: str
    type: str
    parent: str | None = None


def render_johnny_metadata(metadata: JohnnyMetadata) -> str:
    lines = [
        "<!-- johnny-johnny",
        f"id: {metadata.id}",
        f"schema: {metadata.schema}",
        f"type: {metadata.type}",
    ]

    if metadata.parent:
        lines.append(f"parent: {metadata.parent}")

    lines.append("-->")

    return "\n".join(lines)
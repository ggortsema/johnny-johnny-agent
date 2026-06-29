import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


DEFAULT_SCHEMA_PATH = "docs/schemas/backlog-v1.schema.json"


def validate_backlog_yaml(
        backlog_path: str,
        schema_path: str = DEFAULT_SCHEMA_PATH,
) -> None:
    backlog_file = Path(backlog_path)
    schema_file = Path(schema_path)

    if not backlog_file.exists():
        raise RuntimeError(f"Backlog YAML not found: {backlog_file}")

    if not schema_file.exists():
        raise RuntimeError(f"Backlog schema not found: {schema_file}")

    backlog_data = yaml.safe_load(backlog_file.read_text(encoding="utf-8"))
    schema_data = json.loads(schema_file.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema_data)
    errors = sorted(
        validator.iter_errors(backlog_data),
        key=lambda error: list(error.path),
    )

    if errors:
        print("Backlog YAML validation failed:")
        print()

        for error in errors:
            path = ".".join(str(part) for part in error.path)

            if not path:
                path = "<root>"

            print(f"- {path}: {error.message}")

        raise RuntimeError("Backlog YAML failed schema validation")

    print("Backlog YAML validation passed.")
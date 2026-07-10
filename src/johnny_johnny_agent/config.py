"""Runtime configuration helpers."""

import os

from dotenv import load_dotenv


load_dotenv()


def resolve_database_url(explicit_database_url: str | None = None) -> str:
    """Resolve PostgreSQL connectivity without coupling to its network path."""
    database_url = explicit_database_url or os.environ.get("DATABASE_URL")
    if not database_url or not database_url.strip():
        raise RuntimeError(
            "DATABASE_URL is required. Set it in the environment or pass "
            "--database-url."
        )
    return database_url.strip()

import os

import pytest

# Importing the CLI app proves the application can load with its startup imports.
from johnny_johnny_agent.cli.main import app
from johnny_johnny_agent.capabilities.github.client import get_viewer_project_by_title


DEFAULT_GITHUB_PROJECT_TITLE = "MycroftAI Engineering Roadmap"


def test_application_loads():
    assert app is not None


@pytest.mark.skipif(
    not os.getenv("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN is required for GitHub behavior tests.",
)
def test_can_connect_to_github_project():
    project = get_viewer_project_by_title(DEFAULT_GITHUB_PROJECT_TITLE)

    assert project["id"]
    assert project["title"] == DEFAULT_GITHUB_PROJECT_TITLE
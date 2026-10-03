import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that create and delete live macOS calendars and events",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="Live Calendar access requires --run-integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)

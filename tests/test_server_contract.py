import asyncio
from unittest.mock import Mock

from mcp_ical import server


def test_mcp_tool_names_and_parameters():
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    expected = {
        "list_calendars": set(),
        "list_events": {"start_date", "end_date", "calendar_name"},
        "create_event": {"create_event_request"},
        "update_event": {"event_id", "update_event_request"},
    }
    assert set(tools) == set(expected)
    for name, parameters in expected.items():
        assert set(tools[name].inputSchema["properties"]) == parameters
    assert tools["list_events"].inputSchema["required"] == ["start_date", "end_date"]


def test_calendar_resource_and_tool_keep_response_format(monkeypatch):
    manager = Mock()
    manager.list_calendar_names.return_value = ["Home", "Work"]
    monkeypatch.setattr(server, "get_calendar_manager", lambda: manager)
    expected = "Available calendars:\n- Home\n- Work"
    assert server.get_calendars() == expected
    assert asyncio.run(server.list_calendars()) == expected

# MCP iCal Server

An MCP server for reading and updating macOS Calendar through EventKit. It works with
MCP clients that support stdio and calendars configured in the macOS Calendar app,
including local, iCloud and other connected calendar accounts.

## Tools

| Tool | Behavior |
| --- | --- |
| `list_calendars` | List available event calendar names. |
| `list_events` | Read events between required start and end times, optionally by calendar name. |
| `create_event` | Create an event with optional calendar, location, notes, URL, reminders and recurrence. |
| `update_event` | Update an event by ID; recurring-event updates affect this and future occurrences. |

Calendar names are also available from the `calendars://list` resource. The Python
`CalendarManager` additionally supports event deletion and calendar helpers; these
are not exposed as MCP tools.

Times use ISO 8601. Include the UTC offset when known. Reminder offsets are minutes
before the event start; negative offsets are after the start. An empty reminder list
on update clears reminders. Omitted or null update fields stay unchanged.

Recurrence frequencies are `0` (daily), `1` (weekly), `2` (monthly), and `3` (yearly).
Weekdays run from `1` (Sunday) to `7` (Saturday). Use either an end date or a positive
occurrence count, or leave both unset. More complex recurrence patterns are not
represented by the request schema.

## Installation

Requires macOS, Python 3.12+, [uv](https://docs.astral.sh/uv/), a configured Calendar
app, and an MCP client.

```bash
git clone https://github.com/Omar-V2/mcp-ical.git
cd mcp-ical
uv sync --locked
```

Configure the client to run `uv --directory /absolute/path/to/mcp-ical run mcp-ical`.
For clients using an `mcpServers` configuration, such as Claude Desktop:

```json
{
  "mcpServers": {
    "mcp-ical": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mcp-ical", "run", "mcp-ical"]
    }
  }
}
```

Calendar access is requested on the first calendar operation. Grant access in macOS
System Settings → Privacy & Security → Calendars for the application running the
server. See [installation and permission troubleshooting](docs/install.md) if access
is denied or a permission prompt does not appear.

## Development

```bash
uv sync --locked --dev
uv run pytest
```

The default suite uses mocked calendar stores and skips live integration tests.
To run integration tests deliberately on a development account with an iCloud
calendar source:

```bash
uv run pytest --run-integration tests/test_calendar_manager_integration.py
```

Integration tests create and delete calendars and events. Cleanup targets only the
calendars created by each test; interrupted runs may leave their test calendars behind.

Keep tool names, request fields and text response formats compatible. Test changes
with mocked EventKit stores before testing against a live calendar.

## License

[MIT](LICENSE). Built with [MCP](https://modelcontextprotocol.io/) and
[PyObjC](https://pyobjc.readthedocs.io/).

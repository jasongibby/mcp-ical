import sys
from datetime import datetime
from functools import lru_cache
from textwrap import dedent

from loguru import logger
from mcp.server.fastmcp import FastMCP

from .ical import CalendarManager
from .models import CreateEventRequest, UpdateEventRequest

mcp = FastMCP("Calendar")

logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
)


# Initialize the CalendarManager on demand in order to only request calendar permission
# when a calendar tool is invoked instead of on the launch of the Claude Desktop app.
@lru_cache(maxsize=None)
def get_calendar_manager() -> CalendarManager:
    """Get or initialize the calendar manager with proper error handling."""
    try:
        return CalendarManager()
    except ValueError as e:
        error_msg = dedent("""\
        Calendar access is not granted. Please follow these steps:

        1. Open System Preferences/Settings
        2. Go to Privacy & Security > Calendar
        3. Check the box next to your terminal application or Claude Desktop
        4. Restart Claude Desktop

        Once you've granted access, try your calendar operation again.
        """)
        raise ValueError(error_msg) from e


def _format_calendars(calendars: list[str]) -> str:
    if not calendars:
        return "No calendars found"
    return "Available calendars:\n" + "\n".join(f"- {calendar}" for calendar in calendars)


@mcp.resource("calendars://list")
def get_calendars() -> str:
    """List all available calendars that can be used with calendar operations."""
    try:
        manager = get_calendar_manager()
        calendars = manager.list_calendar_names()
        return _format_calendars(calendars)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error listing calendars: {str(e)}"


@mcp.tool()
async def list_calendars() -> str:
    """List all available calendars."""
    try:
        manager = get_calendar_manager()
        return _format_calendars(manager.list_calendar_names())

    except Exception as e:
        return f"Error listing calendars: {str(e)}"


@mcp.tool()
async def list_events(start_date: datetime, end_date: datetime, calendar_name: str | None = None) -> str:
    """List calendar events in a date range.

    Use the desired time window, or 00:00:00 through 23:59:59 for whole days.

    Args:
        start_date: Start date in ISO8601 format (YYYY-MM-DDT00:00:00).
        end_date: End date in ISO8601 format (YYYY-MM-DDT23:59:59).
        calendar_name: Optional calendar name to filter by
    """
    try:
        manager = get_calendar_manager()
        events = manager.list_events(start_date, end_date, calendar_name)
        if not events:
            return "No events found in the specified date range"

        return "".join(str(event) for event in events)

    except Exception as e:
        return f"Error listing events: {str(e)}"


@mcp.tool()
async def create_event(create_event_request: CreateEventRequest) -> str:
    """Create an event in the named calendar, or the default calendar when omitted.

    Provide title, start_time and end_time in create_event_request. Times use ISO 8601;
    include a UTC offset when known. Optional fields include location, notes, url,
    all_day, alarms_minutes_offsets, and recurrence_rule. Alarm offsets are minutes
    before the event (for example, [60, 1440]); negative offsets are after the start.
    Recurrence frequency: 0=daily, 1=weekly, 2=monthly, 3=yearly. Weekdays: 1=Sunday
    through 7=Saturday. Use at most one of end_date or occurrence_count.
    """
    try:
        manager = get_calendar_manager()

        event = manager.create_event(create_event_request)
        if not event:
            return "Failed to create event. Please check calendar permissions and try again."

        return f"Successfully created event: {event.title} (ID: {event.identifier})"

    except Exception as e:
        return f"Error creating event: {str(e)}"


@mcp.tool()
async def update_event(event_id: str, update_event_request: UpdateEventRequest) -> str:
    """Update an event by ID using the fields in update_event_request.

    Omitted or null fields stay unchanged. Empty notes or location clear those fields;
    an empty alarms_minutes_offsets list clears reminders. Times use ISO 8601. Alarm
    offsets are minutes before the start, including for all-day events. A recurrence
    update affects this and future occurrences. Use list_events to obtain the event ID
    and list_calendars to find calendar names.
    """
    try:
        manager = get_calendar_manager()
        event = manager.update_event(event_id, update_event_request)
        if not event:
            return f"Failed to update event. Event with ID {event_id} not found or update failed."

        return f"Successfully updated event: {event.title}"

    except Exception as e:
        return f"Error updating event: {str(e)}"


def main():
    logger.info("Running mcp-ical server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

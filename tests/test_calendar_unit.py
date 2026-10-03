"""Calendar behavior checks that never request access or touch a real calendar."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from Foundation import NSDate
from pydantic import ValidationError

from mcp_ical.ical import CalendarManager
from mcp_ical.models import CreateEventRequest, Event, Frequency, RecurrenceRule, UpdateEventRequest


@pytest.fixture
def manager():
    manager = CalendarManager.__new__(CalendarManager)
    manager.event_store = Mock()
    return manager


@pytest.fixture
def native_event():
    event = Mock()
    event.title.return_value = "Test"
    event.eventIdentifier.return_value = "event-id"
    event.startDate.return_value = NSDate.dateWithTimeIntervalSince1970_(1_700_000_000)
    event.endDate.return_value = NSDate.dateWithTimeIntervalSince1970_(1_700_003_600)
    event.lastModifiedDate.return_value = event.startDate.return_value
    event.calendar.return_value.title.return_value = "Test calendar"
    event.attendees.return_value = []
    event.alarms.return_value = []
    event.recurrenceRules.return_value = []
    event.recurrenceRule.return_value = None
    event.organizer.return_value = None
    event.URL.return_value = None
    event.status.return_value = 0
    return event


def test_native_dates_are_converted_to_datetimes(native_event):
    event = Event.from_ekevent(native_event)
    assert isinstance(event.start_time, datetime)
    assert isinstance(event.end_time, datetime)
    assert isinstance(event.last_modified, datetime)
    assert event.start_time.timestamp() == 1_700_000_000


def test_status_zero_is_preserved(native_event):
    assert "Status: 0," in str(Event.from_ekevent(native_event))


def test_alarm_presence_is_preserved(native_event):
    alarm = Mock()
    alarm.relativeOffset.return_value = -900
    native_event.alarms.return_value = [alarm]
    event = Event.from_ekevent(native_event)
    assert event.alarms_minutes_offsets == [15]
    assert event.has_alarms is True


def test_recurrence_uses_public_collection(native_event):
    recurrence = Mock()
    recurrence.frequency.return_value = Frequency.DAILY
    recurrence.interval.return_value = 2
    recurrence.daysOfTheWeek.return_value = None
    recurrence.recurrenceEnd.return_value = None
    native_event.recurrenceRules.return_value = [recurrence]
    event = Event.from_ekevent(native_event)
    assert event.recurrence_rule.frequency == Frequency.DAILY
    assert event.recurrence_rule.interval == 2


@pytest.mark.parametrize("count", [0, -1])
def test_recurrence_rejects_nonpositive_counts(count):
    with pytest.raises(ValidationError):
        RecurrenceRule(frequency=Frequency.DAILY, occurrence_count=count)


@pytest.mark.parametrize("all_day", [True, False, None])
def test_alarm_updates_keep_the_same_offsets(manager, native_event, monkeypatch, all_day):
    manager.find_event_by_id = Mock(return_value=SimpleNamespace(_raw_event=native_event))
    manager.event_store.saveEvent_span_error_.return_value = (True, None)
    monkeypatch.setattr(Event, "from_ekevent", Mock(return_value="updated"))
    assert manager.update_event(
        "event-id", UpdateEventRequest(title="Test", all_day=all_day, alarms_minutes_offsets=[60, 1440])
    ) == "updated"
    alarms = native_event.setAlarms_.call_args.args[0]
    assert [alarm.relativeOffset() for alarm in alarms] == [-3600, -86400]


def test_empty_alarm_update_clears_reminders(manager, native_event, monkeypatch):
    manager.find_event_by_id = Mock(return_value=SimpleNamespace(_raw_event=native_event))
    manager.event_store.saveEvent_span_error_.return_value = (True, None)
    monkeypatch.setattr(Event, "from_ekevent", Mock(return_value="updated"))
    manager.update_event("event-id", UpdateEventRequest(title="Test", alarms_minutes_offsets=[]))
    native_event.setAlarms_.assert_called_once_with([])


def test_calendar_deletion_verifies_identifiers(manager):
    calendar = Mock()
    manager._find_calendar_by_id = Mock(return_value=calendar)
    manager.event_store.removeCalendar_commit_error_.return_value = (True, None)
    manager.event_store.calendars.return_value = []
    with pytest.raises(RuntimeError, match="not properly deleted"):
        manager._delete_calendar("calendar-id")


def test_event_calendars_use_public_api(manager):
    from EventKit import EKEntityTypeEvent

    calendar = Mock()
    calendar.title.return_value = "Test"
    manager.event_store.calendarsForEntityType_.return_value = [calendar]
    assert manager.list_calendar_names() == ["Test"]
    manager.event_store.calendarsForEntityType_.assert_called_once_with(EKEntityTypeEvent)


def test_create_uses_public_recurrence_setter(manager, native_event, monkeypatch):
    monkeypatch.setattr("mcp_ical.ical.EKEvent", Mock(eventWithEventStore_=Mock(return_value=native_event)))
    manager.event_store.saveEvent_span_error_.return_value = (True, None)
    recurrence = RecurrenceRule(frequency=Frequency.DAILY)
    manager.create_event(CreateEventRequest(
        title="Test", start_time=datetime(2026, 10, 3), end_time=datetime(2026, 10, 4),
        recurrence_rule=recurrence,
    ))
    manager.event_store.defaultCalendarForNewEvents.assert_called_once_with()
    native_event.setCalendar_.assert_called_once_with(
        manager.event_store.defaultCalendarForNewEvents.return_value
    )
    native_event.setRecurrenceRules_.assert_called_once()
    assert len(native_event.setRecurrenceRules_.call_args.args[0]) == 1


@pytest.mark.parametrize("granted", [True, False])
def test_permission_request_uses_full_access(manager, granted):
    manager.event_store = SimpleNamespace(
        requestFullAccessToEventsWithCompletion_=lambda callback: callback(granted, None)
    )
    assert manager._request_access() is granted


def test_permission_request_supports_older_macos(manager):
    manager.event_store = SimpleNamespace(
        requestAccessToEntityType_completion_=lambda entity, callback: callback(True, None)
    )
    assert manager._request_access() is True


def test_missing_calendar_does_not_partially_modify_event(manager, native_event):
    from mcp_ical.ical import NoSuchCalendarException

    manager.find_event_by_id = Mock(return_value=SimpleNamespace(_raw_event=native_event))
    manager._find_calendar_by_name = Mock(return_value=None)
    with pytest.raises(NoSuchCalendarException):
        manager.update_event("event-id", UpdateEventRequest(title="New title", calendar_name="Missing"))
    native_event.setTitle_.assert_not_called()
    manager.event_store.saveEvent_span_error_.assert_not_called()


@pytest.mark.parametrize("sources", [[], [False, True]])
def test_missing_calendar_source_reports_available_sources(manager, monkeypatch, sources):
    monkeypatch.setattr("mcp_ical.ical.EKCalendar", Mock())
    native_sources = []
    for index, supported in enumerate(sources):
        source = Mock()
        source.title.return_value = f"source-{index}"
        source.sourceType.return_value = index
        source.supportsCalendarCreation.return_value = supported
        native_sources.append(source)
    manager.event_store.sources.return_value = native_sources
    with pytest.raises(ValueError, match="No source found") as error:
        manager._create_calendar("Test", source_name="Missing")
    if sources:
        assert "source-0" not in str(error.value)
        assert "source-1" in str(error.value)


def test_permission_request_timeout_is_explicit(manager, monkeypatch):
    semaphore = Mock()
    semaphore.acquire.return_value = False
    monkeypatch.setattr("mcp_ical.ical.Semaphore", Mock(return_value=semaphore))
    with pytest.raises(TimeoutError, match="Calendar access request timed out"):
        manager._request_access()
    semaphore.acquire.assert_called_once_with(timeout=30)

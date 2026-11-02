import pytest
from datetime import datetime

from task_tools.cli import SPEC_MARKER_RE, _parse_move_file
from task_tools.manage import Event, EventManager, Task, TaskManager


class TestTask:
    mockdatap0 = {
        "id": "FAKEID",
        "title": "P0: Do something!",
        "due": "2024-01-01T00:00:00.000Z",
        "notes": "Some notes.",
    }

    def test_initialization(self):
        task = Task(TestTask.mockdatap0)
        assert task.due == "2024-01-01"
        assert task.timing == Task.task_types["P0:"][0]

    def test_raw_fields(self):
        task = Task(dict(TestTask.mockdatap0, status="completed"))
        assert task.due_date == "2024-01-01"
        assert task.raw_notes == "Some notes."
        assert task.completed


class _FakeRequest(object):
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class _FakeTasks(object):
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeRequest(self.pages[len(self.calls) - 1])

    def patch(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeRequest(dict(TestTask.mockdatap0, **kwargs["body"]))


class _FakeService(object):
    def __init__(self, fake_tasks):
        self.fake_tasks = fake_tasks

    def tasks(self):
        return self.fake_tasks


def _manager(pages):
    manager = TaskManager.__new__(TaskManager)
    manager.enable_logging = False
    manager.task_list_id = "LIST"
    manager.service = _FakeService(_FakeTasks(pages))
    return manager


class TestTaskManager:
    def test_get_tasks_follows_pages(self):
        item = TestTask.mockdatap0
        manager = _manager(
            [{"items": [item] * 100, "nextPageToken": "NEXT"}, {"items": [item] * 5}]
        )
        tasks = manager.getTasks(datetime(2024, 1, 1), show_completed=True)
        assert len(tasks) == 105
        calls = manager.service.fake_tasks.calls
        assert "pageToken" not in calls[0]
        assert calls[1]["pageToken"] == "NEXT"
        assert calls[0]["showCompleted"] and calls[0]["showHidden"]
        assert "dueMin" not in calls[0]

    def test_complete_and_move(self):
        manager = _manager([])
        assert manager.completeTask("FAKEID").completed
        moved = manager.moveTask("FAKEID", datetime(2024, 2, 3))
        assert moved.due_date == "2024-02-03"
        calls = manager.service.fake_tasks.calls
        assert calls[0]["body"] == {"status": "completed"}
        assert calls[1]["body"] == {"due": "2024-02-03T00:00:00.000Z"}


class TestEvent:
    def test_all_day_end_is_inclusive(self):
        event = Event(
            {
                "id": "EV",
                "summary": "Tahoe",
                "start": {"date": "2026-08-07"},
                "end": {"date": "2026-08-15"},
            }
        )
        assert event.all_day
        assert event.toString(False) == "(2026-08-07 -> 2026-08-14) Tahoe"

    def test_put_event_body(self):
        inserted = []

        class FakeEvents(object):
            def insert(self, calendarId, body):
                inserted.append(body)
                return _FakeRequest(dict(body, id="EV"))

        class FakeCalendar(object):
            def events(self):
                return FakeEvents()

        manager = EventManager(calendar_time_zone="America/Los_Angeles")
        manager._service = FakeCalendar()
        manager.putEvent("Trip", datetime(2026, 8, 7), datetime(2026, 8, 14), True, "link")
        manager.putEvent(
            "Dinner", datetime(2026, 8, 7, 18, 30), datetime(2026, 8, 7, 20, 0), False
        )
        assert inserted[0]["end"] == {"date": "2026-08-15"}
        assert inserted[0]["description"] == "link"
        assert inserted[1]["start"] == {
            "dateTime": "2026-08-07T18:30:00",
            "timeZone": "America/Los_Angeles",
        }
        assert "description" not in inserted[1]


class TestCli:
    def test_spec_marker(self):
        notes = "desc\n\nspec: m|P0: Reach out to Siblings|2026-12-06"
        assert SPEC_MARKER_RE.findall(notes) == [
            ("m", "P0: Reach out to Siblings", "2026-12-06")
        ]

    def test_parse_move_file(self, tmp_path):
        move_file = tmp_path / "moves.txt"
        move_file.write_text("# header\nAAA 2026-11-04\nBBB|2026-11-07  # note\n\n")
        assert _parse_move_file(str(move_file)) == [
            ("AAA", datetime(2026, 11, 4)),
            ("BBB", datetime(2026, 11, 7)),
        ]

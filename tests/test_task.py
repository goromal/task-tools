import pytest
from task_tools.manage import Task

class TestTask:
    mockdata1 = {
        "id": "FAKEID",
        "title": "P0: Do something!",
        "due": "2024-01-01T00:00:00.00",
        "notes": "Some notes."
    }
    def test_initialization(self):
        task = Task(TestTask.mockdata1)
        assert task.due == "2024-01-01"

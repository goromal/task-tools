import logging
import sys
from datetime import datetime, timedelta

from easy_google_auth.auth import getGoogleService
from task_tools.defaults import TaskToolsDefaults as TTD

class Task(object):
    def __init__(self, data):
        self.name = data["title"]
        self.due = data["due"].split("T")[0]
        self.notes = data["notes"].replace("\n", "\n    ") if "notes" in data else None
    
    def __repr__(self):
        base = f"(Due {self.due}) '{self.name}'"
        if self.notes is not None:
            base += f"\n    {self.notes}"
        return base

class TaskManager(object):
    def __init__(self, **kwargs):
        self.enable_logging = TTD.getKwargsOrDefault("enable_logging", **kwargs)
        if self.enable_logging:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        self.service = getGoogleService(
            "tasks",
            "v1",
            TTD.getKwargsOrDefault("task_secrets_file", **kwargs),
            TTD.getKwargsOrDefault("task_refresh_token", **kwargs),
            TTD.getKwargsOrDefault("task_scope", **kwargs)
        )

    def getTasks(self, date=None):
        if date is None:
            date = datetime.today()
        fdate = f"{(date + timedelta(1)).strftime('%Y-%m-%d')}T23:00:00.000Z"
        results = self.service.tasks().list(tasklist="MDY2MzkyMzI4NTQ1MTA0NDUwODY6MDow", showCompleted=False, dueMax=fdate).execute()
        items = results.get('items', [])
        if not items:
            if self.enable_logging:
                logging.warn(f"No tasks found through {date}.")
            return []
        return [Task(item) for item in items]

    def putTask(self, name, notes, date=None):
        if date is None:
            date = datetime.today()
        fdate = f"{date.strftime('%Y-%m-%d')}T00:00:00.000Z"
        body = {
            "status": "needsAction",
            "kind": "tasks#task",
            "title": name,
            "notes": notes,
            "due": fdate,
        }
        if self.enable_logging:
            logging.info(f"Creating task {name} (due {date})")
        self.service.tasks().insert(tasklist="MDY2MzkyMzI4NTQ1MTA0NDUwODY6MDow", body=body).execute()

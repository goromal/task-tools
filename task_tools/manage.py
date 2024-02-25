import logging
import sys
from datetime import datetime, timedelta

from easy_google_auth.auth import getGoogleService
from task_tools.defaults import TaskToolsDefaults as TTD

def dateTimeToGoogleDate(date_time):
    return f"{date_time.strftime('%Y-%m-%d')}T23:59:59.000Z"

def googleDateToDateTime(google_date):
    return datetime.strptime(google_date.split("T")[0], "%Y-%m-%d")

class Task(object):
    def __init__(self, data):
        self.id = data["id"]
        self.name = data["title"]
        created_date = googleDateToDateTime(data["due"])
        if self.name[:3] == "P0:":
            self.timing = 0
            self.autogen = ("[T]" in self.name)
            due_date = created_date + datetime.timedelta(days=0)
            self.due = due_date.strftime("%y-%m-%d")
            self.days_late = max((datetime.today() - due_date).days, 0)
        elif self.name[:3] == "P1:":
            self.timing = 1
            self.autogen = ("[T]" in self.name)
            due_date = created_date + datetime.timedelta(days=5)
            self.due = due_date.strftime("%y-%m-%d")
            self.days_late = max((datetime.today() - due_date).days, 0)
        elif self.name[:3] == "P2:":
            self.timing = 2
            self.autogen = ("[T]" in self.name)
            due_date = created_date + datetime.timedelta(days=27)
            self.due = due_date.strftime("%y-%m-%d")
            self.days_late = max((datetime.today() - due_date).days, 0)
        else:
            self.timing = -1
            self.autogen = False
            self.due = data["due"].split("T")[0]
            self.days_late = 0
        self.notes = data["notes"].replace("\n", "\n    ") if "notes" in data else None
    
    def toString(self, show_id=True):
        if self.timing >= 0 and self.days_late > 0:
            timed_info = f"[LATE {self.days_late} DAYS] "
        else:
            timed_info = ""
        if show_id:
            id_info = f" < {self.id} >"
        else:
            id_info = ""
        return f"(Due {self.due}) {timed_info}'{self.name}'{id_info}"

    def __repr__(self):
        return self.toString()

class TaskManager(object):
    def __init__(self, **kwargs):
        self.enable_logging = TTD.getKwargsOrDefault("enable_logging", **kwargs)
        if self.enable_logging:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        self.task_list_id = TTD.getKwargsOrDefault("task_list_id", **kwargs)
        self.service = getGoogleService(
            "tasks",
            "v1",
            TTD.getKwargsOrDefault("task_secrets_file", **kwargs),
            TTD.getKwargsOrDefault("task_refresh_token", **kwargs),
            TTD.getKwargsOrDefault("task_scope", **kwargs),
            headless=True
        )

    def getTasks(self, date=None, start_date=None):
        if date is None:
            date = datetime.today()
        fdate = dateTimeToGoogleDate(date + timedelta(days=1))
        if start_date is None:
            results = self.service.tasks().list(tasklist=self.task_list_id, maxResults=100, showCompleted=False, dueMax=fdate).execute()
        else:
            fmindate = dateTimeToGoogleDate(start_date - timedelta(days=1))
            results = self.service.tasks().list(tasklist=self.task_list_id, maxResults=100, showCompleted=False, dueMin=fmindate, dueMax=fdate).execute()
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
        self.service.tasks().insert(tasklist=self.task_list_id, body=body).execute()
    
    def deleteTask(self, task_id):
        self.service.tasks().delete(tasklist=self.task_list_id, task=task_id).execute()

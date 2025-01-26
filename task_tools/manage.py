import logging
import sys
from datetime import datetime, timedelta

from easy_google_auth.auth import getRateLimitedGoogleService
from task_tools.defaults import TaskToolsDefaults as TTD


def dateTimeToGoogleDate(date_time):
    return f"{date_time.strftime('%Y-%m-%d')}T23:59:59.000Z"


def googleDateToDateTime(google_date):
    return datetime.strptime(google_date.split("T")[0], "%Y-%m-%d")


class Task(object):
    task_types = {
        # label: (timing id, days of leeway),
        "P0:": (0, 0),
        "P1:": (1, 6),
        "P2:": (2, 27),
        "P3:": (3, 90),
    }

    def __init__(self, data):
        self.id = data["id"]
        self.name = data["title"]
        created_date = googleDateToDateTime(data["due"])
        if self.name[:3] in Task.task_types:
            self.timing = Task.task_types[self.name[:3]][0]
            self.autogen = "[T]" in self.name
            due_date = created_date + timedelta(days=Task.task_types[self.name[:3]][1])
            self.days_score = (datetime.today() - due_date).days
            self.due = due_date.strftime("%Y-%m-%d")
            self.days_late = max(self.days_score, 0)
        else:
            self.timing = -1
            self.autogen = False
            self.days_score = 0
            self.due = data["due"].split("T")[0]
            self.days_late = 0
        self.notes = data["notes"].replace("\n", "\n    ") if "notes" in data else None

    def toString(self, show_id=True, show_due=True, show_bar=False):
        if self.timing >= 0 and self.days_late > 0 and show_due:
            timed_info = f"[LATE {self.days_late} DAYS] "
        else:
            timed_info = ""
        if show_due:
            due_info = f"(Due {self.due}) "
        else:
            due_info = ""
        if show_bar and self.timing >= 0:
            normalized_score = 1.0 - (
                float(max(-self.days_score, 0))
                / max(float(Task.task_types[self.name[:3]][1]), 1.0)
            )
            if 0 <= normalized_score < 0.25:
                bar_info = "🟩🟩🟩🟩 "
            elif 0.25 <= normalized_score < 0.5:
                bar_info = "🟥🟩🟩🟩 "
            elif 0.5 <= normalized_score < 0.75:
                bar_info = "🟥🟥🟩🟩 "
            elif 0.75 <= normalized_score < 1.0:
                bar_info = "🟥🟥🟥🟩 "
            else:
                bar_info = "🟥🟥🟥🟥 "
        else:
            bar_info = ""
        if show_id:
            id_info = f" < {self.id} >"
        else:
            id_info = ""
        return f"{bar_info}{due_info}{timed_info}{self.name}{id_info}"

    def __repr__(self):
        return self.toString()


class TaskManager(object):
    def _check_valid_interface(func):
        def wrapper(self, *args, **kwargs):
            if self.service is None:
                raise Exception(
                    "Tasks interface not initialized properly; check your secrets"
                )
            return func(self, *args, **kwargs)

        return wrapper

    def __init__(self, **kwargs):
        self.enable_logging = TTD.getKwargsOrDefault("enable_logging", **kwargs)
        if self.enable_logging:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        self.task_list_id = TTD.getKwargsOrDefault("task_list_id", **kwargs)
        self.service = None
        try:
            self.service = getRateLimitedGoogleService(
                "tasks",
                "v1",
                TTD.getKwargsOrDefault("task_secrets_file", **kwargs),
                TTD.getKwargsOrDefault("task_refresh_token", **kwargs),
                headless=True,
                max_rate_per_sec=1.0,
            )
        except:
            pass

    @_check_valid_interface
    def getTasks(self, date=None, start_date=None):
        if date is None:
            date = datetime.today()
        fdate = dateTimeToGoogleDate(date + timedelta(days=1))
        if start_date is None:
            results = (
                self.service.tasks()
                .list(
                    tasklist=self.task_list_id,
                    maxResults=100,
                    showCompleted=False,
                    dueMax=fdate,
                )
                .execute()
            )
        else:
            fmindate = dateTimeToGoogleDate(start_date)  #  - timedelta(days=1))
            results = (
                self.service.tasks()
                .list(
                    tasklist=self.task_list_id,
                    maxResults=100,
                    showCompleted=False,
                    dueMin=fmindate,
                    dueMax=fdate,
                )
                .execute()
            )
        items = results.get("items", [])
        if not items:
            if self.enable_logging:
                logging.warn(f"No tasks found through {date}.")
            return []
        return [Task(item) for item in items]

    @_check_valid_interface
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

    @_check_valid_interface
    def deleteTask(self, task_id):
        self.service.tasks().delete(tasklist=self.task_list_id, task=task_id).execute()

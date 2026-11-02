import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from easy_google_auth.auth import (
    CredentialsRefreshException,
    getGoogleService,
    getRateLimitedGoogleService,
)
from task_tools.defaults import TaskToolsDefaults as TTD


def dateTimeToGoogleDate(date_time):
    return f"{date_time.strftime('%Y-%m-%d')}T23:59:59.000Z"


def dateTimeToGoogleDueDate(date_time):
    return f"{date_time.strftime('%Y-%m-%d')}T00:00:00.000Z"


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
        self.due_date = data["due"].split("T")[0]
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
        self.raw_notes = data.get("notes", "")
        self.completed = data.get("status") == "completed"

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
    def getTasks(self, date=None, start_date=None, show_completed=False):
        if date is None:
            date = datetime.today()
        list_kwargs = {
            "tasklist": self.task_list_id,
            "maxResults": 100,
            "showCompleted": show_completed,
            "dueMax": dateTimeToGoogleDate(date + timedelta(days=1)),
        }
        if show_completed:
            # Tasks completed in first-party clients are hidden, not just completed
            list_kwargs["showHidden"] = True
        if start_date is not None:
            list_kwargs["dueMin"] = dateTimeToGoogleDate(start_date)
        items = []
        while True:
            results = self.service.tasks().list(**list_kwargs).execute()
            items += results.get("items", [])
            page_token = results.get("nextPageToken")
            if not page_token:
                break
            list_kwargs["pageToken"] = page_token
        if not items:
            if self.enable_logging:
                logging.warn(f"No tasks found through {date}.")
            return []
        return [Task(item) for item in items if "due" in item]

    @_check_valid_interface
    def putTask(self, name, notes, date=None):
        if date is None:
            date = datetime.today()
        fdate = dateTimeToGoogleDueDate(date)
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

    @_check_valid_interface
    def completeTask(self, task_id):
        if self.enable_logging:
            logging.info(f"Completing task {task_id}")
        return Task(
            self.service.tasks()
            .patch(
                tasklist=self.task_list_id,
                task=task_id,
                body={"status": "completed"},
            )
            .execute()
        )

    @_check_valid_interface
    def moveTask(self, task_id, date):
        if self.enable_logging:
            logging.info(f"Moving task {task_id} to {date}")
        return Task(
            self.service.tasks()
            .patch(
                tasklist=self.task_list_id,
                task=task_id,
                body={"due": dateTimeToGoogleDueDate(date)},
            )
            .execute()
        )


class Event(object):
    def __init__(self, data):
        self.id = data["id"]
        self.name = data.get("summary", "(No title)")
        self.description = data.get("description")
        self.all_day = "date" in data["start"]
        if self.all_day:
            self.start = data["start"]["date"]
            # Google all-day end dates are exclusive
            self.end = (
                datetime.strptime(data["end"]["date"], "%Y-%m-%d") - timedelta(days=1)
            ).strftime("%Y-%m-%d")
        else:
            self.start = data["start"]["dateTime"][:16].replace("T", " ")
            self.end = data["end"]["dateTime"][:16].replace("T", " ")

    def toString(self, show_id=True):
        if self.start == self.end:
            when = self.start
        else:
            when = f"{self.start} -> {self.end}"
        id_info = f" < {self.id} >" if show_id else ""
        return f"({when}) {self.name}{id_info}"

    def __repr__(self):
        return self.toString()


class EventManager(object):
    def __init__(self, **kwargs):
        self.calendar_id = TTD.getKwargsOrDefault("calendar_id", **kwargs)
        self.time_zone = TTD.getKwargsOrDefault("calendar_time_zone", **kwargs)
        self.secrets_file = TTD.getKwargsOrDefault("task_secrets_file", **kwargs)
        self.refresh_token = TTD.getKwargsOrDefault(
            "calendar_refresh_token", **kwargs
        )
        self._service = None

    @property
    def service(self):
        if self._service is None:
            try:
                self._service = getGoogleService(
                    "calendar",
                    "v3",
                    self.secrets_file,
                    self.refresh_token,
                    headless=True,
                    scope=TTD.CALENDAR_SCOPE,
                )
            except CredentialsRefreshException:
                raise Exception(
                    "Calendar credentials missing or expired; refresh the Calendar token in the Auth UI"
                )
        return self._service

    def getEvents(self, start_date, end_date):
        # Day boundaries in the calendar's time zone, not UTC
        tz = ZoneInfo(self.time_zone)
        time_min = datetime(start_date.year, start_date.month, start_date.day, tzinfo=tz)
        time_max = datetime(end_date.year, end_date.month, end_date.day, tzinfo=tz)
        time_min = time_min.isoformat()
        time_max = (time_max + timedelta(days=1)).isoformat()
        list_kwargs = {
            "calendarId": self.calendar_id,
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": self.time_zone,
        }
        items = []
        while True:
            results = self.service.events().list(**list_kwargs).execute()
            items += results.get("items", [])
            page_token = results.get("nextPageToken")
            if not page_token:
                break
            list_kwargs["pageToken"] = page_token
        return [Event(item) for item in items]

    def putEvent(self, title, start, end, all_day, description=None):
        if all_day:
            # Google all-day end dates are exclusive
            body = {
                "start": {"date": start.strftime("%Y-%m-%d")},
                "end": {"date": (end + timedelta(days=1)).strftime("%Y-%m-%d")},
            }
        else:
            body = {
                "start": {
                    "dateTime": start.strftime("%Y-%m-%dT%H:%M:00"),
                    "timeZone": self.time_zone,
                },
                "end": {
                    "dateTime": end.strftime("%Y-%m-%dT%H:%M:00"),
                    "timeZone": self.time_zone,
                },
            }
        body["summary"] = title
        if description:
            body["description"] = description
        return Event(
            self.service.events()
            .insert(calendarId=self.calendar_id, body=body)
            .execute()
        )

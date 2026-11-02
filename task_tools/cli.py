import click
import datetime
import os
import re

from task_tools.defaults import TaskToolsDefaults as TTD
from task_tools.manage import EventManager, TaskManager

SPEC_MARKER_RE = re.compile(r"spec: ([dwmq])\|([^|\n]*)\|(\d{4}-\d{2}-\d{2})")

def _get_next_sunday(include_today = False):
    today = datetime.date.today()
    if today.weekday() == 6:  # Sunday
        if include_today:
            return today
        else:
            return today + datetime.timedelta(days=7)
    days_ahead = 6 - today.weekday()
    return today + datetime.timedelta(days=days_ahead)

def _get_first_sunday_next_month(include_today = False):
    today = datetime.date.today()
    # If today is the first Sunday of the month, return today
    if include_today:
        if today.weekday() == 6 and today.day <= 7:
            return today
    # Move to the next month
    year = today.year + (today.month // 12)
    month = (today.month % 12) + 1
    for day in range(1, 8):
        date = datetime.date(year, month, day)
        if date.weekday() == 6:  # Sunday
            return date

def _first_day_of_quarter(ref_date, offset_quarters=1):
    current_quarter = (ref_date.month - 1) // 3
    target_quarter = current_quarter + offset_quarters
    target_year = ref_date.year + target_quarter // 4
    target_quarter = target_quarter % 4
    first_month = 3 * target_quarter + 1
    return datetime.date(target_year, first_month, 1)

def _first_sunday_on_or_after(d):
    days_until_sunday = (6 - d.weekday()) % 7
    return d + datetime.timedelta(days=days_until_sunday)

_DAY_TOKENS = {"sun": 6, "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5}


def parse_interval(token: str) -> tuple[str, int]:
    """Return (interval_type, weekday) for a CSV interval token.

    weekday is datetime.weekday() int (Mon=0, Sun=6); only meaningful for 'w'.
    Plain 'w' returns ('w', 6) — Sunday default.
    """
    token = token.strip().lower()
    if ":" in token:
        itype, day = token.split(":", 1)
        if itype != "w":
            raise ValueError(f"Day qualifier ':{day}' is only valid for 'w' intervals, got '{itype}'")
        if day not in _DAY_TOKENS:
            raise ValueError(f"Unknown day token '{day}' in interval '{token}'")
        return itype, _DAY_TOKENS[day]
    return token, 6


def _all_weeks_on_day(start, end, weekday: int):
    """Return all datetimes in [start, end] that fall on the given weekday (Mon=0, Sun=6)."""
    result = []
    current = start
    while current.weekday() != weekday:
        current += datetime.timedelta(days=1)
    while current <= end:
        result.append(current)
        current += datetime.timedelta(days=7)
    return result

def _first_sunday_of_next_quarter(ref_date=None):
    if ref_date is None:
        ref_date = datetime.date.today()
    first_day = _first_day_of_quarter(ref_date, offset_quarters=1)
    return _first_sunday_on_or_after(first_day)

def _first_sunday_of_quarter_after_next(ref_date=None):
    if ref_date is None:
        ref_date = datetime.date.today()
    first_day = _first_day_of_quarter(ref_date, offset_quarters=2)
    return _first_sunday_on_or_after(first_day)

@click.group()
@click.pass_context
@click.option(
    "--task-secrets-file",
    "task_secrets_file",
    type=click.Path(),
    default=TTD.TASK_SECRETS_FILE,
    show_default=True,
    help="Google Tasks client secrets file.",
)
@click.option(
    "--task-refresh-token",
    "task_refresh_token",
    type=click.Path(),
    default=TTD.TASK_REFRESH_TOKEN,
    show_default=True,
    help="Google Tasks refresh file (if it exists).",
)
@click.option(
    "--task-list-id",
    "task_list_id",
    type=str,
    default=TTD.TASK_LIST_ID,
    show_default=True,
    help="UUID of the Task List to query.",
)
@click.option(
    "--enable-logging",
    "enable_logging",
    type=bool,
    default=TTD.ENABLE_LOGGING,
    show_default=True,
    help="Whether to enable logging.",
)
def cli(
    ctx: click.Context,
    task_secrets_file,
    task_refresh_token,
    task_list_id,
    enable_logging,
):
    """Manage Google Tasks."""
    try:
        ctx.obj = TaskManager(
            task_secrets_file=task_secrets_file,
            task_refresh_token=task_refresh_token,
            task_list_id=task_list_id,
            enable_logging=enable_logging,
        )
    except Exception as e:
        print(f"Program error: {e}")
        exit(1)


@cli.command()
@click.pass_context
@click.argument(
    "filter",
    type=str,
)
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Maximum due date for filtering tasks.",
)
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Minimum due date for filtering tasks (default: no minimum).",
)
@click.option(
    "--no-ids",
    "no_ids",
    is_flag=True,
    help="Don't show the UUIDs.",
)
@click.option(
    "--notes",
    "show_notes",
    is_flag=True,
    help="Show task notes.",
)
def list(ctx: click.Context, filter, date, start_date, no_ids, show_notes):
    """List pending tasks according to a filter ∈ [all, p0, p1, p2, p3, late, ranked]."""
    tasks = ctx.obj.getTasks(date, start_date=start_date)
    show_bar = False
    if filter == "all":
        filtered_tasks = tasks
    elif filter == "p0":
        filtered_tasks = [
            task for task in tasks if task.timing == 0 and task.days_late == 0
        ]
    elif filter == "p1":
        filtered_tasks = [
            task for task in tasks if task.timing == 1 and task.days_late == 0
        ]
    elif filter == "p2":
        filtered_tasks = [
            task for task in tasks if task.timing == 2 and task.days_late == 0
        ]
    elif filter == "p3":
        filtered_tasks = [
            task for task in tasks if task.timing == 3 and task.days_late == 0
        ]
    elif filter == "late":
        filtered_tasks = [
            task for task in tasks if task.timing >= 0 and task.days_late > 0
        ]
    elif filter == "ranked":
        show_bar = True
        raw_tasks = [task for task in tasks if task.timing >= 0]
        filtered_tasks = sorted(raw_tasks, key=lambda t: -t.days_score)
    elif filter == "":
        print("ERROR: no list filter provided.")
        exit(1)
    else:
        print(f"ERROR: unrecognized filter provided ({filter})")
        exit(1)
    for task in filtered_tasks:
        print(f"{task.toString(not no_ids, not show_bar, show_bar)}")
        if show_notes and task.notes:
            print(f"    {task.notes}")


@cli.command()
@click.pass_context
@click.argument(
    "task_id",
    type=str,
)
def delete(ctx: click.Context, task_id):
    """Delete a particular task by UUID."""
    try:
        ctx.obj.deleteTask(task_id)
    except Exception as e:
        print(f"Program error: {e}")
        exit(1)
    print(f"Task {task_id} deleted.")


@cli.command()
@click.pass_context
@click.argument(
    "task_ids",
    type=str,
    nargs=-1,
    required=True,
)
def complete(ctx: click.Context, task_ids):
    """Mark one or more tasks (by UUID) as completed."""
    for task_id in task_ids:
        try:
            task = ctx.obj.completeTask(task_id)
        except Exception as e:
            print(f"Program error: {e}")
            exit(1)
        print(f"Task {task.name} < {task_id} > completed.")


@cli.command()
@click.pass_context
@click.argument(
    "name_substr",
    type=str,
)
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Due date of the task(s) to complete.",
)
def complete_by_name(ctx: click.Context, name_substr, date):
    """Mark all pending tasks due on a date whose names contain a substring as completed."""
    matches = [task for task in ctx.obj.getTasks(date, date) if name_substr in task.name]
    if not matches:
        print(f"No pending tasks matching '{name_substr}' due {date.strftime('%Y-%m-%d')}.")
        exit(1)
    for task in matches:
        try:
            ctx.obj.completeTask(task.id)
        except Exception as e:
            print(f"Program error: {e}")
            exit(1)
        print(f"Task {task.name} < {task.id} > completed.")


def _parse_move_file(move_file):
    moves = []
    with open(os.path.expanduser(move_file), "r") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.split("#")[0].strip()
            if not line:
                continue
            fields = [field for field in re.split(r"[|\s]+", line) if field]
            if len(fields) != 2:
                raise click.ClickException(
                    f"{move_file}:{lineno}: expected '<task-id> <YYYY-MM-DD>'"
                )
            try:
                date = datetime.datetime.strptime(fields[1], "%Y-%m-%d")
            except ValueError:
                raise click.ClickException(
                    f"{move_file}:{lineno}: invalid date '{fields[1]}'"
                )
            moves.append((fields[0], date))
    return moves


@cli.command()
@click.pass_context
@click.argument(
    "task_id",
    type=str,
    required=False,
)
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="New due date for TASK_ID.",
)
@click.option(
    "--from-file",
    "move_file",
    type=click.Path(exists=True),
    default=None,
    help="File of '<task-id> <YYYY-MM-DD>' lines (whitespace- or pipe-delimited; # comments).",
)
def move(ctx: click.Context, task_id, date, move_file):
    """Change the due date of a task in place, keeping its UUID, title, and notes."""
    if move_file is not None:
        if task_id is not None or date is not None:
            raise click.UsageError("--from-file cannot be combined with TASK_ID/--date.")
        moves = _parse_move_file(move_file)
    elif task_id is not None and date is not None:
        moves = [(task_id, date)]
    else:
        raise click.UsageError("Provide TASK_ID and --date, or --from-file.")
    for move_id, move_date in moves:
        try:
            task = ctx.obj.moveTask(move_id, move_date)
        except Exception as e:
            print(f"Program error moving {move_id}: {e}")
            exit(1)
        print(f"{move_date.strftime('%Y-%m-%d')}: {task.name} < {move_id} >")


@cli.command()
@click.pass_context
@click.argument(
    "name_substr",
    type=str,
)
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="First day of the window.",
)
@click.option(
    "--end-date",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date(datetime.datetime.today().year, 12, 31)),
    show_default=True,
    help="Last day of the window.",
)
def delete_by_name(ctx: click.Context, name_substr, start_date, end_date):
    """Delete all tasks in a range by name."""
    current_date = start_date
    while current_date <= end_date:
        print(f"Scanning {current_date}...")
        tasks = ctx.obj.getTasks(current_date, current_date)
        for task in tasks:
            if name_substr in task.name:
                print(f"  Deleting task {task.name} on date {current_date}")
                try:
                    ctx.obj.deleteTask(task.id)
                except Exception as e:
                    print(f"Program error: {e}")
                    exit(1)
        current_date += datetime.timedelta(days=1)


@cli.command()
@click.pass_context
@click.option(
    "--name",
    "name",
    type=str,
    required=True,
    help="Name of the task.",
)
@click.option(
    "--notes",
    "notes",
    type=str,
    default="",
    show_default=True,
    help="Notes to add to the task description.",
)
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Task due date.",
)
@click.option(
    "--until",
    "until",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Specify an end date if for multiple days.",
)
def put(ctx: click.Context, name, notes, date, until):
    """Upload a task."""
    current_date = date
    end_date = until if until >= date else date
    while current_date <= end_date:
        print(f"{current_date.strftime('%Y-%m-%d')}: {name}")
        ctx.obj.putTask(name, notes, current_date)
        current_date += datetime.timedelta(days=1)


@cli.command()
@click.pass_context
@click.option(
    "--spec-csv",
    "spec_csv",
    type=click.Path(),
    default="~/configs/intervaled-tasks.csv",
    show_default=True,
    help="Path to the CSV containing the task specs.",
)
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(_first_sunday_of_next_quarter()),
    show_default=True,
    help="First day of the window.",
)
@click.option(
    "--end-date",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(_first_sunday_of_quarter_after_next()),
    show_default=True,
    help="Last day of the window.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="Do a dry run; no task creations.",
)
@click.option(
    "--only",
    "only_titles",
    type=str,
    multiple=True,
    help="Only put the spec line(s) with this title (repeatable).",
)
def put_spec(ctx: click.Context, spec_csv, start_date, end_date, dry_run, only_titles):
    """Read a CSV of task specifications and idempotently put them on your calendar.

    CSV must be pipe-delimited. Example:

    d | "Daily Task Name" | "Task Description"
    w | "Weekly Task Name" | "Each Sunday"
    w:fri | "Weekly Task Name" | "Each Friday (any of sun, mon, ..., sat)"
    m | "Monthly Task Name" | "First Sunday of each Month"
    q | "Quarterly Task Name" | "First Sunday of each Quarter"

    A spec instance is skipped if a task (pending or completed) with the same
    title is already due that day, or if a task carrying that instance's
    "spec: <type>|<title>|<date>" notes marker exists anywhere near the window
    (i.e., it was generated by put-spec and then moved).
    """
    spec_csv = os.path.expanduser(spec_csv)

    daily_task_specs = []
    weekly_specs_by_day = {}
    first_sundays_of_month = []
    monthly_task_specs = []
    first_sundays_of_quarter = []
    quarterly_task_specs = []

    month = start_date.month
    year = start_date.year
    quarter_months = (1, 4, 7, 10)

    while datetime.datetime(year, month, 1) <= end_date:
        first_of_month = datetime.datetime(year, month, 1)
        while first_of_month.weekday() != 6:
            first_of_month += datetime.timedelta(days=1)
        if start_date <= first_of_month <= end_date:
            first_sundays_of_month.append(first_of_month)
            if month in quarter_months:
                first_sundays_of_quarter.append(first_of_month)
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

    only_titles = {title.strip() for title in only_titles}
    found_titles = set()
    with open(spec_csv, "r") as csvfile:
        for specline in csvfile:
            speclist = specline.split("|")
            if len(speclist) > 1:
                rtype = speclist[0].strip().lower()
                ttitle = speclist[1]
                tdesc = speclist[2]
                if only_titles:
                    if ttitle.strip() not in only_titles:
                        continue
                    found_titles.add(ttitle.strip())
                itype, weekday = parse_interval(rtype)
                if itype == "d":
                    daily_task_specs.append((ttitle, tdesc))
                elif itype == "w":
                    weekly_specs_by_day.setdefault(weekday, []).append((ttitle, tdesc))
                elif itype == "m":
                    monthly_task_specs.append((ttitle, tdesc))
                elif itype == "q":
                    quarterly_task_specs.append((ttitle, tdesc))
    missing_titles = only_titles - found_titles
    if missing_titles:
        print(f"ERROR: no spec lines found for --only {sorted(missing_titles)}")
        exit(1)

    # Fetch every task near the window once, including completed ones, so that
    # completed or moved instances are not regenerated.
    margin = datetime.timedelta(days=92)
    existing_titles = {}
    existing_markers = set()
    for task in ctx.obj.getTasks(
        date=end_date + margin, start_date=start_date - margin, show_completed=True
    ):
        existing_titles.setdefault(task.due_date, set()).add(task.name)
        existing_markers.update(SPEC_MARKER_RE.findall(task.raw_notes))

    def put_if_missing(rtype, task_title, task_description, date):
        date_str = date.strftime("%Y-%m-%d")
        marker = (rtype, task_title, date_str)
        if task_title in existing_titles.get(date_str, set()):
            return
        if marker in existing_markers:
            return
        print(f"  {task_title}")
        if not dry_run:
            notes = task_description.rstrip()
            notes = f"{notes}\n\n" if notes else ""
            notes += f"spec: {rtype}|{task_title}|{date_str}"
            ctx.obj.putTask(task_title, notes, date)

    weekly_dates_by_day = {day: set(_all_weeks_on_day(start_date, end_date, day)) for day in weekly_specs_by_day}

    current_date = start_date
    while current_date <= end_date:
        print(f"Tasks for {current_date.strftime('%Y-%m-%d')}:")
        for task_title, task_description in daily_task_specs:
            put_if_missing("d", task_title, task_description, current_date)
        for day, specs in weekly_specs_by_day.items():
            if current_date in weekly_dates_by_day[day]:
                for task_title, task_description in specs:
                    put_if_missing("w", task_title, task_description, current_date)
        if current_date in first_sundays_of_month:
            for task_title, task_description in monthly_task_specs:
                put_if_missing("m", task_title, task_description, current_date)
        if current_date in first_sundays_of_quarter:
            for task_title, task_description in quarterly_task_specs:
                put_if_missing("q", task_title, task_description, current_date)
        current_date += datetime.timedelta(days=1)


@cli.command()
@click.pass_context
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today() - datetime.timedelta(days=7)),
    show_default=True,
    help="First day of the grading window.",
)
@click.option(
    "--end-date",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Last day of the grading window.",
)
@click.option(
    "-o",
    "--out",
    "out_file",
    type=click.Path(),
    default=TTD.GRADER_OUTPUT_FILE,
    show_default=True,
    help="CSV file to generate the report in.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="Do a dry run; no task deletions.",
)
def grader(ctx: click.Context, start_date, end_date, out_file, dry_run):
    """Generate a CSV report of how consistently tasks have been completed within the specified window.

    Grading criteria:\n
    - P0: ... tasks must be completed same day. They will be carried over day to day until completed.\n
    - P1: ... tasks can wait until the next weekly planning session to get scheduled.\n
    - P2: ... tasks can wait until the next monthly planning session to get scheduled.

    Deletion / failure criteria:\n
    - P[0-3]: [T] ... tasks that have not be completed within the appropriate window.

    Migration patterns:\n
    - P0 manually generated tasks will be migrated to the current day.\n
    - P1 tasks get migrated to P0 tasks at the start of next week.\n
    - P2 tasks get migrated to P0 tasks at the start of next month.
    """
    with open(os.path.expanduser(out_file), "a") as logfile:
        tasks = ctx.obj.getTasks(
            end_date, start_date=start_date - datetime.timedelta(days=1)
        )
        on_time_tasks = []
        late_tasks = []
        migrate_tasks = []
        migrate_p1_tasks = []
        migrate_p2_tasks = []
        failed_tasks = []
        for task in tasks:
            if task.timing >= 0:
                if task.timing == 2: # P2 tasks get migrated to P0 tasks at the start of next month
                    migrate_p2_tasks.append(task)
                elif task.timing == 1: # P1 tasks get migrated to P0 tasks at the start of next week
                    migrate_p1_tasks.append(task)
                else: # P0 task grading
                    late = task.days_late > 0
                    failed = task.autogen and late
                    logfile.write(
                        f"{task.id}|{task.due}|{task.name}|{task.days_late}|{failed}\n"
                    )
                    if late:
                        if failed:
                            failed_tasks.append(
                                (task.days_late, task.id, task.toString(False))
                            )
                        else:
                            late_tasks.append((task.days_late, task, task.toString(False)))
                    else:
                        on_time_tasks.append(task.toString(False))
        if len(on_time_tasks) > 0:
            sorted_on_time_tasks = sorted(on_time_tasks)
            print("PENDING TASKS:")
            for task in sorted_on_time_tasks:
                print(f"- {task}")
        else:
            print("NO PENDING TASKS")
        print()
        if len(late_tasks) > 0:
            sorted_late_tasks = sorted(late_tasks, key=lambda k: -k[0])
            print("LATE TASKS:")
            for _, task, taskname in sorted_late_tasks:
                to_migrate = task.timing == 0 and not task.autogen
                print(f"- {taskname}{' [TO MIGRATE]' if to_migrate else ''}")
                if to_migrate:
                    migrate_tasks.append(task)
            if len(migrate_tasks) > 0 and not dry_run:
                print("\nMigrating applicable late tasks...")
                for migrate_task in migrate_tasks:
                    ctx.obj.putTask(migrate_task.name, migrate_task.notes)
                    ctx.obj.deleteTask(migrate_task.id)
        else:
            print("NO LATE TASKS")
        print()
        if len(migrate_p1_tasks) > 0:
            print("Migrating p1 -> p0:")
            for task in migrate_p1_tasks:
                print(f"- {task.name}")
                ctx.obj.putTask(
                    task.name.replace("P1","P0").replace("p1","P0"),
                    task.notes,
                    _get_next_sunday()
                )
                ctx.obj.deleteTask(task.id)
        print()
        if len(migrate_p2_tasks) > 0:
            print("Migrating P2 -> p0:")
            for task in migrate_p2_tasks:
                print(f"- {task.name}")
                ctx.obj.putTask(
                    task.name.replace("P2","P0").replace("p2","P0"),
                    task.notes,
                    _get_first_sunday_next_month()
                )
                ctx.obj.deleteTask(task.id)
        print()
        if len(failed_tasks) > 0:
            sorted_failed_tasks = sorted(failed_tasks, key=lambda k: -k[0])
            print("FAILED TASKS:")
            for _, _, task in sorted_failed_tasks:
                print(f"- {task}")
            if not dry_run:
                print("\nDeleting failed tasks...")
                for _, task_id, _ in sorted_failed_tasks:
                    try:
                        ctx.obj.deleteTask(task_id)
                    except Exception as e:
                        print(f"WARNING: {e}")
                        continue
        else:
            print("NO FAILED TASKS")


@cli.command()
@click.pass_context
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today() - datetime.timedelta(days=7)),
    show_default=True,
    help="First day of the cleaning window.",
)
@click.option(
    "--end-date",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Last day of the cleaning window.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="Do a dry run; no task deletions.",
)
def clean(ctx: click.Context, start_date, end_date, dry_run):
    """Delete / clean up failed timed tasks.

    Timing criteria:\n
    - P0: ... tasks must be completed same day.\n
    - P1: ... tasks must be completed within a week.\n
    - P2: ... tasks must be completed within a month.\n
    - P3: ... tasks must be completed within 90 days.

    Deletion / failure criteria:\n
    - P[0-3]: [T] ... tasks that have not be completed within the appropriate window.

    Migration patterns:\n
    - P0 manually generated tasks will be migrated to the current day.\n
    - P1 tasks get migrated to P0 tasks at the start of next week.\n
    - P2 tasks get migrated to P0 tasks at the start of next month.
    """
    tasks = ctx.obj.getTasks(
        end_date, start_date=start_date - datetime.timedelta(days=1)
    )
    failed_tasks = []
    migrate_tasks = []
    migrate_p1_tasks = []
    migrate_p2_tasks = []
    for task in tasks:
        if task.timing >= 0:
            if task.timing == 2: # P2 tasks get migrated to P0 tasks at the start of next month
                migrate_p2_tasks.append(task)
            elif task.timing == 1: # P1 tasks get migrated to P0 tasks at the start of next week
                migrate_p1_tasks.append(task)
            else: # P0 task grading
                failed = task.autogen and task.days_late > 0
                if failed:
                    failed_tasks.append((task.days_late, task.id, task.toString(False)))
                migrate = task.days_late > 0 and not task.autogen and task.timing == 0
                if migrate:
                    migrate_tasks.append(task)
    if len(migrate_tasks) > 0:
        print("MIGRATABLE TASKS:")
        for task in migrate_tasks:
            print(f"- {task.name}")
        if not dry_run:
            print("\nMigrating tasks...")
            for migrate_task in migrate_tasks:
                ctx.obj.putTask(migrate_task.name, migrate_task.notes)
                ctx.obj.deleteTask(migrate_task.id)
    else:
        print("NO TASKS TO MIGRATE")
    print()
    if len(migrate_p1_tasks) > 0:
        print("Migrating p1 -> p0:")
        for task in migrate_p1_tasks:
            print(f"- {task.name}")
            ctx.obj.putTask(
                task.name.replace("P1","P0").replace("p1","P0"),
                task.notes,
                _get_next_sunday()
            )
            ctx.obj.deleteTask(task.id)
    print()
    if len(migrate_p2_tasks) > 0:
        print("Migrating P2 -> p0:")
        for task in migrate_p2_tasks:
            print(f"- {task.name}")
            ctx.obj.putTask(
                task.name.replace("P2","P0").replace("p2","P0"),
                task.notes,
                _get_first_sunday_next_month()
            )
            ctx.obj.deleteTask(task.id)
    print()
    if len(failed_tasks) > 0:
        sorted_failed_tasks = sorted(failed_tasks, key=lambda k: -k[0])
        print("FAILED TASKS:")
        for _, _, task in sorted_failed_tasks:
            print(f"- {task}")
        if not dry_run:
            print("\nDeleting failed tasks...")
            for _, task_id, _ in sorted_failed_tasks:
                try:
                    ctx.obj.deleteTask(task_id)
                except Exception as e:
                    print(f"WARNING: {e}")
                    continue
    else:
        print("NO FAILED TASKS")


@cli.group()
@click.pass_context
@click.option(
    "--calendar-refresh-token",
    "calendar_refresh_token",
    type=click.Path(),
    default=TTD.CALENDAR_REFRESH_TOKEN,
    show_default=True,
    help="Google Calendar refresh file (separate from the Tasks one; refreshed via the Auth UI).",
)
@click.option(
    "--calendar-id",
    "calendar_id",
    type=str,
    default=TTD.CALENDAR_ID,
    show_default=True,
    help="ID of the calendar to use.",
)
@click.option(
    "--time-zone",
    "time_zone",
    type=str,
    default=TTD.CALENDAR_TIME_ZONE,
    show_default=True,
    help="IANA time zone for timed events and listing.",
)
def event(ctx: click.Context, calendar_refresh_token, calendar_id, time_zone):
    """Manage Google Calendar events."""
    ctx.obj = EventManager(
        task_secrets_file=ctx.parent.params["task_secrets_file"],
        calendar_refresh_token=calendar_refresh_token,
        calendar_id=calendar_id,
        calendar_time_zone=time_zone,
    )


_EVENT_TIME_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]


@event.command(name="put")
@click.pass_context
@click.option(
    "--title",
    "title",
    type=str,
    required=True,
    help="Event title.",
)
@click.option(
    "--start",
    "start",
    type=click.DateTime(formats=_EVENT_TIME_FORMATS),
    required=True,
    help="Start date (all-day) or date and time (YYYY-MM-DDTHH:MM).",
)
@click.option(
    "--end",
    "end",
    type=click.DateTime(formats=_EVENT_TIME_FORMATS),
    default=None,
    help="Inclusive end date (all-day) or end date and time. Default: same day / one hour after start.",
)
@click.option(
    "--all-day",
    "all_day",
    is_flag=True,
    help="Make an all-day event (implied when --start has no time).",
)
@click.option(
    "--description",
    "description",
    type=str,
    default="",
    help="Event description.",
)
def event_put(ctx: click.Context, title, start, end, all_day, description):
    """Create a calendar event."""
    has_time = start.hour != 0 or start.minute != 0
    all_day = all_day or not has_time
    if end is None:
        end = start if all_day else start + datetime.timedelta(hours=1)
    if end < start:
        raise click.UsageError("--end must not be before --start.")
    try:
        created = ctx.obj.putEvent(title, start, end, all_day, description)
    except Exception as e:
        print(f"Program error: {e}")
        exit(1)
    print(f"Created {created.toString()}")


@event.command(name="list")
@click.pass_context
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="Last day to list events for.",
)
@click.option(
    "--start-date",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(datetime.date.today()),
    show_default=True,
    help="First day to list events for.",
)
@click.option(
    "--no-ids",
    "no_ids",
    is_flag=True,
    help="Don't show the event IDs.",
)
def event_list(ctx: click.Context, date, start_date, no_ids):
    """List calendar events in a date range."""
    try:
        events = ctx.obj.getEvents(start_date, date)
    except Exception as e:
        print(f"Program error: {e}")
        exit(1)
    for ev in events:
        print(ev.toString(not no_ids))


def main():
    cli()


if __name__ == "__main__":
    main()

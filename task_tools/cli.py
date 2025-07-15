import click
import datetime
import os
import time

from task_tools.defaults import TaskToolsDefaults as TTD
from task_tools.manage import TaskManager

def _get_next_sunday():
    today = datetime.date.today()
    if today.weekday() == 6:  # Sunday
        return today
    days_ahead = 6 - today.weekday()
    return today + datetime.timedelta(days=days_ahead)

def _get_first_sunday_next_month():
    today = datetime.date.today()
    # If today is the first Sunday of the month, return today
    if today.weekday() == 6 and today.day <= 7:
        return today
    # Move to the next month
    year = today.year + (today.month // 12)
    month = (today.month % 12) + 1
    for day in range(1, 8):
        date = datetime.date(year, month, day)
        if date.weekday() == 6:  # Sunday
            return date

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
    "--no-ids",
    "no_ids",
    is_flag=True,
    help="Don't show the UUIDs.",
)
def list(ctx: click.Context, filter, date, no_ids):
    """List pending tasks according to a filter ∈ [all, p0, p1, p2, p3, late, ranked]."""
    tasks = ctx.obj.getTasks(date)
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
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="Do a dry run; no task creations.",
)
def put_spec(ctx: click.Context, spec_csv, start_date, end_date, dry_run):
    """Read a CSV of task specifications and idempotently put them on your calendar.

    CSV must be pipe-delimited. Example:

    d | "Daily Task Name" | "Task Description"
    w | "Weekly Task Name" | "Each Sunday"
    m | "Monthly Task Name" | "First Sunday of each Month"
    q | "Quarterly Task Name" | "First Sunday of each Quarter"
    """
    spec_csv = os.path.expanduser(spec_csv)

    daily_task_specs = []
    all_sundays = []
    weekly_task_specs = []
    first_sundays_of_month = []
    monthly_task_specs = []
    first_sundays_of_quarter = []
    quarterly_task_specs = []

    current_date = start_date
    while current_date.weekday() != 6:
        current_date += datetime.timedelta(days=1)

    while current_date <= end_date:
        all_sundays.append(current_date)
        current_date += datetime.timedelta(days=7)

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

    with open(spec_csv, "r") as csvfile:
        for specline in csvfile:
            speclist = specline.split("|")
            if len(speclist) > 1:
                rtype = speclist[0]
                ttitle = speclist[1]
                tdesc = speclist[2]
                if rtype.lower() == "d":
                    daily_task_specs.append((ttitle, tdesc))
                elif rtype.lower() == "w":
                    weekly_task_specs.append((ttitle, tdesc))
                elif rtype.lower() == "m":
                    monthly_task_specs.append((ttitle, tdesc))
                elif rtype.lower() == "q":
                    quarterly_task_specs.append((ttitle, tdesc))

    current_date = start_date
    while current_date <= end_date:
        print(f"Tasks for {current_date.strftime('%Y-%m-%d')}:")
        existing_ttitles = [
            task.name
            for task in ctx.obj.getTasks(date=current_date, start_date=current_date)
        ]
        for task_title, task_description in daily_task_specs:
            if task_title not in existing_ttitles:
                print(f"  {task_title}")
                if not dry_run:
                    ctx.obj.putTask(task_title, task_description, current_date)
        if current_date in all_sundays:
            for task_title, task_description in weekly_task_specs:
                if task_title not in existing_ttitles:
                    print(f"  {task_title}")
                    if not dry_run:
                        ctx.obj.putTask(task_title, task_description, current_date)
        if current_date in first_sundays_of_month:
            for task_title, task_description in monthly_task_specs:
                if task_title not in existing_ttitles:
                    print(f"  {task_title}")
                    if not dry_run:
                        ctx.obj.putTask(task_title, task_description, current_date)
        if current_date in first_sundays_of_quarter:
            for task_title, task_description in quarterly_task_specs:
                if task_title not in existing_ttitles:
                    print(f"  {task_title}")
                    if not dry_run:
                        ctx.obj.putTask(task_title, task_description, current_date)
        current_date += datetime.timedelta(days=1)
        time.sleep(1.0)


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


def main():
    cli()


if __name__ == "__main__":
    main()

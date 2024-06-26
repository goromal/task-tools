import click
import datetime
import os

from task_tools.defaults import TaskToolsDefaults as TTD
from task_tools.manage import TaskManager

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
def cli(ctx: click.Context, task_secrets_file, task_refresh_token, task_list_id, enable_logging):
    """Manage Google Tasks."""
    try:
        ctx.obj = TaskManager(task_secrets_file=task_secrets_file, task_refresh_token=task_refresh_token, task_list_id=task_list_id, enable_logging=enable_logging)
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
        filtered_tasks = [task for task in tasks if task.timing == 0 and task.days_late == 0]
    elif filter == "p1":
        filtered_tasks = [task for task in tasks if task.timing == 1 and task.days_late == 0]
    elif filter == "p2":
        filtered_tasks = [task for task in tasks if task.timing == 2 and task.days_late == 0]
    elif filter == "p3":
        filtered_tasks = [task for task in tasks if task.timing == 3 and task.days_late == 0]
    elif filter == "late":
        filtered_tasks = [task for task in tasks if task.timing >= 0 and task.days_late > 0]
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
def put(ctx: click.Context, name, notes, date):
    """Upload a task."""
    ctx.obj.putTask(name, notes, date)

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
    - P0: ... tasks must be completed same day.\n
    - P1: ... tasks must be completed within a week.\n
    - P2: ... tasks must be completed within a month.\n
    - P3: ... tasks must be completed within 90 days.

    Deletion / failure criteria:\n
    - P[0-3]: [T] ... tasks that have not be completed within the appropriate window.
    """
    with open(os.path.expanduser(out_file), "a") as logfile:
        tasks = ctx.obj.getTasks(end_date, start_date=start_date)
        on_time_tasks = []
        late_tasks = []
        failed_tasks = []
        for task in tasks:
            if task.timing >= 0:
                late = task.days_late > 0
                failed = task.autogen and late
                logfile.write(f"{task.id}|{task.due}|{task.name}|{task.days_late}|{failed}\n")
                if late:
                    if failed:
                        failed_tasks.append((task.days_late, task.id, task.toString(False)))
                    else:
                        late_tasks.append((task.days_late, task.toString(False)))
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
            for _, task in sorted_late_tasks:
                print(f"- {task}")
        else:
            print("NO LATE TASKS")
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
    """
    tasks = ctx.obj.getTasks(end_date, start_date=start_date)
    failed_tasks = []
    for task in tasks:
        if task.timing >= 0:
            failed = task.autogen and task.days_late > 0
            if failed:
                failed_tasks.append((task.days_late, task.id, task.toString(False)))
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

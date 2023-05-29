import click
from datetime import datetime

from task_tools.defaults import TaskToolsDefaults as TTD
from task_tools.manage import TaskManager

@click.group()
@click.pass_context
@click.option(
    "--task-secrets-file",
    "task_secrets_file",
    type=click.Path(exists=True),
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
    "--enable-logging",
    "enable_logging",
    type=bool,
    default=TTD.ENABLE_LOGGING,
    show_default=True,
    help="Whether to enable logging.",
)
def cli(ctx: click.Context, task_secrets_file, task_refresh_token, enable_logging):
    """Manage Google Tasks."""
    ctx.obj = TaskManager(task_secrets_file=task_secrets_file, task_refresh_token=task_refresh_token, enable_logging=enable_logging)

@cli.command()
@click.pass_context
@click.option(
    "--date",
    "date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=datetime.today(),
    show_default=True,
    help="Maximum due date for filtering tasks.",
)
def list(ctx: click.Context, date):
    """List pending tasks."""
    tasks = ctx.obj.getTasks(date)
    for task in tasks:
        print(task)
        print()

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
    default=datetime.today(),
    show_default=True,
    help="Task due date.",
)
def put(ctx: click.Context, name, notes, date):
    """Upload a task."""
    ctx.obj.putTask(name, notes, date)

def main():
    cli()

if __name__ == "__main__":
    main()

# Task-Tools

![workflow](https://github.com/goromal/task-tools/actions/workflows/test.yml/badge.svg)

## Commands

```bash
Usage: task-tools [OPTIONS] COMMAND [ARGS]...

  Manage Google Tasks.

Options:
  --task-secrets-file PATH   Google Tasks client secrets file.  [default:
                             ~/secrets/task/secrets.json]
  --task-refresh-token PATH  Google Tasks refresh file (if it exists).
                             [default:
                             ~/secrets/task/token.json]
  --task-list-id TEXT        UUID of the Task List to query.  [default:
                             MDY2MzkyMzI4NTQ1MTA0NDUwODY6MDow]
  --enable-logging BOOLEAN   Whether to enable logging.  [default: False]
  --help                     Show this message and exit.

Commands:
  delete  Delete a particular task by UUID.
  grader  Generate a CSV report of how consistently tasks have been...
  list    List pending tasks according to a filter ∈ [all, p0, p1, p2,...
  put     Upload a task.
```

### List

```bash
Usage: task-tools list [OPTIONS] FILTER

  List pending tasks according to a filter ∈ [all, p0, p1, p2, p3, late, ranked].

Options:
  --date [%Y-%m-%d]  Maximum due date for filtering tasks.  [default:
                     Today]
  --no-ids           Don't show the UUIDs.
  --help             Show this message and exit.
```

### Put

```bash
Usage: task-tools put [OPTIONS]

  Upload a task.

Options:
  --name TEXT        Name of the task.  [required]
  --notes TEXT       Notes to add to the task description.
  --date [%Y-%m-%d]  Task due date.  [default: Today]
  --help             Show this message and exit.
```

### Delete

```bash
Usage: task-tools delete [OPTIONS] TASK_ID

  Delete a particular task by UUID.

Options:
  --help  Show this message and exit.
```

### Grader

```bash
Usage: task-tools grader [OPTIONS]

  Generate a CSV report of how consistently tasks have been completed within
  the specified window.

  Grading criteria:

  - P0: ... tasks must be completed same day.

  - P1: ... tasks must be completed within a week.

  - P2: ... tasks must be completed within a month.

  - P3: ... tasks must be completed within 90 days.

  Deletion / failure criteria:

  - P[0-3]: [T] ... tasks that have not be completed within the appropriate
  window.

Options:
  --start-date [%Y-%m-%d]  First day of the grading window.  [default:
                           One week ago]
  --end-date [%Y-%m-%d]    Last day of the grading window.  [default:
                           Today]
  -o, --out PATH           CSV file to generate the report in.  [default:
                           ~/data/task_grades/log.csv]
  --dry-run                Do a dry run; no task deletions.
  --help                   Show this message and exit.
```

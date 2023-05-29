# Task-Tools

![workflow](https://github.com/goromal/task-tools/actions/workflows/test.yml/badge.svg)

## Commands

```bash
Usage: task-tools [OPTIONS] COMMAND [ARGS]...

  Manage Google Tasks.

Options:
  --task-secrets-file PATH   Google Tasks client secrets file.  [default:
                             /data/andrew/secrets/task/secrets.json]
  --task-refresh-token PATH  Google Tasks refresh file (if it exists).
                             [default: /data/andrew/secrets/task/token.json]
  --enable-logging BOOLEAN   Whether to enable logging.  [default: False]
  --help                     Show this message and exit.

Commands:
  list  List pending tasks.
  put   Upload a task.
```

### List

```bash
Usage: task-tools list [OPTIONS]

  List pending tasks.

Options:
  --date [%Y-%m-%d]  Maximum due date for filtering tasks.  [default:
                     2023-05-28 22:52:09.460816]
  --help             Show this message and exit.
```

### Put

```bash
Usage: task-tools put [OPTIONS]

  Upload a task.

Options:
  --name TEXT        Name of the task.  [required]
  --notes TEXT       Notes to add to the task description.
  --date [%Y-%m-%d]  Task due date.  [default:
                     2023-05-28 22:53:09.147066]
  --help             Show this message and exit.
```

import os

class TaskToolsDefaults:
    TASK_SECRETS_FILE = os.path.expanduser("~/secrets/task/secrets.json")
    TASK_REFRESH_TOKEN = os.path.expanduser("~/secrets/task/token.json")
    TASK_SCOPE = [
        "https://www.googleapis.com/auth/tasks"
    ]
    ENABLE_LOGGING = False

    @staticmethod
    def getKwargsOrDefault(argname, **kwargs):
        argname_mapping = {
            "task_secrets_file": TaskToolsDefaults.TASK_SECRETS_FILE,
            "task_refresh_token": TaskToolsDefaults.TASK_REFRESH_TOKEN,
            "task_scope": TaskToolsDefaults.TASK_SCOPE,
            "enable_logging": TaskToolsDefaults.ENABLE_LOGGING,
        }
        return kwargs[argname] if (argname in kwargs and kwargs[argname] is not None) else argname_mapping[argname]

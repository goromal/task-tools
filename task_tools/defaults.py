import os

class TaskToolsDefaults:
    TASK_SECRETS_FILE = "~/secrets/google/client_secrets.json"
    TASK_REFRESH_TOKEN = "~/secrets/google/refresh.json"
    TASK_LIST_ID = "MDY2MzkyMzI4NTQ1MTA0NDUwODY6MDow"
    GRADER_OUTPUT_FILE = "~/data/task_grades/log.csv"
    ENABLE_LOGGING = False

    @staticmethod
    def getKwargsOrDefault(argname, **kwargs):
        argname_mapping = {
            "task_secrets_file": TaskToolsDefaults.TASK_SECRETS_FILE,
            "task_refresh_token": TaskToolsDefaults.TASK_REFRESH_TOKEN,
            "enable_logging": TaskToolsDefaults.ENABLE_LOGGING,
            "task_list_id": TaskToolsDefaults.TASK_LIST_ID,
        }
        return kwargs[argname] if (argname in kwargs and kwargs[argname] is not None) else argname_mapping[argname]

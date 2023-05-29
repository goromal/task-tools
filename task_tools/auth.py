import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def getTaskService(task_secrets_file, task_refresh_token, task_scope):
    creds = None
    if os.path.exists(task_refresh_token):
        creds = Credentials.from_authorized_user_file(task_refresh_token, task_scope)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(task_secrets_file, task_scope)
            creds = flow.run_local_server(port=0)
        with open(task_refresh_token, "w") as token:
            token.write(creds.to_json())
    return build("tasks", "v1", credentials=creds)

"""Explicit read-only account checks; no browser or console login side effects."""
import requests
from agent.storage.projects import ProjectConfigurationError


def check_account(kind,token):
    if kind not in {"github","gitlab"}:raise ProjectConfigurationError("Choose GitHub or GitLab.")
    if not token:raise ProjectConfigurationError("Supply an account token or an environment-variable credential.")
    url="https://api.github.com/user" if kind=="github" else "https://gitlab.com/api/v4/user"
    headers={"Authorization":"Bearer "+token} if kind=="github" else {"PRIVATE-TOKEN":token}
    try:
        response=requests.get(url,headers=headers,timeout=20,allow_redirects=False)
        if response.status_code!=200:raise ValueError("not accepted")
        data=response.json();name=data.get("login") if kind=="github" else data.get("username")
        if not isinstance(name,str) or not name:raise ValueError("missing account")
        return {"account":name[:100]}
    except (requests.RequestException,ValueError):
        raise ProjectConfigurationError("Account verification failed. Check the token, account permissions and connection.") from None

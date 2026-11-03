"""Bounded Git transport; callers control clone/sync and reviewed publication."""
import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
from agent.storage.projects import ProjectConfigurationError,validate_local_folder


def repository_url(value):
    if not isinstance(value,str) or len(value)>1000:raise ProjectConfigurationError("Enter a repository HTTPS URL.")
    parsed=urlsplit(value.strip())
    if parsed.scheme!="https" or parsed.hostname not in {"github.com","gitlab.com"} or parsed.port not in {None,443} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProjectConfigurationError("Use a GitHub.com or GitLab.com HTTPS repository URL without credentials.")
    path=parsed.path.strip("/").removesuffix(".git")
    parts=path.split("/")
    if len(parts)<2 or (parsed.hostname=="github.com" and len(parts)!=2) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+",part) or part in {".",".."} for part in parts):
        raise ProjectConfigurationError("Use a repository URL such as https://github.com/owner/repository.")
    return "https://"+parsed.hostname+"/"+path+".git"


def git_failure_message(stderr,*,authenticated=False,remote=False):
    """Classify a failed operation without exposing remote text or credentials."""
    text=stderr.casefold() if isinstance(stderr,str) else ""
    if any(term in text for term in ("could not resolve host","failed to connect","connection timed out","ssl certificate problem")):
        return "Git could not reach the repository securely. Check network, proxy and certificate settings; no push was performed."
    access_errors=("repository not found","authentication failed","could not read username",
                   "http basic: access denied","error: 401","error: 403","access denied","permission denied")
    if remote and any(term in text for term in access_errors):
        if not authenticated:
            return ("Repository access was denied or the URL was not found. Check the URL. "
                    "For a private repository, add a GitHub/GitLab account in Settings → Connections, "
                    "then select it under Repository access. Public repository uses no account. No push was performed.")
        return ("Git rejected the selected account or its repository permission. Check the token, repository access "
                "and any required organization authorization, then use Test connection in Settings → Connections. "
                "No push was performed.")
    if "not a git repository" in text:
        return "Choose an existing Git checkout folder, or choose Clone repository with a new destination."
    return "Git could not complete this operation. Check repository access, branch state and network. No push was performed."


def git_command(arguments,*,cwd=None,token="",host="",timeout=180,index_file=None,raw=False):
    executable=shutil.which("git")
    if not executable:raise ProjectConfigurationError("Install Git on the agent server before cloning or syncing.")
    env=os.environ.copy()
    for name in list(env):
        if name.startswith("GIT_CONFIG_") or name in {"GIT_DIR","GIT_WORK_TREE","GIT_INDEX_FILE","GIT_OBJECT_DIRECTORY","GIT_ALTERNATE_OBJECT_DIRECTORIES","GIT_ASKPASS","SSH_ASKPASS","GIT_COMMON_DIR","GIT_REPLACE_REF_BASE"} or name.startswith(("GIT_AUTHOR_","GIT_COMMITTER_")):env.pop(name,None)
    env.update({"GIT_TERMINAL_PROMPT":"0","GCM_INTERACTIVE":"never","GIT_LFS_SKIP_SMUDGE":"1","GIT_CONFIG_GLOBAL":os.devnull,"GIT_CONFIG_NOSYSTEM":"1"})
    env["GIT_NO_REPLACE_OBJECTS"]="1"
    env["GIT_OPTIONAL_LOCKS"]="0"
    if index_file is not None:
        env["GIT_INDEX_FILE"]=str(Path(index_file).resolve())
    if host:
        env.update({"GIT_CONFIG_COUNT":"1","GIT_CONFIG_KEY_0":"http.https://"+host+"/.extraHeader","GIT_CONFIG_VALUE_0":""})
        if token:
            encoded=base64.b64encode(("oauth2:"+token).encode()).decode()
            env.update({"GIT_CONFIG_COUNT":"2","GIT_CONFIG_KEY_1":"http.https://"+host+"/.extraHeader",
                        "GIT_CONFIG_VALUE_1":"Authorization: Basic "+encoded})
    with tempfile.TemporaryDirectory(prefix="jeshla-git-hooks-") as hooks:
        command=[executable,"-c","credential.helper=","-c","http.extraHeader=","-c","http.followRedirects=false",
                 "-c","core.hooksPath="+hooks,"-c","submodule.recurse=false","-c","maintenance.auto=false","-c","gc.auto=0","-c","core.fsmonitor=false",*arguments]
        try:
            result=subprocess.run(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,timeout=timeout,encoding="utf-8",errors="replace",
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except (OSError,subprocess.TimeoutExpired):
            message=("Push was not confirmed. Inspect the remote before retrying." if arguments and arguments[0]=="push" else
                     "Git could not finish within the time limit. Check the working folder before retrying.")
            raise ProjectConfigurationError(message) from None
    if result.returncode:
        # Remote error text can echo credentials, URLs or untrusted instructions.
        message=git_failure_message(result.stderr,authenticated=bool(token),remote=bool(host))
        if arguments and arguments[0]=="push":
            message=message.replace("No push was performed.","").replace("no push was performed.","").strip(" ;")
            message+=" Push was not confirmed; inspect the remote before retrying."
        raise ProjectConfigurationError(message)
    return result.stdout if raw else result.stdout.strip()


def clone_repository(url,destination,*,token=""):
    url=repository_url(url)
    target=Path(destination.strip()).expanduser() if isinstance(destination,str) else Path("")
    if not target.is_absolute() or target.exists() or target.is_symlink():
        raise ProjectConfigurationError("Choose a new absolute destination folder; existing folders are never overwritten.")
    parent=Path(validate_local_folder(str(target.parent)));target=parent/target.name
    git_command(["clone","--",url,str(target)],token=token,host=urlsplit(url).hostname)
    observed=git_command(["remote","get-url","origin"],cwd=target,timeout=15)
    if repository_url(observed)!=url:raise ProjectConfigurationError("The cloned repository identity did not match.")
    return {"root":str(target.resolve()),"remote_url":url,"source":"git"}


def synchronize_repository(project,*,token=""):
    url=repository_url(project.get("remote_url",""))
    root=validate_local_folder(project["root"])
    if git_command(["rev-parse","--show-toplevel"],cwd=root,timeout=15).casefold()!=str(Path(root)).replace("\\","/").casefold():
        # Git may use native backslashes on some systems.
        observed=git_command(["rev-parse","--show-toplevel"],cwd=root,timeout=15)
        if Path(observed).resolve()!=Path(root).resolve():raise ProjectConfigurationError("The working folder is not this repository root.")
    observed=git_command(["remote","get-url","origin"],cwd=root,timeout=15)
    if repository_url(observed)!=url:raise ProjectConfigurationError("The repository origin changed. Review its project registration.")
    if git_command(["status","--porcelain"],cwd=root,timeout=20):
        raise ProjectConfigurationError("Commit or set aside local changes before syncing this project.")
    output=git_command(["pull","--ff-only","--no-recurse-submodules"],cwd=root,token=token,host=urlsplit(url).hostname)
    # Never display arbitrary remote text as a success receipt.
    return {"synced":True,"mode":"fast-forward only","project_id":project["id"]}

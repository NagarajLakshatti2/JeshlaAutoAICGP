"""Bounded clone and fast-forward synchronization; never push or execute project code."""
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


def git_command(arguments,*,cwd=None,token="",host="",timeout=180):
    executable=shutil.which("git")
    if not executable:raise ProjectConfigurationError("Install Git on the agent server before cloning or syncing.")
    env=os.environ.copy()
    for name in list(env):
        if name.startswith("GIT_CONFIG_") or name in {"GIT_DIR","GIT_WORK_TREE","GIT_INDEX_FILE","GIT_OBJECT_DIRECTORY","GIT_ALTERNATE_OBJECT_DIRECTORIES","GIT_ASKPASS","SSH_ASKPASS"}:env.pop(name,None)
    env.update({"GIT_TERMINAL_PROMPT":"0","GCM_INTERACTIVE":"never","GIT_LFS_SKIP_SMUDGE":"1","GIT_CONFIG_GLOBAL":os.devnull,"GIT_CONFIG_NOSYSTEM":"1"})
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
            raise ProjectConfigurationError("Git could not finish within the time limit. Check the working folder before retrying.") from None
    if result.returncode:
        # Remote error text can echo credentials, URLs or untrusted instructions.
        raise ProjectConfigurationError("Git could not complete this operation. Check repository access, branch state and network. No push was performed.")
    return result.stdout.strip()


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

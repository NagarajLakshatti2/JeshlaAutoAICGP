"""Exact-file commits and separately reviewed fast-forward pushes."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from integrations.git.repositories import git_command,repository_url
from agent.storage.projects import ProjectConfigurationError

LIMIT=120000


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def safe_path(root,name):
    from agent.tools.project_tools import SKIP_DIRS,SKIP_FILES,TEXT_EXTENSIONS
    if not isinstance(name,str) or not name or len(name)>300 or any(c in name for c in "\\:\x00\r\n"):
        raise ProjectConfigurationError("Select a normal relative source-file path.")
    path=Path(name)
    denied=SKIP_DIRS|{"outputs","test-output","logs",".devin",".ssh"}
    if path.is_absolute() or any(part in {".",".."} or part.startswith("-") or part in denied for part in path.parts):
        raise ProjectConfigurationError("Excluded Git path.")
    if path.name in SKIP_FILES or path.name.startswith(".env") or path.suffix.lower() not in TEXT_EXTENSIONS|{".gitignore"}:
        if path.name not in {".gitignore","LICENSE","Dockerfile"}:
            raise ProjectConfigurationError("Only reviewable source/text files can be published here.")
    target=Path(root)/path
    if any(p.is_symlink() for p in [target,*list(target.parents)[:len(path.parts)-1]]):
        raise ProjectConfigurationError("Symlink files/folders are excluded from Git publication.")
    if not target.resolve().is_relative_to(Path(root).resolve()):
        raise ProjectConfigurationError("Git paths must remain inside this project.")
    return target


def check_text(text):
    if len(text)>LIMIT:
        raise ProjectConfigurationError("The Git review is too large. Select a smaller change.")
    if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}",text):
        raise ProjectConfigurationError("Possible credential material found. Remove it before reviewing publication.")


def local_state(root):
    root=Path(root).resolve()
    if not (root/".git").is_dir() or (root/".git").is_symlink():
        raise ProjectConfigurationError("This workflow requires a normal local Git checkout.")
    if Path(git_command(["rev-parse","--show-toplevel"],cwd=root)).resolve()!=root:
        raise ProjectConfigurationError("Choose the Git repository root.")
    if any((root/".git"/name).exists() for name in ("MERGE_HEAD","CHERRY_PICK_HEAD","rebase-merge","rebase-apply")):
        raise ProjectConfigurationError("Finish the existing merge/rebase operation first.")
    branch=git_command(["symbolic-ref","--quiet","--short","HEAD"],cwd=root)
    git_command(["check-ref-format","--branch",branch],cwd=root)
    head=git_command(["rev-parse","HEAD"],cwd=root)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",head):
        raise ProjectConfigurationError("An existing initial commit is required.")
    index=root/".git/index"
    if index.is_symlink():raise ProjectConfigurationError("A symlink Git index is unsupported.")
    return {"head":head,"branch":branch,"remote_url":repository_url(git_command(["remote","get-url","origin"],cwd=root)),
            "index":hashlib.sha256(index.read_bytes()).hexdigest() if index.exists() else "missing"}


def project_data(project):
    return {key:project.get(key,"") for key in ("id","root","remote_url","account_id")}


def changes(project):
    root=project["root"];state=local_state(root)
    names=git_command(["ls-files","--modified","--deleted","--others","--exclude-standard","-z"],cwd=root,raw=True)
    files=[];excluded=0
    for name in sorted(set(x for x in names.split("\0") if x)):
        try:safe_path(root,name)
        except ProjectConfigurationError:excluded+=1;continue
        files.append(name)
    return {"branch":state["branch"],"files":files[:100],"excluded":excluded,"truncated":len(files)>100}


def file_snapshot(root,paths):
    files=[];patches=[]
    for name in paths:
        path=safe_path(root,name)
        old=""
        tree=git_command(["ls-tree","HEAD","--",name],cwd=root)
        if tree:
            oid=tree.split()[2]
            if int(git_command(["cat-file","-s",oid],cwd=root))>LIMIT:
                raise ProjectConfigurationError("The original file is too large for an exact review.")
            old=git_command(["show","HEAD:"+name],cwd=root,raw=True)
        if path.exists():
            if not path.is_file() or path.stat().st_size>LIMIT:
                raise ProjectConfigurationError("Selected file is not a bounded text file.")
            data=path.read_bytes()
            try:new=data.decode("utf-8")
            except UnicodeError:raise ProjectConfigurationError("Selected file must be UTF-8 text.") from None
            if "\0" in new:raise ProjectConfigurationError("Binary files are not supported.")
            sha=hashlib.sha256(data).hexdigest()
        else:new="";sha="deleted"
        mode=tree.split(" ",1)[0] if tree else "100644"
        if mode not in {"100644","100755"}:raise ProjectConfigurationError("Only regular files can be committed.")
        patch="".join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile="a/"+name,tofile="b/"+name))
        patches.append(patch);files.append({"path":name,"sha256":sha,"mode":mode})
    text="\n".join(patches);check_text(text)
    return files,text


def version(root,action,review):
    state=local_state(root)
    files=file_snapshot(root,review.get("paths",[]))[0] if action=="git_commit" else []
    return digest({"state":state,"files":files})


def prepare_commit(project,paths,message,author_name,author_email):
    root=project["root"];state=local_state(root)
    if state["remote_url"]!=repository_url(project["remote_url"]):raise ProjectConfigurationError("Repository origin changed.")
    if not isinstance(paths,list) or not 1<=len(paths)<=8 or len(set(paths))!=len(paths):
        raise ProjectConfigurationError("Select 1–8 distinct source files.")
    if git_command(["diff","--cached","--name-only","--no-ext-diff"],cwd=root):
        raise ProjectConfigurationError("Existing staged changes must be handled before this workflow.")
    if not isinstance(message,str) or not message.strip() or len(message)>1000 or "\0" in message:
        raise ProjectConfigurationError("Enter a commit message of 1–1000 characters.")
    if not isinstance(author_name,str) or not 1<=len(author_name.strip())<=100 or any(c in author_name for c in "<>\r\n\0"):
        raise ProjectConfigurationError("Enter the commit author's name.")
    if not isinstance(author_email,str) or not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+",author_email):
        raise ProjectConfigurationError("Enter the commit author's email.")
    files,patch=file_snapshot(root,paths)
    if not patch:raise ProjectConfigurationError("No selected changes to commit.")
    review={"kind":"git_commit","project":project_data(project),"state":state,"paths":paths,"files":files,
            "message":message,"author_name":author_name,"author_email":author_email,"diff":patch}
    review["version"]=version(root,"git_commit",review)
    return review


def commit(project,review):
    if review!=prepare_commit(project,review.get("paths"),review.get("message"),review.get("author_name"),review.get("author_email")):
        raise ProjectConfigurationError("Commit review changed. Prepare a fresh approval.")
    root=Path(project["root"]);lock=root/".git/index.lock";owned=False
    try:
        try:handle=lock.open("xb");owned=True
        except FileExistsError:raise ProjectConfigurationError("Git index is busy. Prepare a new review after it finishes.") from None
        handle.close()
        with tempfile.TemporaryDirectory(prefix="jeshla-git-index-") as folder:
            index=Path(folder)/"index"
            git_command(["read-tree",review["state"]["head"]],cwd=root,index_file=index)
            for item in review["files"]:
                name=item["path"]
                if item["sha256"]=="deleted":
                    git_command(["update-index","--force-remove","--",name],cwd=root,index_file=index)
                    continue
                data=safe_path(root,name).read_bytes()
                if hashlib.sha256(data).hexdigest()!=item["sha256"]:raise ProjectConfigurationError("Selected file changed.")
                blob=git_command(["hash-object","-w","--no-filters","--",name],cwd=root)
                algorithm="sha1" if len(review["state"]["head"])==40 else "sha256"
                expected=hashlib.new(algorithm,b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
                if blob!=expected:raise ProjectConfigurationError("Selected content changed during commit preparation.")
                git_command(["update-index","--add","--cacheinfo",item["mode"]+","+blob+","+name],cwd=root,index_file=index)
            tree=git_command(["write-tree"],cwd=root,index_file=index)
            new=git_command(["-c","user.name="+review["author_name"],"-c","user.email="+review["author_email"],
                             "commit-tree",tree,"-p",review["state"]["head"],"-m",review["message"]],cwd=root,index_file=index)
            if version(root,"git_commit",review)!=review["version"]:raise ProjectConfigurationError("Repository changed before commit.")
            with lock.open("wb") as output:output.write(index.read_bytes());output.flush();os.fsync(output.fileno())
            git_command(["update-ref","refs/heads/"+review["state"]["branch"],new,review["state"]["head"]],cwd=root)
            os.replace(lock,root/".git/index");owned=False
        return {"committed":True,"commit":new,"branch":review["state"]["branch"],"files":review["paths"],"pushed":False,
                "tests":"not run; a separate action is required"}
    finally:
        if owned:lock.unlink(missing_ok=True)


def prepare_push(project,token):
    if not project.get("account_id") or not token:
        raise ProjectConfigurationError("Select a GitHub/GitLab account with repository write access in Project details before push.")
    root=project["root"];state=local_state(root);url=repository_url(project["remote_url"])
    if state["remote_url"]!=url:raise ProjectConfigurationError("Repository origin changed.")
    if url.startswith("ssh:"):
        raise ProjectConfigurationError("SSH publication requires a separate reviewed workflow.")
    branch=state["branch"]
    remote=git_command(["ls-remote","--refs",url,"refs/heads/"+branch],host=url.split("/")[2],token=token,cwd=root)
    parts=remote.split()
    if len(parts)!=2 or parts[1]!="refs/heads/"+branch or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",parts[0]):
        raise ProjectConfigurationError("This workflow requires an existing remote branch with the same name.")
    base=parts[0]
    if base==state["head"]:raise ProjectConfigurationError("This branch is already at the remote commit.")
    git_command(["merge-base","--is-ancestor",base,state["head"]],cwd=root)
    span=base+".."+state["head"]
    commits=git_command(["rev-list","--reverse","--max-count=21",span],cwd=root).splitlines()
    if not 1<=len(commits)<=20:raise ProjectConfigurationError("Review at most 20 pending commits at a time.")
    if git_command(["rev-list","--min-parents=2",span],cwd=root):
        raise ProjectConfigurationError("Merge commits require a separate reviewed publication workflow.")
    names=set();objects=set(commits);total_bytes=0
    for oid in commits:
        raw=git_command(["diff-tree","--no-commit-id","--raw","--no-renames","-r","-z",oid],cwd=root,raw=True).split("\0")
        entries=[entry for entry in raw if entry]
        if len(entries)>200 or len(entries)%2:
            raise ProjectConfigurationError("Too many changed files for one push review.")
        for metadata,name in zip(entries[::2],entries[1::2]):
            fields=metadata.split()
            if len(fields)!=5:raise ProjectConfigurationError("Unsupported Git change metadata.")
            names.add(name)
            objects.update(value for value in fields[2:4] if set(value)!={"0"})
    if len(names)>100 or len(objects)>120:
        raise ProjectConfigurationError("Too many changed objects for one push review.")
    for oid in objects:
        total_bytes+=int(git_command(["cat-file","-s",oid],cwd=root))
        if total_bytes>LIMIT:raise ProjectConfigurationError("Pending commits are too large for one exact push review.")
    for name in names:safe_path(root,name)
    patch=git_command(["log","--format=medium","--patch","--no-ext-diff","--no-textconv",span,"--"],cwd=root,raw=True)
    check_text(patch)
    if "GIT binary patch" in patch or "Binary files " in patch:raise ProjectConfigurationError("Binary changes need a separate publication review.")
    review={"kind":"git_push","project":project_data(project),"state":state,"remote_tip":base,"commits":commits,
            "paths":sorted(names),"diff":patch,"target":"refs/heads/"+branch}
    review["version"]=version(root,"git_push",review)
    return review


def push(project,review,token):
    if review!=prepare_push(project,token):raise ProjectConfigurationError("Push review changed. Prepare a fresh approval.")
    state=review["state"];url=repository_url(project["remote_url"])
    git_command(["push","--porcelain",url,state["head"]+":"+review["target"]],cwd=project["root"],host=url.split("/")[2],token=token)
    observed=git_command(["ls-remote","--refs",url,review["target"]],cwd=project["root"],host=url.split("/")[2],token=token).split()
    if not observed or observed[0]!=state["head"]:
        raise ProjectConfigurationError("Push confirmation is uncertain. Inspect the remote before another attempt.")
    return {"pushed":True,"commit":state["head"],"branch":state["branch"],"remote_url":url,"commits":review["commits"]}


def prepare_branch(project, name):
    state = local_state(project["root"])
    if state["remote_url"] != repository_url(project["remote_url"]):
        raise ProjectConfigurationError("Repository origin changed.")
    if not isinstance(name, str) or not name or name.startswith("-") or len(name) > 200:
        raise ProjectConfigurationError("Enter a valid branch name.")
    git_command(["check-ref-format", "refs/heads/" + name], cwd=project["root"])
    refs = git_command(["for-each-ref", "--format=%(refname)", "refs/heads/"], cwd=project["root"])
    if "refs/heads/" + name in refs.splitlines():
        raise ProjectConfigurationError("That branch already exists.")
    review = {"kind": "git_branch", "project": project_data(project), "state": state,
              "name": name, "diff": "Create branch " + name + " at " + state["head"]}
    review["version"] = version(project["root"], "git_branch", review)
    return review


def create_branch(project, review):
    if review != prepare_branch(project, review.get("name")):
        raise ProjectConfigurationError("Branch review changed. Prepare a fresh approval.")
    git_command(["update-ref", "refs/heads/" + review["name"], review["state"]["head"], ""],
                cwd=project["root"])
    return {"created": True, "branch": review["name"], "commit": review["state"]["head"],
            "checked_out": False}


def prepare_pull_request(project, base, head, title, body):
    state = local_state(project["root"])
    if state["remote_url"] != repository_url(project["remote_url"]):
        raise ProjectConfigurationError("Repository origin changed.")
    for name in (base, head):
        if not isinstance(name, str) or not name or len(name) > 200:
            raise ProjectConfigurationError("Choose explicit local base and head branches.")
        git_command(["check-ref-format", "refs/heads/" + name], cwd=project["root"])
    if base == head:
        raise ProjectConfigurationError("Choose different base and head branches.")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ProjectConfigurationError("Enter a PR title of 1–200 characters.")
    if not isinstance(body, str) or len(body) > 12000:
        raise ProjectConfigurationError("Keep the PR body within 12000 characters.")
    check_text(title + body)
    base_sha = git_command(["rev-parse", "--verify", "refs/heads/" + base], cwd=project["root"])
    head_sha = git_command(["rev-parse", "--verify", "refs/heads/" + head], cwd=project["root"])
    span = base_sha + "..." + head_sha
    names = git_command(["diff", "--name-only", "-z", span], cwd=project["root"], raw=True)
    for name in filter(None, names.split("\0")):
        safe_path(project["root"], name)
    diff = git_command(["diff", "--no-ext-diff", "--no-textconv", span], cwd=project["root"], raw=True)
    check_text(diff)
    if not diff:
        raise ProjectConfigurationError("The selected branches have no PR changes.")
    return {"title": title.strip(), "body": body, "base": base, "head": head,
            "base_commit": base_sha, "head_commit": head_sha, "diff": diff,
            "remote_url": state["remote_url"]}

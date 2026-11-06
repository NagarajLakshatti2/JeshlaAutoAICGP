"""Streamlit adapter using the existing graph, chats, memory and providers."""
import os
from pathlib import Path
from agent.storage.chats import ChatCatalog,validate_chat_command

from agent.config.paths import DATA_ROOT as ROOT

from agent.runtime.workspace import WorkspaceSupport

class BrowserBackend(WorkspaceSupport):
    def __init__(self):
        from agent.langgraph.langgraph_agent import graph,session_config,LLM_PROVIDER
        self.graph,self.session_config,self.provider=graph,session_config,LLM_PROVIDER
        self.user=os.getenv("AI_MEMORY_USER_ID","local-user")
        self.space=os.getenv("AI_MEMORY_NAMESPACE","project")
        self.catalog=ChatCatalog(ROOT/"outputs/memory/chats.sqlite3",self.user,self.space)
        self.catalog.register("default")

    def project_store(self):
        from agent.storage.projects import ProjectCatalog
        return ProjectCatalog(ROOT/"outputs/memory/projects.sqlite3",self.user,getattr(self,"base_space",self.space))

    def add_project(self,name,folder):return self.project_store().add_local(name,folder)

    def for_project(self,project_id):
        import copy
        if not project_id:
            if not getattr(self,"project_id",None):return self
            backend=copy.copy(self);backend.space=self.base_space
            backend.project=None;backend.project_id=None
            backend.catalog=ChatCatalog(ROOT/"outputs/memory/chats.sqlite3",self.user,backend.space)
            return backend
        from agent.storage.projects import ProjectConfigurationError,project_namespace
        project=self.project_store().get(project_id)
        if project is None:raise ProjectConfigurationError("Project not found in your workspace.")
        backend=copy.copy(self)
        backend.base_space=getattr(self,"base_space",self.space)
        backend.project=project;backend.project_id=project["id"]
        backend.space=project_namespace(backend.base_space,project["id"])
        backend.catalog=ChatCatalog(ROOT/"outputs/memory/chats.sqlite3",self.user,backend.space)
        return backend

    def request_scope(self):
        if not getattr(self,"project_id",None):return None
        from agent.storage.projects import ProjectConfigurationError
        from agent.runtime.project_scope import validate_request_scope
        current=self.project_store().get(self.project_id)
        if current is None or current["root"]!=self.project["root"]:
            raise ProjectConfigurationError("Project configuration changed. Select it again before continuing.")
        scope={"memory_user_id":self.user,"memory_namespace":self.space,
               "project_id":self.project_id,"bound_project_root":current["root"]}
        jira_binding=self.project_store().bindings(self.project_id).get("jira_mcp")
        scope["jira_scope"]=None
        if jira_binding:
            profile=self.connection_store().get(jira_binding.get("connection_id",""))
            if not profile or profile.get("kind")!="jira_mcp":
                raise ProjectConfigurationError("The Jira profile assigned to this project is unavailable. Review Project details.")
            scope["jira_scope"]={
                "connection_id":profile["id"],
                "site_url":profile.get("details",{}).get("jira_site_url",""),
                "project_key":jira_binding.get("options",{}).get("project_key",""),
                "connection_namespace":getattr(self,"base_space",self.space),
                "connected":profile.get("status")=="verified",
            }
        validate_request_scope(scope)
        return scope

    def project_documents(self):
        from rag.project_retrieval import collection_for_state
        return collection_for_state(self.request_scope() or {}, ROOT)

    def search_project_documents(self, query):
        from rag.project_retrieval import search_project_documents
        return search_project_documents(query, state=self.request_scope() or {}, application_root=ROOT)

    def list_chats(self):return self.catalog.list()
    def list_chat_page(self,offset=0):return self.catalog.list(limit=31,offset=offset)
    def create_chat(self,title):return self.catalog.create(title)
    def get_chat(self,session):return self.catalog.get(session)
    def turns(self,session):return self.catalog.transcript(session)

    def search_chats(self,query,session=None):
        """Search only this backend user/memory space; no model request."""
        return self.catalog.search_turns(query,session=session,limit=10)

    def provider_info(self,provider=None):
        """Return allowlisted configuration metadata, never credentials or health claims."""
        from agent.providers import text
        from agent.providers.gemini import KEY_NAMES
        provider=provider or self.provider
        model={"ollama":text.OLLAMA_MODEL,"openrouter":text.OPENROUTER_MODEL,
               "groq":os.getenv("GROQ_MODEL",""),"gemini":os.getenv("GEMINI_MODEL","")}.get(provider,"")
        names=KEY_NAMES if provider=="gemini" else (provider.upper()+"_API_KEY",)
        key_present=None if provider=="ollama" else any(bool(os.getenv(name,"").strip()) for name in names)
        return {"provider":provider,"model":model.strip(),"key_present":key_present,
                "local":provider=="ollama","supported":provider in {"ollama","openrouter","groq","gemini"}}

    def edit_memory(self,session,operation,key,value=""):
        """Use the normal archived memory-command path, with exact input validation."""
        import re
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}",key):
            raise ValueError("Use a fact name of 1–64 letters, numbers, dots, underscores or hyphens.")
        if operation=="save":
            if not isinstance(value,str) or not value.strip() or len(value.strip())>2000:
                raise ValueError("Enter a fact of 1–2,000 characters.")
            command="REMEMBER "+key+" = "+value.strip()
        elif operation=="forget":command="FORGET "+key
        else:raise ValueError("Choose save or forget.")
        return self.submit(session,command)

    def save_model_settings(self,provider,model):
        from agent.config.ui_settings import save_model_settings
        return save_model_settings(ROOT/".env",provider,model)

    def generated_files(self,session):
        from agent.actions.downloads import list_downloadable_files
        return list_downloadable_files(self.actions(),self.user,self.space,session)

    def generated_file(self,session,token):
        from agent.actions.downloads import read_downloadable_file
        return read_downloadable_file(self.actions(),self.user,self.space,session,token)

    def generated_zip_file(self,session,token):
        from agent.actions.downloads import zip_snapshot
        return zip_snapshot(self.generated_file(session,token))

    def memory(self):
        from agent.langgraph.langgraph_agent import load_long_term_memory_node
        return load_long_term_memory_node(self.request_scope() or {})["memory_context"]

    def memory_records(self):
        """Read structured facts in this backend scope without model calls."""
        from agent.memory.long_term_memory import LongTermMemory
        with LongTermMemory(ROOT/"outputs/memory/long_term_memory.sqlite3") as store:
            return store.list(self.user,self.space)

    def submit_selected(self,session,question,provider,agent_mode="autogen"):
        """Apply this browser choice only for the lifetime of one request."""
        from agent.runtime.chat_shortcuts import is_shortcut
        if is_shortcut(question):return self.submit(session,question)
        from agent.providers.selection import provider_selection
        from agent.providers.errors import ProviderError
        info=self.provider_info(provider)
        if not info["supported"] or not info["model"] or (not info["local"] and not info["key_present"]):
            raise ProviderError(provider,"CONFIGURATION","Configure the selected provider key and default model locally before using it.",attempts=0)
        if agent_mode not in {"autogen","langgraph"}:raise ValueError("Select AutoGen or LangGraph agent mode.")
        from integrations.autogen.selection import agent_mode_selection
        with provider_selection(provider),agent_mode_selection(agent_mode):return self.submit(session,question)

    def submit(self,session,question):
        if not self.catalog.get(session):raise ValueError("Chat not found.")
        if not question.strip():raise ValueError("Enter a message first.")
        normalized,error=validate_chat_command(question)
        if error:return {"answer":error,"notices":[]}
        if normalized.upper().startswith(("NEW CHAT","NEW SESSION","OPEN CHAT","SESSION ")) or normalized.upper()=="LIST CHATS":
            return {"answer":"Use the sidebar to create or open a chat. Your current chat has not changed.","notices":[]}
        from agent.runtime.git_workspace import git_status_reply
        from agent.runtime.chat_shortcuts import is_shortcut
        shortcut=is_shortcut(question)
        git_status=None if shortcut else git_status_reply(self,session,question)
        if git_status is not None:
            self.catalog.append(session,question,git_status["answer"])
            return git_status
        from agent.policies.routing import git_write_mode
        git_mode=None if shortcut else git_write_mode(question)
        if git_mode:
            if not getattr(self,"project_id",None) or getattr(self,"project",{}).get("source")!="git":
                return {"answer":"Select a saved Git project, then review its changes before committing or pushing.","notices":[]}
            answer="Git commit/push requires a review of selected files or pending commits, followed by a separate exact-action approval. Use the Git review panel. No commit or push has executed."
            self.catalog.append(session,question,answer)
            return {"answer":answer,"notices":[],"task_status":"awaiting_input","execution_outcome":"awaiting_input","open_git_review":self.project_id,"git_review_action":git_mode}
        from agent.runtime.turns import run_turn
        from agent.runtime.context import local_action_handler
        queued=[]
        scope=self.request_scope()
        def browser_approval(action,arguments):
            from agent.actions.receipts import ActionPending
            if scope and str(Path(arguments["project_root"]).resolve())!=scope["bound_project_root"]:
                from agent.actions.receipts import ActionBlocked
                raise ActionBlocked("The proposed action does not belong to this selected project.")
            token=self.actions().propose(self.user,self.space,session,action,arguments)
            queued.append(token)
            raise ActionPending("Action is waiting for your browser approval. Review its exact project root and arguments below; no local action has executed.")
        config=self.session_config(session,self.user,self.space)
        with local_action_handler(browser_approval):
            result=run_turn(self.graph,config,self.catalog,session,question,ROOT,**({"request_scope":scope} if scope else {}))
        if queued:
            result["notices"].append("Review the pending action below. Approving executes only that stored action; send another message to continue any remaining work.")
        return result

    def actions(self):
        from agent.actions.browser import BrowserActions
        from agent.runtime.git_workspace import WorkspaceActionTools
        return BrowserActions(ROOT/"outputs/local_actions.sqlite3",tools_factory=lambda root:WorkspaceActionTools(self,root))

    def pending_actions(self,session):
        return self.actions().pending(self.user,self.space,session)

    def expired_file_reviews(self,session):
        if not self.catalog.get(session):return []
        rows=self.actions().expired_file_reviews(self.user,self.space,session)
        if getattr(self,"project_id",None):
            root=self.request_scope()["bound_project_root"]
            rows=[item for item in rows if str(Path(item["project_root"]).resolve())==root]
        return rows

    def refresh_file_review(self,session,token):
        from agent.actions.receipts import ActionBlocked
        if not self.catalog.get(session):raise ActionBlocked("Chat not found.")
        actions=self.actions();row=actions._row(self.user,self.space,session,token)
        if getattr(self,"project_id",None):
            import json
            if str(Path(json.loads(row["proposal"])["project_root"]).resolve())!=self.request_scope()["bound_project_root"]:
                raise ActionBlocked("This review belongs to a different project folder.")
        return actions.refresh_file_review(self.user,self.space,session,token)

    def execution_result(self,session,token):
        """Read an owned supported action receipt without executing or reopening artifacts."""
        import json,re
        from agent.actions.receipts import ActionBlocked
        from agent.interfaces.execution_results import RESULT_ACTIONS
        if not isinstance(token,str) or not re.fullmatch(r"[0-9a-f]{32}",token) or not self.catalog.get(session):return None
        actions=self.actions()
        try:row=actions._row(self.user,self.space,session,token)
        except ActionBlocked:return None
        proposal=json.loads(row["proposal"])
        if proposal["action"] not in RESULT_ACTIONS:return None
        if getattr(self,"project_id",None):
            scope=self.request_scope()
            if Path(proposal["project_root"]).resolve()!=Path(scope["bound_project_root"]):return None
        receipt=actions.receipts.get(token)
        if not receipt or receipt["status"] not in {"completed","uncertain","running"} or not receipt["result"]:return None
        from agent.actions.receipts import canonical
        import hashlib
        fingerprint=hashlib.sha256(canonical(proposal).encode()).hexdigest()
        if receipt["fingerprint"]!=fingerprint:return None
        result=json.loads(receipt["result"])
        if not isinstance(result,dict):return None
        if receipt["status"]=="completed" and row["status"]!="completed":return None
        return {"receipt_id":token,"receipt_status":receipt["status"],"action":proposal["action"],
                "project_root":proposal["project_root"],"arguments":proposal["arguments"],"result":result}

    def decide_action(self,session,token,approve):
        if type(approve) is not bool:raise ValueError("Choose approve or decline explicitly.")
        if not self.catalog.get(session):raise ValueError("Chat not found.")
        from agent.runtime.turns import process_turn_lock,session_turn_lock
        config=self.session_config(session,self.user,self.space)
        with process_turn_lock,session_turn_lock(ROOT,config):
            actions=self.actions()
            if not approve:
                actions.decline(self.user,self.space,session,token)
                return {"answer":"Action declined. No local action executed.","notices":[]}
            if getattr(self,"project_id",None):
                from agent.actions.receipts import ActionBlocked
                row=actions._row(self.user,self.space,session,token)
                import json
                proposal=json.loads(row["proposal"])
                scope=self.request_scope()
                if str(Path(proposal["project_root"]).resolve())!=scope["bound_project_root"]:
                    raise ActionBlocked("This approval belongs to a different project folder.")
            result,replayed=actions.execute(self.user,self.space,session,token)
            import json
            answer="Stored action returned. Receipt: "+token+"\n\n"+json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)
            fence="\x60"*3
            if result.get("committed") is True:
                answer=("Commit created locally: "+result["commit"]+" on "+result["branch"]+
                        ".\nSelected files: "+", ".join(result["files"])+
                        ".\nPush has not run. Request a push review for a separate approval.\nReceipt: "+token+
                        "\n\n"+fence+"json\n"+json.dumps(result,ensure_ascii=False,indent=2)+"\n"+fence)
            elif result.get("pushed") is True:
                answer=("Push confirmed: "+result["commit"]+" on "+result["branch"]+
                        ".\nRemote: "+result["remote_url"]+"\nReceipt: "+token+
                        "\n\n"+fence+"json\n"+json.dumps(result,ensure_ascii=False,indent=2)+"\n"+fence)
            notices=[]
            if not replayed:
                try:
                    question="Approved exact local action "+token
                    self.catalog.append(session,question,answer)
                    saved=self.graph.get_state(config).values or {}
                    history=saved.get("history","")+"\nUser: "+question+"\nAssistant: "+answer
                    # Approval publishes a new exchange, not merely a history tail.
                    # run_turn uses these structured fields for the next prompt.
                    self.graph.update_state(config,{"history":history[-16000:],
                        "question":question,"answer":answer,"task_status":"completed",
                        "execution_outcome":"completed","answer_available":True})
                except Exception:
                    notices.append("The action receipt is saved, but conversation recording failed. Do not repeat the action to repair the transcript.")
            if replayed:notices.append("Showing the saved receipt; the action did not execute again.")
            return {"answer":answer,"notices":notices}



def make_browser_backend():return BrowserBackend()

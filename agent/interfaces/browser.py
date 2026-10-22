"""Streamlit adapter using the existing graph, chats, memory and providers."""
import os
from pathlib import Path
from agent.storage.chats import ChatCatalog,validate_chat_command

from agent.config.paths import DATA_ROOT as ROOT

class BrowserBackend:
    def __init__(self):
        from agent.langgraph.langgraph_agent import graph,session_config,LLM_PROVIDER
        self.graph,self.session_config,self.provider=graph,session_config,LLM_PROVIDER
        self.user=os.getenv("AI_MEMORY_USER_ID","local-user")
        self.space=os.getenv("AI_MEMORY_NAMESPACE","project")
        self.catalog=ChatCatalog(ROOT/"outputs/memory/chats.sqlite3",self.user,self.space)
        self.catalog.register("default")

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
        from agent.actions.downloads import list_created_files
        return list_created_files(self.actions(),self.user,self.space,session)

    def generated_file(self,session,token):
        from agent.actions.downloads import read_created_file
        return read_created_file(self.actions(),self.user,self.space,session,token)

    def memory(self):
        from agent.langgraph.langgraph_agent import load_long_term_memory_node
        return load_long_term_memory_node({})["memory_context"]

    def memory_records(self):
        """Read structured facts in this backend scope without model calls."""
        from agent.memory.long_term_memory import LongTermMemory
        with LongTermMemory(ROOT/"outputs/memory/long_term_memory.sqlite3") as store:
            return store.list(self.user,self.space)

    def submit_selected(self,session,question,provider):
        """Apply this browser choice only for the lifetime of one request."""
        from agent.providers.selection import provider_selection
        from agent.providers.errors import ProviderError
        info=self.provider_info(provider)
        if not info["supported"] or not info["model"] or (not info["local"] and not info["key_present"]):
            raise ProviderError(provider,"CONFIGURATION","Configure the selected provider key and default model locally before using it.",attempts=0)
        with provider_selection(provider):return self.submit(session,question)

    def submit(self,session,question):
        if not self.catalog.get(session):raise ValueError("Chat not found.")
        if not question.strip():raise ValueError("Enter a message first.")
        normalized,error=validate_chat_command(question)
        if error:return {"answer":error,"notices":[]}
        if normalized.upper().startswith(("NEW CHAT","NEW SESSION","OPEN CHAT","SESSION ")) or normalized.upper()=="LIST CHATS":
            return {"answer":"Use the sidebar to create or open a chat. Your current chat has not changed.","notices":[]}
        from agent.runtime.turns import run_turn
        from agent.runtime.context import local_action_handler
        queued=[]
        def browser_approval(action,arguments):
            from agent.actions.receipts import ActionPending
            token=self.actions().propose(self.user,self.space,session,action,arguments)
            queued.append(token)
            raise ActionPending("Action is waiting for your browser approval. Review its exact project root and arguments below; no local action has executed.")
        config=self.session_config(session,self.user,self.space)
        with local_action_handler(browser_approval):
            result=run_turn(self.graph,config,self.catalog,session,question,ROOT)
        if queued:
            result["notices"].append("Review the pending action below. Approving executes only that stored action; send another message to continue any remaining work.")
        return result

    def actions(self):
        from agent.actions.browser import BrowserActions
        return BrowserActions(ROOT/"outputs/local_actions.sqlite3")

    def pending_actions(self,session):
        return self.actions().pending(self.user,self.space,session)

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
            result,replayed=actions.execute(self.user,self.space,session,token)
            import json
            answer="Stored action returned. Receipt: "+token+"\n\n"+json.dumps(result,ensure_ascii=False,indent=2)
            notices=[]
            if not replayed:
                try:
                    self.catalog.append(session,"Approved exact local action "+token,answer)
                    saved=self.graph.get_state(config).values or {}
                    history=saved.get("history","")+"\nUser: Approved exact local action "+token+"\nAssistant: "+answer
                    self.graph.update_state(config,{"history":history[-16000:],"task_status":"completed"})
                except Exception:
                    notices.append("The action receipt is saved, but conversation recording failed. Do not repeat the action to repair the transcript.")
            if replayed:notices.append("Showing the saved receipt; the action did not execute again.")
            return {"answer":answer,"notices":notices}



def make_browser_backend():return BrowserBackend()

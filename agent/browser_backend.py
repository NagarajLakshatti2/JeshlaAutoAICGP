"""Streamlit adapter using the existing graph, chats, memory and providers."""
import os
from pathlib import Path
from agent.chat_catalog import ChatCatalog,validate_chat_command

ROOT=Path(__file__).resolve().parents[1]

class BrowserBackend:
    def __init__(self):
        from agent.langgraph.langgraph_agent import graph,session_config,LLM_PROVIDER
        self.graph,self.session_config,self.provider=graph,session_config,LLM_PROVIDER
        self.user=os.getenv("AI_MEMORY_USER_ID","local-user")
        self.space=os.getenv("AI_MEMORY_NAMESPACE","project")
        self.catalog=ChatCatalog(ROOT/"outputs/memory/chats.sqlite3",self.user,self.space)
        self.catalog.register("default")

    def list_chats(self):return self.catalog.list()
    def create_chat(self,title):return self.catalog.create(title)
    def get_chat(self,session):return self.catalog.get(session)
    def turns(self,session):return self.catalog.transcript(session)

    def memory(self):
        from agent.langgraph.langgraph_agent import load_long_term_memory_node
        return load_long_term_memory_node({})["memory_context"]

    def submit(self,session,question):
        if not self.catalog.get(session):raise ValueError("Chat not found.")
        if not question.strip():raise ValueError("Enter a message first.")
        normalized,error=validate_chat_command(question)
        if error:return {"answer":error,"notices":[]}
        if normalized.upper().startswith(("NEW CHAT","NEW SESSION","OPEN CHAT","SESSION ")) or normalized.upper()=="LIST CHATS":
            return {"answer":"Use the sidebar to create or open a chat. Your current chat has not changed.","notices":[]}
        from agent.chat_runtime import run_turn
        from agent.runtime_context import local_action_handler
        declined=[]
        def browser_approval(action,arguments):
            declined.append(action)
            return False
        config=self.session_config(session,self.user,self.space)
        with local_action_handler(browser_approval):
            result=run_turn(self.graph,config,self.catalog,session,question,ROOT)
        if declined:
            result["notices"].append("Local edits and command execution require the console's interactive approval. No proposed local action was executed in the browser.")
        return result


def make_browser_backend():return BrowserBackend()

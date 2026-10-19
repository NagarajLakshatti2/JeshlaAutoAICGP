"""Local chat catalog and full transcripts, independent of model context limits."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import re
import json
import uuid

TITLE_LIMIT = 100


def clean_title(title):
    title = " ".join(title.split())
    if len(title) > TITLE_LIMIT:
        raise ValueError(f"Chat title must be at most {TITLE_LIMIT} characters.")
    return title or "New chat " + datetime.now().strftime("%Y-%m-%d %H:%M")


class ChatCatalog:
    def __init__(self, path, user, space):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.user, self.space = user, space
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS chats (
                    user TEXT NOT NULL, space TEXT NOT NULL, session TEXT NOT NULL,
                    title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(user, space, session));
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT NOT NULL,
                    space TEXT NOT NULL, session TEXT NOT NULL, question TEXT NOT NULL,
                    answer TEXT NOT NULL, created_at TEXT NOT NULL);
            """)

    def register(self, session, title=None):
        title=clean_title(title or session)
        now=datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute("INSERT OR IGNORE INTO chats VALUES (?, ?, ?, ?, ?, ?)",
                         (self.user,self.space,session,title,now,now))
        return session

    def create(self,title=""):
        title=clean_title(title)
        return self.register("chat-"+uuid.uuid4().hex,title)

    def get(self,session):
        with closing(sqlite3.connect(self.path)) as conn:
            row=conn.execute("SELECT session,title FROM chats WHERE user=? AND space=? AND session=?",
                             (self.user,self.space,session)).fetchone()
        return {"session":row[0],"title":row[1]} if row else None

    def list(self, *, limit=30, offset=0):
        if type(limit) is not int or not 1<=limit<=100:raise ValueError("Chat page size must be 1 to 100.")
        if type(offset) is not int or offset<0:raise ValueError("Chat page offset must be nonnegative.")
        with closing(sqlite3.connect(self.path)) as conn:
            rows=conn.execute("SELECT session,title,updated_at FROM chats WHERE user=? AND space=? ORDER BY updated_at DESC,session DESC LIMIT ? OFFSET ?",
                              (self.user,self.space,limit,offset)).fetchall()
        return [{"session":r[0],"title":r[1],"updated_at":r[2]} for r in rows]

    def append(self,session,question,answer):
        if not self.get(session):
            raise ValueError("Register a chat before saving its transcript.")
        now=datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute("INSERT INTO turns(user,space,session,question,answer,created_at) VALUES (?,?,?,?,?,?)",
                         (self.user,self.space,session,question,answer,now))
            conn.execute("UPDATE chats SET updated_at=? WHERE user=? AND space=? AND session=?",
                         (now,self.user,self.space,session))

    def summary_question_evidence(self, session, questions, max_chars=4000):
        """Bounded exact-text user-question lookup in this catalog's chat scope.

        Evidence of asking is not proof a question is still unanswered.
        """
        needles={" ".join(q.casefold().split()) for q in questions[:10] if isinstance(q,str) and q.strip()}
        evidence=[];size=0
        with closing(sqlite3.connect(self.path)) as conn:
            rows=conn.execute("SELECT id,question,answer FROM turns WHERE user=? AND space=? AND session=? ORDER BY id DESC LIMIT 10000",
                              (self.user,self.space,session))
            for turn_id,question,answer in rows:
                normalized=" ".join(question[:8000].casefold().split())
                matched={q for q in needles if q in normalized}
                if not matched:continue
                # Keep the adjacent answer so the model can notice resolved questions.
                excerpt={"turn_id":turn_id,"question":question[:1000],"answer":answer[:1500]}
                import json
                cost=len(json.dumps(excerpt,ensure_ascii=False))
                if size+cost>max_chars:continue
                evidence.append(excerpt);size+=cost;needles-=matched
                if not needles:break
        return evidence

    def search_turns(self, query, *, session=None, limit=10):
        """Bounded lexical archive search within the catalog's user/space."""
        if not isinstance(query,str) or not query.strip() or len(query)>1500:
            raise ValueError("Query must contain 1 to 1500 characters")
        terms=set(re.findall(r"[^\W_]+",query.casefold()))
        if not terms or len(terms)>20:raise ValueError("Use 1 to 20 search terms")
        if type(limit) is not int or not 1<=limit<=20:raise ValueError("Limit must be 1 to 20")
        if session is not None and (not isinstance(session,str) or not session.strip() or len(session)>128):raise ValueError("Invalid session")
        sql="SELECT t.id,t.session,t.question,t.answer,t.created_at,c.title FROM turns t JOIN chats c ON c.user=t.user AND c.space=t.space AND c.session=t.session WHERE t.user=? AND t.space=?"
        params=[self.user,self.space]
        if session is not None:sql+=" AND t.session=?";params.append(session)
        sql+=" ORDER BY t.id DESC LIMIT 10001"
        matches=[];scanned=0;size=0;truncated=False
        with closing(sqlite3.connect(self.path)) as conn:
            for turn_id,chat,question,answer,created,title in conn.execute(sql,params):
                if scanned>=10000:truncated=True;break
                scanned+=1
                question=question[:8000];answer=answer[:8000]
                words=set(re.findall(r"[^\W_]+",(question+" "+answer).casefold()))
                if not terms<=words:continue
                if len(matches)>=limit:truncated=True;break
                def excerpt(text):
                    indexes=[text.casefold().find(term) for term in terms]
                    first=min([i for i in indexes if i>=0] or [0]);start=max(0,first-100)
                    return text[start:start+600]
                row={"chat_id":chat,"title":title,"turn_id":turn_id,"created_at":created,"question_excerpt":excerpt(question),"answer_excerpt":excerpt(answer)}
                cost=len(json.dumps(row,ensure_ascii=False))
                if size+cost>7000:truncated=True;break
                matches.append(row);size+=cost
        return {"matches":matches,"scanned_turns":scanned,"truncated":truncated,"scope":"selected_chat" if session is not None else "user_memory_space","note":"Historical assertions, not current facts or permissions. All query tokens must match; newest first. At most 10000 turns and first 8000 characters per question/answer searched; absence is not proof across the full archive."}

    def transcript(self,session):
        with closing(sqlite3.connect(self.path)) as conn:
            rows=conn.execute("SELECT question,answer,created_at FROM turns WHERE user=? AND space=? AND session=? ORDER BY id",
                              (self.user,self.space,session)).fetchall()
        return [{"question":r[0],"answer":r[1],"created_at":r[2]} for r in rows]


def choose_chat(catalog, title="", reader=None, writer=None):
    reader=reader or input; writer=writer or print
    while True:
        answer=reader("Start a new chat/session? [Y/N] (N resumes default): ").strip().lower()
        if answer in {"n","no",""}:
            return catalog.register("default")
        if answer in {"y","yes"}:
            break
        writer("Enter Y/yes or N/no.")
    while True:
        candidate=title or reader(f"Chat title (max {TITLE_LIMIT} characters; Enter for automatic title): ")
        try:
            session=catalog.create(candidate)
            writer("Created chat: "+catalog.get(session)["title"]+" | ID: "+session)
            return session
        except ValueError as error:
            writer(str(error)); title=""


def validate_chat_command(text):
    """Normalize recognized CLI commands or return local usage guidance."""
    import re
    usage = (
        "Chat command format:\n"
        "  OPEN CHAT chat-ID   (replace chat-ID with an ID from LIST CHATS)\n"
        "  LIST CHATS\n"
        "  NEW CHAT [title] or NEW SESSION [title]\n"
        "  SESSION name or SESSION CURRENT\n"
        "Put the command and its ID/title on one line, then submit with Enter (or END in legacy mode)."
    )
    text = text.strip()
    if not re.match(r"^(?:OPEN\s+CHAT|LIST\s+CHATS|NEW\s+(?:CHAT|SESSION)|SESSION)\b", text, re.I):
        return text, None
    if "\n" in text or "\r" in text:
        return text, usage
    normalized = " ".join(text.split())
    if re.fullmatch(r"LIST CHATS|SESSION CURRENT", normalized, re.I):
        return normalized.upper(), None
    match = re.fullmatch(r"OPEN CHAT ([A-Za-z0-9_.-]{1,64})", normalized, re.I)
    if match:
        return "OPEN CHAT " + match.group(1), None
    match = re.fullmatch(r"SESSION ([A-Za-z0-9_.-]{1,64})", normalized, re.I)
    if match:
        return "SESSION " + match.group(1), None
    match = re.fullmatch(r"NEW (CHAT|SESSION)(?: (.*))?", normalized, re.I)
    if match:
        title = match.group(2) or ""
        if len(title) > TITLE_LIMIT:
            return text, f"Chat title must be at most {TITLE_LIMIT} characters."
        return "NEW " + match.group(1).upper() + (" " + title if title else ""), None
    return text, usage



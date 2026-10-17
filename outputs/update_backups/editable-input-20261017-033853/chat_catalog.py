"""Local chat catalog and full transcripts, independent of model context limits."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid

TITLE_LIMIT = 80


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

    def list(self):
        with closing(sqlite3.connect(self.path)) as conn:
            rows=conn.execute("SELECT session,title,updated_at FROM chats WHERE user=? AND space=? ORDER BY updated_at DESC LIMIT 30",
                              (self.user,self.space)).fetchall()
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
        candidate=title or reader("Chat title (max 80 characters; Enter for automatic title): ")
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
        "Put the command and its ID/title on one line; then END on the next line."
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



"""Lazy checkpoint-backed graph lifecycle; no database is opened on import."""
import sqlite3
import threading
from functools import wraps
from pathlib import Path

class LazyGraph:
    """Preserve the synchronous graph API while deferring connection creation.

    Close only after interface work stops. Core synchronous operations hold the
    lifecycle lock; streaming/async lifecycle acceptance is outside current scope.
    """
    def __init__(self,path,builder):
        self.path=Path(path);self.builder=builder
        self._lock=threading.RLock();self._graph=None;self._connection=None

    def _ensure(self):
        if self._graph is None:
            from langgraph.checkpoint.sqlite import SqliteSaver
            self.path.parent.mkdir(parents=True,exist_ok=True)
            connection=sqlite3.connect(str(self.path),check_same_thread=False)
            try:graph=self.builder(SqliteSaver(connection))
            except BaseException:
                connection.close()
                raise
            self._connection=connection;self._graph=graph
        return self._graph

    def __getattr__(self,name):
        if name.startswith('_'):raise AttributeError(name)
        with self._lock:
            value=getattr(self._ensure(),name)
        if name in {'invoke','get_state','update_state'}:
            @wraps(value)
            def operation(*args,**kwargs):
                with self._lock:return getattr(self._ensure(),name)(*args,**kwargs)
            return operation
        return value

    def close(self):
        with self._lock:
            if self._connection is not None:self._connection.close()
            self._connection=None;self._graph=None

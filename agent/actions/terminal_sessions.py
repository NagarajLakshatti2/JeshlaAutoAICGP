"""Bounded process sessions. Each write is a separately approved action."""
import os
import subprocess
import threading
import uuid
import atexit

_lock = threading.RLock()
_sessions = {}


def _stop(entry):
    process = entry["process"]
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        if process.poll() is None:
            process.kill()


def _entry(identity, session_id):
    with _lock:
        entry = _sessions.get(session_id)
        if entry is None or entry["identity"] != identity:
            raise ValueError("Terminal session expired or belongs to another context.")
        return entry


def snapshot(identity, session_id):
    entry = _entry(identity, session_id)
    with entry["lock"]:
        return {"terminal_id": session_id, "revision": entry["revision"],
                "exit_code": entry["process"].poll(), "stdout": entry["stdout"],
                "stderr": entry["stderr"], "running": entry["process"].poll() is None,
                "command": entry["command"]}


def start(identity, tools, command, lifetime=300):
    if type(lifetime) is not int or not 1 <= lifetime <= 300:
        raise ValueError("Session lifetime must be 1–300 seconds.")
    argv = tools._command_argv(command, lifetime)
    with _lock:
        if sum(entry["process"].poll() is None for entry in _sessions.values()) >= 4:
            raise ValueError("Four terminal sessions are already running.")
        for key in list(_sessions):
            if len(_sessions) < 32:
                break
            if _sessions[key]["process"].poll() is not None:
                del _sessions[key]
        process = subprocess.Popen(argv, cwd=tools.root, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        token = uuid.uuid4().hex
        entry = {"identity": identity, "process": process, "command": command,
                 "revision": 0, "stdout": "", "stderr": "", "lock": threading.RLock()}
        _sessions[token] = entry

    def read(stream, field):
        try:
            while True:
                value = stream.read(1024)
                if not value:
                    break
                with entry["lock"]:
                    entry[field] = (entry[field] + value.decode("utf-8", errors="replace"))[-12000:]
        finally:
            stream.close()

    for stream, field in ((process.stdout, "stdout"), (process.stderr, "stderr")):
        threading.Thread(target=read, args=(stream, field), daemon=True).start()

    def expire():
        try:
            process.wait(timeout=lifetime)
        except subprocess.TimeoutExpired:
            _stop(entry)
            process.wait(timeout=10)
        finally:
            process.stdin.close()
    threading.Thread(target=expire, daemon=True).start()
    return snapshot(identity, token)


def send(identity, session_id, revision, text):
    entry = _entry(identity, session_id)
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > 1024:
        raise ValueError("Input must contain 1–1024 UTF-8 bytes.")
    with entry["lock"]:
        if revision != entry["revision"] or entry["process"].poll() is not None:
            raise ValueError("Terminal input review is stale.")
        entry["revision"] += 1
        errors = []
        def write():
            try:
                entry["process"].stdin.write(text.encode("utf-8"))
                entry["process"].stdin.flush()
            except (OSError, ValueError) as error:
                errors.append(error)
        writer = threading.Thread(target=write, daemon=True)
        writer.start()
        writer.join(timeout=2)
        if writer.is_alive():
            _stop(entry)
            raise ValueError("Terminal input stalled and the session was stopped.")
        if errors:
            raise ValueError("Terminal input could not be delivered.")
    return snapshot(identity, session_id)


def stop(identity, session_id, revision):
    entry = _entry(identity, session_id)
    with entry["lock"]:
        if revision != entry["revision"]:
            raise ValueError("Terminal stop review is stale.")
        entry["revision"] += 1
        _stop(entry)
    return snapshot(identity, session_id)


def list_sessions(identity):
    with _lock:
        keys = [key for key, entry in _sessions.items() if entry["identity"] == identity]
    return [snapshot(identity, key) for key in keys]


def _shutdown():
    with _lock:
        entries = list(_sessions.values())
    for entry in entries:
        try:
            _stop(entry)
        except (OSError, subprocess.TimeoutExpired):
            pass


atexit.register(_shutdown)

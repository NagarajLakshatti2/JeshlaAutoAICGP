"""Run unit tests with external network and browser launches blocked.

From the project root: python tests/run_offline.py
Loopback sockets remain available for asyncio and local framework internals.
This guard applies to this Python process; it is not a sandbox for subprocesses.
"""
from contextlib import ExitStack, contextmanager
import ipaddress
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def is_loopback(address):
    if not isinstance(address, tuple) or not address:
        return False
    try:
        return ipaddress.ip_address(address[0]).is_loopback
    except ValueError:
        return False


@contextmanager
def offline_guard():
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def connect(sock, address):
        if not is_loopback(address):
            raise RuntimeError("Offline tests blocked an external socket connection")
        return original_connect(sock, address)

    def connect_ex(sock, address):
        if not is_loopback(address):
            raise RuntimeError("Offline tests blocked an external socket connection")
        return original_connect_ex(sock, address)

    def blocked(*args, **kwargs):
        raise RuntimeError("Offline tests require a mock for HTTP requests or browser launches")

    with ExitStack() as stack:
        stack.enter_context(patch("socket.socket.connect", connect))
        stack.enter_context(patch("socket.socket.connect_ex", connect_ex))
        stack.enter_context(patch("requests.sessions.Session.request", blocked))
        for name in ("open", "open_new", "open_new_tab"):
            stack.enter_context(patch("webbrowser." + name, blocked))
        yield


def main():
    import os,io
    from datetime import datetime,timezone
    from functools import partial
    from tests.offline_log import ProgressResult,writer
    path=ROOT/'outputs/logs'/('offline-tests-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())+'.jsonl')
    try:
        path.parent.mkdir(parents=True,exist_ok=True);handle=path.open('w',encoding='utf-8')
        print('Offline progress log:',path,flush=True)
    except OSError:
        handle=io.StringIO();print('Progress file unavailable; tests will still run.',flush=True)
    with handle,patch.dict('os.environ',{'JESHLA_EXECUTION_MODE':'offline'}):
        progress=writer(handle);progress('run_started')
        try:
            with offline_guard():
                progress('discovery_started')
                suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
                progress('discovery_finished',test_count=suite.countTestCases())
                result=unittest.TextTestRunner(verbosity=1,resultclass=partial(ProgressResult,progress=progress)).run(suite)
            progress('run_finished',tests=result.testsRun,status='passed' if result.wasSuccessful() else 'failed',failures=len(result.failures),errors=len(result.errors))
        except BaseException:
            progress('run_interrupted');raise
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

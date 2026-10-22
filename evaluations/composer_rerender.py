"""Reproduce duplicate composers with isolated chat data and slow fake responses."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NODE = Path("C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, default=ROOT / "streamlit_app.py")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/acceptance/composer-rerender-20261022/browser")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jeshla-composer-") as folder:
        entry = Path(folder) / "fixture.py"
        entry.write_text("""import sys,time
from pathlib import Path
sys.path.insert(0,ROOT_VALUE)
import streamlit as st
from tests.test_streamlit_ui import FakeBackend
from agent import browser_backend,browser_activity
class Backend(FakeBackend):
    provider='groq'
    def submit(self,session,question):
        time.sleep(1.5)
        result=super().submit(session,question)
        result['notices']=['Fixture quota notice','Fixture provider selected']
        return result
@st.cache_resource
def fixture():return Backend(FOLDER_VALUE)
browser_backend.make_browser_backend=fixture
browser_activity.log_browser_event=lambda *a,**k:None
original_markdown=st.markdown
def slow_history(body,*a,**k):
    if body in {'hi','how are you','Test answer'}:time.sleep(.3)
    return original_markdown(body,*a,**k)
from unittest.mock import patch
with patch.object(st,'markdown',slow_history):
    exec(compile(Path(APP_VALUE).read_text(encoding='utf-8'),APP_VALUE,'exec'))
""".replace("ROOT_VALUE", repr(str(ROOT))).replace("FOLDER_VALUE", repr(folder)).replace("APP_VALUE", repr(str(args.app.resolve()))), encoding="utf-8")
        with socket.socket() as connection:
            connection.bind(("127.0.0.1", 0));port=connection.getsockname()[1]
        url=f"http://127.0.0.1:{port}/JeshlaAutoAI/"
        with (args.output_dir / "server.log").open("w", encoding="utf-8") as log:
            server=subprocess.Popen([sys.executable,"-m","streamlit","run",str(entry),"--server.address","127.0.0.1","--server.port",str(port),"--server.baseUrlPath","JeshlaAutoAI","--server.headless","true","--server.fileWatcherType","none"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for _ in range(120):
                    if server.poll() is not None:raise RuntimeError("Fixture server stopped")
                    try:
                        with urllib.request.urlopen(url+"_stcore/health", timeout=1) as health:
                            if health.status==200:break
                    except Exception:time.sleep(.25)
                else:raise RuntimeError("Fixture server startup timeout")
                result=subprocess.run([str(NODE),str(ROOT/"evaluations/composer_rerender_browser.cjs"),url,str(args.output_dir.resolve())],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
                (args.output_dir / "browser.log").write_text(result.stdout,encoding="utf-8")
                print(result.stdout[-4000:]);return result.returncode
            finally:
                server.terminate()
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:server.kill();server.wait()
                (args.output_dir / "owned-server.json").write_text(json.dumps({"pid":server.pid,"status":"stopped","port":port}),encoding="utf-8")


if __name__ == "__main__":raise SystemExit(main())

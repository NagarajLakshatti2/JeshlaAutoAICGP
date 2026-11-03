"""Small synthetic Gradle/native-report fixtures; no external project or network."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import os
import sys

from agent.tools.project_tools import ProjectTools
from agent.tools.test_results import parse_test_results


def put(root, name, text):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_plan(root, source="calculator.py"):
    root = Path(root).resolve()
    put(root, source, "def add(a, b):\n    return a - b\n")
    if not (root/"requirements.md").exists():
        put(root, "requirements.md", "Adding two numbers must return their arithmetic sum.\n")
    if not (root/"reports/TEST-demo.xml").exists():
        put(root, "reports/TEST-demo.xml", '<testsuite><testcase name="entry" classname="Demo"><failure>AssertionError: expected 5 but got -1</failure></testcase></testsuite>')
    if not (root/"baseline.json").exists():
        native = parse_test_results(root, "reports/TEST-demo.xml")
        native["freshness"] = "associated with this command by changed content/metadata and execution time window"
        stamp = datetime.fromisoformat(native["modified_at"])
        run = {"command":["gradlew","test","--tests","Demo.entry"],"exit_code":1,"timed_out":False,
               "report_status":"fresh_reports_found","report_errors":[],"reports":[native],
               "started_at":(stamp-timedelta(seconds=1)).isoformat(),"finished_at":(stamp+timedelta(seconds=1)).isoformat()}
        put(root, "baseline.json", json.dumps(run))
    if not (root/"gradlew.bat").exists():
        put(root, "gradlew.bat", "@echo off\r\necho synthetic fixture only\r\n")
    if os.name != "nt" and not (root/"gradlew").exists():
        path = put(root, "gradlew", "#!/bin/sh\necho synthetic fixture only\n")
        path.chmod(0o755)
    request = {"relative_path":"reports/TEST-demo.xml","case_name":"entry","case_class":"Demo",
               "run_file":"baseline.json","source_file":source,"old_text":"return a - b","new_text":"return a + b",
               "diagnosis":"The arithmetic expression subtracts while the saved requirement and failed assertion expect addition.",
               "requirements":[{"relative_path":"requirements.md","start_line":1,"max_lines":1}],
               "command":["gradlew","test","--tests","Demo.entry"],"relative_report_folder":"reports","timeout":20}
    return ProjectTools(root).prepare_test_repair(request)


def policy_plans(root):
    apply = make_plan(root, "apply_calculator.py")["plan"]
    rerun = make_plan(root, "rerun_calculator.py")["plan"]
    put(root, "rerun_calculator.py", "def add(a, b):\n    return a + b\n")
    return {"apply_test_repair":apply,"rerun_test_repair":rerun}


def real_runner(root):
    put(root, "calculator.py", "def add(a, b):\n    return a - b\n")
    put(root, "requirements.md", "Adding two numbers must return their arithmetic sum.\n")
    put(root, "fixture_runner.py", """import sys,unittest
from pathlib import Path
from xml.sax.saxutils import escape
from calculator import add
assert sys.argv[1:]==["test","--tests","Demo.entry"],"synthetic runner rejects expanded scope"
class Demo(unittest.TestCase):
    def entry(self):
        self.assertEqual(add(2,3),5)
result=unittest.TestResult()
Demo("entry").run(result)
errors=result.errors+result.failures
failure=("<failure>"+escape(errors[0][1])+"</failure>") if errors else ""
Path("reports").mkdir(exist_ok=True)
Path("reports/TEST-demo.xml").write_text('<testsuite><testcase name="entry" classname="Demo">'+failure+'</testcase></testsuite>',encoding="utf-8")
print("Synthetic fixture: selected case", "failed" if errors else "passed")
raise SystemExit(bool(errors))
""")
    if os.name == "nt":
        put(root, "gradlew.bat", '@echo off\r\n"' + sys.executable + '" -B fixture_runner.py %*\r\n')
    else:
        path = put(root, "gradlew", "#!/bin/sh\nexec '" + sys.executable + "' -B fixture_runner.py \"$@\"\n")
        path.chmod(0o755)

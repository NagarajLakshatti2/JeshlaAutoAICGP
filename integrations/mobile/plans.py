"""Bind a selected Android text smoke to saved native discovery and app bytes."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def evidence_file(value, maximum):
    if not isinstance(value, str) or not value:
        raise ValueError("An explicit evidence-file path is required.")
    path = Path(value).resolve()
    if not path.is_relative_to(ROOT / "outputs/acceptance") or not path.is_file():
        raise ValueError("Evidence must be an existing file under outputs/acceptance.")
    if path.stat().st_size > maximum:
        raise ValueError("Evidence file exceeds this pilot's size bound.")
    return path


def checked_bytes(plan, key, maximum):
    path = evidence_file(plan.get(key), maximum)
    raw = path.read_bytes()
    digest = plan.get(key + "_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Evidence bytes changed: " + key)
    return path, raw


def validate_android_plan(plan):
    if not isinstance(plan, dict) or plan.get("execution_status") != "not_run":
        raise ValueError("Select an unexecuted Android native pilot plan.")
    case = plan.get("case_id")
    if not isinstance(case, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", case):
        raise ValueError("Use a simple explicit case identifier.")
    server = urlparse(plan.get("server_url", ""))
    if (server.scheme != "http" or server.hostname != "127.0.0.1" or server.username or server.password
            or server.path not in ("", "/") or server.query or server.fragment
            or server.port is None or not 1024 <= server.port <= 65535):
        raise ValueError("This local pilot requires an explicit 127.0.0.1 Appium port.")
    udid = plan.get("udid")
    if not isinstance(udid, str) or not re.fullmatch(r"emulator-[0-9]{4,5}", udid):
        raise ValueError("This adapter supports only an explicitly selected emulator.")
    for key in ("app_package", "app_activity"):
        value = plan.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", value):
            raise ValueError("Use an explicit inspected Android package/activity.")
    if not plan["app_activity"].startswith(plan["app_package"] + "."):
        raise ValueError("Activity must belong to the inspected application package.")
    value = plan.get("test_value")
    if not isinstance(value, str) or not 1 <= len(value) <= 500 or any(ord(c) < 32 for c in value):
        raise ValueError("Use bounded single-line text data.")
    apk, _ = checked_bytes(plan, "app_file", 50_000_000)
    if apk.suffix.lower() != ".apk":
        raise ValueError("Choose the verified Android APK.")
    _, raw = checked_bytes(plan, "inspection_file", 1_000_000)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("External XML definitions are not accepted.")
    tree = ET.fromstring(raw)
    field_id = plan.get("field_id")
    if not isinstance(field_id, str) or not field_id.startswith(plan["app_package"] + ":id/"):
        raise ValueError("Field must belong to the inspected application.")
    matches = [node for node in tree.iter() if node.get("resource-id") == field_id]
    if len(matches) != 1:
        raise ValueError("Use a unique observed native resource ID; no positional fallback.")
    field = matches[0]
    if (field.get("class") != "android.widget.EditText" or field.get("enabled") != "true"
            or field.get("displayed") != "true" or field.get("password") != "false"
            or field.get("input-type") != "524289" or field.get("showing-hint") != "false"):
        raise ValueError("This pilot requires an observed visible ordinary unhinted non-password text field.")
    maximum = field.get("max-text-length")
    if maximum is not None and (not maximum.isdigit() or len(value) > int(maximum)):
        raise ValueError("Selected test data exceeds the observed field limit.")
    _, raw = checked_bytes(plan, "baseline_file", 65_000)
    baseline = json.loads(raw)
    if (baseline.get("status") != "passed" or baseline.get("session_closed") is not True
            or baseline.get("field_id") != field_id
            or [baseline.get(k) for k in ("initial_value", "entered_value", "cleared_value")] != ["", value, ""]):
        raise ValueError("Use the exact selected successful and closed native smoke baseline.")
    caps = baseline.get("actual_capabilities", {})
    expected = {"udid": udid, "appPackage": plan["app_package"], "appActivity": plan["app_activity"]}
    if any(caps.get(key, caps.get("appium:" + key)) != wanted for key, wanted in expected.items()):
        raise ValueError("App/device identity differs from the saved selected smoke.")
    if Path(caps.get("app", caps.get("appium:app", ""))).resolve() != apk:
        raise ValueError("APK path differs from the saved selected smoke.")
    return {"inspection_binding": "Y", "baseline_binding": "Y", "app_bytes": "Y",
            "note": "Selected demo-smoke reuse only; not business-rule entailment or execution approval."}

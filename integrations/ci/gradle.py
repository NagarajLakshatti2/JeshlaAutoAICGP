"""Prepare a portable native CI bundle; no publication or application execution."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from agent.config.paths import DATA_ROOT

ROOT = DATA_ROOT
TEMPLATES = Path(__file__).with_name("templates")


def prepare_ci_bundle(tools, output_dir, profile):
    """Validate current selected sources and write a review bundle under acceptance.

    Profile origins/locators/case methods are explicit reviewed pilot data, not
    inferred from filenames or defaults. Nothing is installed in the target here.
    """
    out = Path(output_dir).resolve()
    boundary = (ROOT / "outputs" / "acceptance").resolve()
    if out == boundary or not out.is_relative_to(boundary):
        raise ValueError("Choose a dedicated acceptance output directory.")
    if not isinstance(profile, dict) or set(profile) != {"version", "api", "web", "source_text_sha256"} or type(profile["version"]) is not int or profile["version"] != 1:
        raise ValueError("Profile needs version 1, api, web and source_text_sha256.")
    for lane in ("api", "web"):
        data = profile[lane]
        keys = {"class", "methods", "url", "user_id"} if lane == "api" else {"class", "methods", "url", "by", "target", "value", "dismiss"}
        if not isinstance(data, dict) or set(data) != keys:
            raise ValueError("Unexpected lane configuration fields.")
        if not isinstance(data["class"], str) or not re.fullmatch(r"(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*", data["class"]):
            raise ValueError("Select one qualified Java class per lane.")
        methods = data["methods"]
        if not isinstance(methods, list) or not 1 <= len(methods) <= 20 or any(not isinstance(m, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", m) for m in methods) or len(methods) != len(set(methods)):
            raise ValueError("Expected methods must be explicit, unique Java identifiers.")
        if not isinstance(data["url"], str) or len(data["url"]) > 1500:
            raise ValueError("Select a bounded HTTPS URL.")
        url = urlparse(data["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.port not in (None,443) or url.query or (lane == "api" and url.fragment) or any(c.isspace() for c in data["url"]):
            raise ValueError("Use public HTTPS pilot origins without credentials/query.")
        host = url.hostname.lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError("This CI profile supports public demo origins only.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("Nonpublic literal addresses are excluded from the CI profile.")
        if lane == "api":
            if type(data["user_id"]) is not int or not 1 <= data["user_id"] < 2**31:
                raise ValueError("Choose a positive API fixture user ID.")
        else:
            if not isinstance(data["by"], str) or not isinstance(data["dismiss"], str) or data["by"] not in {"label", "placeholder"} or data["dismiss"] not in {"", "Decline"}:
                raise ValueError("Use the inspected locator and reviewed cookie refusal action.")
            if any(not isinstance(data[k], str) or not data[k].strip() or len(data[k]) > 200 for k in ("target", "value")):
                raise ValueError("Choose bounded reviewed field/data values.")
        accepted_methods = ({"API_TC_001_directLookupMatchesRequestedUser", "API_TC_002_existingFilterMatchesDirectLookup", "API_TC_003_absentIdFilterReturnsEmptyCollection"}
                            if lane == "api" else {"TI_TC_001_textEntryAndClear"})
        if set(methods) != accepted_methods:
            raise ValueError("This CI adapter supports only the selected accepted API/web pilot methods.")
        source = tools._resolve_file("src/test/java/" + data["class"].replace(".", "/") + ".java")
        text = source.read_text(encoding="utf-8-sig")
        if any(not re.search(r"\b" + re.escape(method) + r"\s*\(", text) for method in methods):
            raise ValueError("A selected method is absent from the inspected source.")
    required = {"build.gradle", "src/main/java/config/ConfigReader.java"} | {
        "src/test/java/" + profile[lane]["class"].replace(".", "/") + ".java" for lane in ("api", "web")}
    hashes = profile["source_text_sha256"]
    if not isinstance(hashes, dict) or set(hashes) != required:
        raise ValueError("Bind build.gradle, ConfigReader and both selected Java source revisions.")
    for file, digest in hashes.items():
        if hashlib.sha256(tools._resolve_file(file).read_text(encoding="utf-8-sig").encode("utf-8")).hexdigest() != digest:
            raise ValueError("Selected source revision changed; review a new CI profile.")
    build = tools._resolve_file("build.gradle").read_text(encoding="utf-8-sig")
    if any(not re.search(r"\b"+key+r"\s*=", build) for key in ("playwrightVersion", "testngVersion", "restassuredVersion", "jacksonVersion")):
        raise ValueError("CI recipe requires the inspected dependency-version convention.")
    if not (tools.root/"gradlew").is_file():
        raise ValueError("Portable CI requires the existing Unix Gradle wrapper.")
    files = {"ci/ws9/pilots.json": json.dumps(profile, indent=2)+"\n",
             "gradle/ws9-ci.init.gradle": (TEMPLATES/"ws9-ci.init.gradle").read_text(encoding="utf-8"),
             ".github/workflows/ws9-selected-pilots.yml": (TEMPLATES/"ws9-selected-pilots.yml").read_text(encoding="utf-8")}
    for relative, content in files.items():
        path = out/relative
        if path.exists():
            raise FileExistsError("CI bundle already exists; select a fresh review directory.")
    for relative, content in files.items():
        path=out/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
    return {"status":"P", "scope":"review bundle only; no remote CI result", "target":str(tools.root),
            "files":{f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files},
            "selected_methods":{lane:profile[lane]["methods"] for lane in ("api", "web")},
            "publication_or_dispatch_performed":False}

"""Bounded new-directory project reviews and explicitly approved file creation."""
import hashlib
import json
import keyword
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

MAX_FILES = 20
MAX_TOTAL = 200000
RESERVED = re.compile(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.I)
JAVA_WORDS = set("abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false null _".split())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def component(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value)
            or value in {".", ".."} or value.endswith(".") or RESERVED.fullmatch(value)):
        raise ValueError("Use a portable folder/file component of 1–80 letters, numbers, dots, hyphens or underscores.")
    return value


def relative_file(value):
    from agent.tools.project_tools import SKIP_DIRS, SKIP_FILES, TEXT_EXTENSIONS
    if not isinstance(value, str) or PureWindowsPath(value).drive:
        raise ValueError("Use a relative project file path.")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts or len(path.parts) > 10:
        raise ValueError("Project files must remain under the new folder.")
    for part in path.parts:
        component(part)
        if part.casefold() in {p.casefold() for p in SKIP_DIRS | SKIP_FILES} or part.startswith(".env"):
            raise ValueError("Credential, repository metadata and generated folders are excluded.")
    if path.name != ".gitignore" and path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError("Only supported text source/configuration files can be created.")
    return path.as_posix()


def prepare_project(tools, folder_name, project_files):
    component(folder_name)
    if folder_name.startswith("."):
        raise ValueError("Choose a visible new project folder.")
    destination = tools.root / folder_name
    if destination.exists() or destination.is_symlink():
        raise ValueError("The destination already exists. Choose a new folder; nothing will be overwritten or merged.")
    if not isinstance(project_files, list) or not 1 <= len(project_files) <= MAX_FILES:
        raise ValueError("Review one to twenty project files.")
    files = []
    for item in project_files:
        if not isinstance(item, dict) or set(item) != {"relative_path", "content"}:
            raise ValueError("Each project file needs only relative_path and content.")
        name, content = relative_file(item["relative_path"]), item["content"]
        if not isinstance(content, str) or "\0" in content:
            raise ValueError("Project content must be UTF-8 text, not binary data.")
        data = content.encode("utf-8")
        if len(data) > 50000:
            raise ValueError("A project file exceeds the 50 KB review limit.")
        files.append({"relative_path": name, "content": content, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    files.sort(key=lambda item: item["relative_path"].casefold())
    keys = [f["relative_path"].casefold() for f in files]
    if len(set(keys)) != len(keys) or any(any(key.startswith(other + "/") for other in keys if key != other) for key in keys):
        raise ValueError("Project file names conflict, including case or file/folder collisions.")
    total = sum(f["size_bytes"] for f in files)
    if total > MAX_TOTAL:
        raise ValueError("The complete project review exceeds 200 KB.")
    plan = {"version": 1, "parent_root": str(tools.root), "folder_name": folder_name,
            "destination": str(destination), "files": files, "total_bytes": total}
    plan["id"] = hashlib.sha256(canonical(plan).encode()).hexdigest()
    return {"plan": plan, "created": False, "note": "Review all paths and contents. A separate exact create_project approval is required. No install, test, command or Git operation is included."}


def validate_creation(tools, plan):
    if not isinstance(plan, dict):
        raise ValueError("Prepare a complete project review first.")
    try:
        files = [{"relative_path": f["relative_path"], "content": f["content"]} for f in plan["files"]]
        expected = prepare_project(tools, plan["folder_name"], files)["plan"]
    except (KeyError, TypeError):
        raise ValueError("The project review is incomplete.") from None
    if canonical(plan) != canonical(expected):
        raise ValueError("Project paths or contents changed. Prepare a fresh review.")
    return expected


def create_project(tools, plan):
    plan = validate_creation(tools, plan)
    destination = tools.root / plan["folder_name"]
    destination.mkdir(exist_ok=False)
    written = []
    for item in plan["files"]:
        current = destination
        if current.is_symlink() or current.resolve() != destination:
            raise ValueError("New project folder changed during creation; inspect the partial result.")
        relative = PurePosixPath(item["relative_path"])
        for part in relative.parts[:-1]:
            current = current / part
            current.mkdir(exist_ok=True)
            if current.is_symlink() or not current.resolve().is_relative_to(destination):
                raise ValueError("A new project directory changed; inspect the partial result.")
        path = current / relative.name
        with path.open("xb") as output:
            output.write(item["content"].encode("utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError("A created file changed; inspect the partial result before continuing.")
        written.append({"relative_path": item["relative_path"], "size_bytes": item["size_bytes"], "sha256": digest})
    return {"created": True, "project_root": str(destination), "plan_id": plan["id"],
            "files": written, "commands_executed": False, "tests_executed": False,
            "note": "New source files created and their bytes verified. No dependencies installed, tests run, Git repository initialized or service connected. Interrupted/failed creation is not automatically deleted or retried."}


def starter_files(name, template, package):
    component(name)
    if template == "python" and not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name):
        raise ValueError("Use a Python project name beginning and ending with a letter or number.")
    parts = package.split(".") if isinstance(package, str) else []
    reserved = JAVA_WORDS if template == "java-playwright" else set(keyword.kwlist)
    if (template not in {"python", "java-playwright"} or not parts or len(parts) > 5
            or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) or p in reserved for p in parts)):
        raise ValueError("Use a valid package name; dots can separate parent/child packages.")
    base = "/".join(parts)
    ignore = ".env\n.env.*\n.venv/\n__pycache__/\n*.py[cod]\nbuild/\ndist/\n.gradle/\noutputs/\n"
    if template == "python":
        files = {".gitignore": ignore,
                 "pyproject.toml": '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = '+json.dumps(name)+'\nversion = "0.1.0"\nrequires-python = ">=3.10"\n\n[tool.setuptools.packages.find]\nwhere = ["src"]\n',
                 "src/"+base+"/greeting.py": '"""Small application behavior; replace with your project logic."""\n\ndef greeting(name: str) -> str:\n    return f"Hello, {name}!"\n',
                 "src/"+base+"/__main__.py": 'from '+package+'.greeting import greeting\n\nif __name__ == "__main__":\n    print(greeting("World"))\n',
                 "tests/test_greeting.py": 'import unittest\nfrom '+package+'.greeting import greeting\n\nclass GreetingTests(unittest.TestCase):\n    def test_supplied_name_is_used(self):\n        self.assertEqual(greeting("Nagaraj"), "Hello, Nagaraj!")\n\nif __name__ == "__main__":\n    unittest.main()\n',
                 "README.md": '# '+name+'\n\nPython package starter with parent/child packages, src layout and standard-library tests. No AI service is configured.\n\nPowerShell from this new project:\n\n```powershell\n$env:PYTHONPATH = "src"\npython -m unittest discover -s tests -v\npython -m '+package+'\n```\n\nAlternatively install the package into your chosen environment with `python -m pip install -e .`. That separate step can obtain build dependencies; creation does not install or execute anything. This starter is not production acceptance.\n'}
        for end in range(1, len(parts)+1):
            files['src/'+"/".join(parts[:end])+'/__init__.py'] = '"""'+".".join(parts[:end])+' package."""\n'
    else:
        files = {".gitignore": ignore,
                 "settings.gradle": 'rootProject.name = '+json.dumps(name)+'\n',
                 "build.gradle": "plugins { id 'java' }\n\nrepositories { mavenCentral() }\njava { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }\ndependencies {\n    implementation 'com.microsoft.playwright:playwright:1.62.0'\n    testImplementation 'org.testng:testng:7.12.0'\n}\ntest { useTestNG() }\n",
                 "src/main/java/"+base+"/ExamplePage.java": 'package '+package+';\n\nimport com.microsoft.playwright.Page;\nimport java.util.Objects;\n\npublic class ExamplePage {\n    private final Page page;\n    public ExamplePage(Page page) { this.page = Objects.requireNonNull(page); }\n    public String title() { return page.title(); }\n}\n',
                 "src/test/java/"+base+"/LocalPageTest.java": 'package '+package+';\n\nimport com.microsoft.playwright.*;\nimport org.testng.Assert;\nimport org.testng.annotations.Test;\n\npublic class LocalPageTest {\n    @Test public void readsLocalPageTitle() {\n        try (Playwright playwright = Playwright.create();\n             Browser browser = playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(true))) {\n            Page page = browser.newPage();\n            page.setContent("<title>Starter</title><h1>Local page</h1>");\n            Assert.assertEquals(new ExamplePage(page).title(), "Starter");\n        }\n    }\n}\n',
                 "README.md": '# '+name+'\n\nJava 17 / Gradle / Playwright / TestNG starter using separate production page and test packages. Library versions match the existing reviewed local project declarations; they are not a claim of newest versions.\n\nPrerequisites: a compatible JDK, installed Gradle, resolved dependencies and a Playwright Chromium installation. This starter does not bundle a Gradle wrapper or browsers. Once those prerequisites are configured, run `gradle test`. The example uses local HTML, with no target website or AI service.\n\nProject creation does not install dependencies, download browsers, execute tests or initialize Git. These are separately approved setup/execution steps. This starter is not production acceptance.\n'}
    return [{"relative_path": path, "content": content} for path, content in files.items()]

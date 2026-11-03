"""Bounded Cucumber selection for the existing reviewed repair workflow."""
from pathlib import Path
import re


def native_identity(case):
    """The data-provider ordinal may change; titles and runner may not."""
    name = case.get("name", "")
    if not isinstance(name, str):
        return None
    match = re.fullmatch(r'runScenario(?:\[\d+\])?\("([^"\r\n]{1,250})", "([^"\r\n]{1,250})"\)', name)
    return (case.get("class", ""), *match.groups()) if match else None


def matches_case(case, selection):
    return native_identity(case) == (selection["runner_class"], selection["scenario"], selection["feature"])


def _scenarios(content):
    """Accept only the English, plain-scenario subset we can bind unambiguously."""
    pending, feature, scenarios, current, steps = [], None, [], None, 0
    for number, raw in enumerate(content.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            if line.startswith("# language:"):
                raise ValueError("Localized Gherkin is outside this repair slice.")
            continue
        if any(token in line for token in ('\"\"\"', "'''")) or line.startswith("|"):
            raise ValueError("Docstrings and tables need a separate scenario review.")
        if line.startswith("@"):
            tags = line.split()
            if not all(re.fullmatch(r"@[A-Za-z0-9_-]{1,80}", tag) for tag in tags):
                raise ValueError("Use plain Gherkin tags without expressions/comments.")
            pending.extend(tags)
            continue
        if line.startswith("Feature:"):
            if feature is not None or current is not None:
                raise ValueError("Expected exactly one Feature heading.")
            feature = line.removeprefix("Feature:").strip()
            scenarios.append({"kind": "feature", "tags": pending})
            pending = []
        elif line.startswith("Scenario:"):
            if feature is None or current is not None and not steps:
                raise ValueError("Scenario needs a Feature and nonempty steps.")
            title = line.removeprefix("Scenario:").strip()
            if not title or len(title) > 250 or '"' in title:
                raise ValueError("Scenario title is unsupported or ambiguous.")
            current = {"kind": "scenario", "tags": pending, "scenario": title, "line": number}
            scenarios.append(current)
            pending, steps = [], 0
        elif re.match(r"(?:Given|When|Then|And|But|\*)\s+", line):
            if current is None or pending:
                raise ValueError("Unbound step or dangling scenario tag.")
            steps += 1
        else:
            # Outlines, Rules, Backgrounds and free-form descriptions are intentionally
            # rejected rather than approximated by an incomplete Gherkin parser.
            raise ValueError("Only English Feature/Scenario headings and plain steps are supported.")
    if not feature or '"' in feature or len(feature) > 250 or pending or not current or not steps:
        raise ValueError("Incomplete or unsupported feature selection.")
    return feature, scenarios


def prepare_selection(tools, selection, case):
    """Read and bind an exact runner's bounded feature inventory; never execute."""
    from agent.tools.test_repairs import _read, _relative
    from agent.tools.execution_review import _masked_java
    if not isinstance(selection, dict) or set(selection) != {"runner_file", "feature_file", "tag"}:
        raise ValueError("Cucumber selection needs exactly runner_file, feature_file and tag.")
    if not isinstance(selection["tag"], str) or not re.fullmatch(r"@[A-Za-z0-9_-]{1,80}", selection["tag"]):
        raise ValueError("Choose one literal scenario tag, not a tag expression.")
    runner, text, path = _read(tools.root, selection["runner_file"])
    if not runner["file"].startswith("src/test/java/") or path.suffix != ".java":
        raise ValueError("Choose a Java TestNG runner in src/test/java.")
    masked = _masked_java(text)
    if not all(re.search(r"\bimport\s+io\.cucumber\.testng\." + name + r"\s*;", masked)
               for name in ("AbstractTestNGCucumberTests", "CucumberOptions")):
        raise ValueError("Use the explicit Cucumber TestNG imports for this runner.")
    package = re.search(r"\bpackage\s+([\w.]+)\s*;", masked)
    declaration = re.search(r"\bpublic\s+class\s+(\w+)\s+extends\s+AbstractTestNGCucumberTests\s*\{\s*\}", masked)
    if not package or not declaration or len(re.findall(r"\bclass\s+", masked)) != 1:
        raise ValueError("Use one direct, empty AbstractTestNGCucumberTests runner.")
    cls = package[1] + "." + declaration[1]
    if runner["file"] != "src/test/java/" + cls.replace(".", "/") + ".java":
        raise ValueError("Runner class and source path do not agree.")
    annotation = re.search(r"@CucumberOptions\s*\(([^()]*)\)", masked)
    if not annotation:
        raise ValueError("A literal CucumberOptions annotation is required.")
    attribute = re.search(r"\bfeatures\s*=", masked[annotation.start():annotation.end()])
    if not attribute:
        raise ValueError("Runner must declare its literal feature paths.")
    start = annotation.start() + attribute.end()
    literal = re.match(r'\s*(\{\s*"[^"\\]+"(?:\s*,\s*"[^"\\]+")*\s*\}|"[^"\\]+")\s*(?=,|\))', text[start:])
    if not literal:
        raise ValueError("Use literal project-relative feature roots, without expressions.")
    roots = re.findall(r'"([^"\\]+)"', literal[1])
    paths, entries = set(), 0
    for name in roots:
        relative = _relative(tools.root, name)
        if not relative.startswith("src/test/resources/") or any(c in name for c in "*:?"):
            raise ValueError("Feature roots must stay under src/test/resources without selectors/globs.")
        base = tools.root / relative
        if base.is_file() and base.suffix == ".feature":
            paths.add(base)
        elif base.is_dir():
            # Walk with explicit bounds and reject links; do not scan unrelated projects.
            pending, directories = [base], 0
            while pending:
                directory = pending.pop(); directories += 1
                if directories > 80:
                    raise ValueError("Feature directory inventory exceeds this slice.")
                for child in directory.iterdir():
                    entries += 1
                    if entries > 1000:
                        raise ValueError("Feature inventory exceeds 1000 directory entries.")
                    _relative(tools.root, child.relative_to(tools.root).as_posix())
                    if child.is_dir():
                        pending.append(child)
                    elif child.suffix == ".feature":
                        paths.add(child)
                    if len(paths) > 40 or len(pending) > 80:
                        raise ValueError("Feature inventory exceeds 40 files/80 directories.")
        else:
            raise ValueError("Feature root is missing or unsupported.")
    if not paths or len(paths) > 40:
        raise ValueError("Choose a runner with one to forty feature files.")
    selected = _relative(tools.root, selection["feature_file"])
    inventory, matches, identities, total = [], [], [], 0
    for feature_path in sorted(paths):
        ref, content, _ = _read(tools.root, feature_path.relative_to(tools.root).as_posix())
        total += ref["size_bytes"]
        if total > 512_000:
            raise ValueError("Feature inventory exceeds 512 KB.")
        inventory.append(ref)
        feature, scenarios = _scenarios(content)
        for scenario in scenarios:
            if scenario["kind"] == "scenario":
                identities.append((feature, scenario["scenario"]))
            occurrences = scenario["tags"].count(selection["tag"])
            if occurrences:
                if scenario["kind"] != "scenario" or occurrences != 1:
                    raise ValueError("Choose one direct scenario tag, not an inherited/repeated tag.")
                matches.append({"file": ref["file"], "feature": feature,
                                "scenario": scenario["scenario"], "line": scenario["line"]})
    if len(matches) != 1 or matches[0]["file"] != selected:
        raise ValueError("The tag must identify exactly one scenario in the runner's entire feature inventory.")
    if identities.count((matches[0]["feature"], matches[0]["scenario"])) != 1:
        raise ValueError("Native feature/scenario titles must be unambiguous across the runner inventory.")
    build, build_text, _ = _read(tools.root, "build.gradle")
    _build_selectors(build_text)
    result = {**selection, "runner_class": cls, "runner": runner, "build": build,
              "features": inventory, **{k:v for k,v in matches[0].items() if k != "file"}}
    if not matches_case(case, result):
        raise ValueError("Native failed case does not match the exact selected runner, scenario and feature.")
    # Re-read each revision before publishing the plan.
    for ref in [runner, build, *inventory]:
        _read(tools.root, ref["file"], ref["sha256"])
    return result


def _build_selectors(content):
    """Recognize the reviewed Gradle adapter; arbitrary build logic needs review.

    This is a compatibility guard, not a semantic proof of arbitrary Groovy.
    The entire build file is also revision-bound for exact-action review.
    """
    token = r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|//[^\n]*|/\*[\s\S]*?\*/'''
    clean = re.sub(token, lambda m: m[1] or "", content)
    checks = [
        r'\bdef\s+selectedRunner\s*=\s*System\.getProperty\("test\.runner",\s*""\)\.trim\(\)',
        r'\buseTestNG\s*\{\s*testngOptions\s*->',
        r'\bif\s*\(selectedRunner\)\s*\{\s*def\s+xml\s*=\s*testngOptions\.suiteXmlBuilder\(\)',
        r"xml\.classes\s*\{\s*xml\.'class'\(name:\s*selectedRunner\)\s*\}",
        r'\bdef\s+cucumberTags\s*=\s*System\.getProperty\("cucumber\.filter\.tags"\)',
        r'\bif\s*\(cucumberTags\?\.trim\(\)\)\s*\{\s*systemProperty\s+"cucumber\.filter\.tags",\s*cucumberTags\s*\}',
    ]
    if not all(len(re.findall(pattern, clean)) == 1 for pattern in checks):
        raise ValueError("Gradle runner/tag forwarding is outside the reviewed adapter; inspect its build wiring first.")


def focused_command(tools, command, selection, folder, timeout):
    from agent.tools.test_repairs import _relative
    required = ["-Dtest.runner=" + selection["runner_class"], "-Dcucumber.filter.tags=" + selection["tag"]]
    if not isinstance(command, list) or not 7 <= len(command) <= 16 or not all(isinstance(v, str) for v in command):
        raise ValueError("Supply one bounded Cucumber command list.")
    if command[0] != "gradlew" or command.count("test") != 1 or command.count("--tests") != 1:
        raise ValueError("Select one Gradle test runner and scenario tag.")
    index = command.index("--tests")
    if index+1 >= len(command) or command[index+1] != selection["runner_class"] + ".runScenario":
        raise ValueError("Gradle --tests must select exactly the chosen runner's runScenario method.")
    if any(command.count(value) != 1 for value in required):
        raise ValueError("Use exactly the selected runner and one literal scenario tag.")
    allowed = {"test", "--no-daemon", "--offline", "--console=plain", "--rerun-tasks", *required}
    for i, value in enumerate(command[1:], 1):
        if i not in {index, index+1} and value not in allowed and not re.fullmatch(r"-D(?:env|browser|headless)=[A-Za-z0-9_-]{1,40}", value):
            raise ValueError("Unsupported Cucumber rerun selector, task or flag.")
    if len(command) != len(set(command)):
        raise ValueError("Duplicate Cucumber command arguments are unsupported.")
    for key in ("env", "browser", "headless"):
        if sum(value.startswith("-D" + key + "=") for value in command) > 1:
            raise ValueError("Conflicting environment/browser flags are unsupported.")
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ValueError("Rerun timeout must be an integer between 1 and 300.")
    tools._command_argv(command, timeout)
    return {"command": command, "relative_report_folder": _relative(tools.root, folder), "timeout": timeout}

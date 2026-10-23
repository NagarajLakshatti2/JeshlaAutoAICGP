"""Prepare one isolated native Android Java/TestNG task; no execution or approval."""
import hashlib
import json
import re
from pathlib import Path
from integrations.api.gradle import check_api_pilot_result as check_android_pilot_result
from integrations.mobile.plans import validate_android_plan
from integrations.mobile.text_test import android_text_source

ROOT = Path(__file__).resolve().parents[2]
# Pinned official compatibility pair; not upgrades to the target's normal dependency graph.
APPIUM_JAVA = "11.0.0"
SELENIUM_API = "4.50.0"
INIT_SCRIPT = r"""
gradle.projectsEvaluated {
    def p = gradle.rootProject
    def evidenceRoot = new File(System.getProperty('ws9.output'))
    def reportRoot = new File(System.getProperty('ws9.reports'))
    def selectedClass = System.getProperty('ws9.test.class')
    def deps = p.configurations.create('ws9MobilePilotDeps')
    p.dependencies.add(deps.name, 'io.appium:java-client:11.0.0')
    p.dependencies.add(deps.name, 'org.seleniumhq.selenium:selenium-api:4.50.0')
    p.dependencies.add(deps.name, "org.testng:testng:${p.ext.testngVersion}")
    p.dependencies.add(deps.name, "com.fasterxml.jackson.core:jackson-databind:${p.ext.jacksonVersion}")
    deps.resolutionStrategy.eachDependency { dependency ->
        if (dependency.requested.group == 'org.seleniumhq.selenium') dependency.useVersion '4.50.0'
    }
    def pilotFile = new File(p.projectDir, 'src/mobileTest/java/' + selectedClass.replace('.', '/') + '.java')
    if (p.sourceSets.test.java.files.contains(pilotFile)) {
        throw new GradleException('Mobile pilot must remain outside the default test source set')
    }
    p.tasks.register('verifyWs9MobileIsolation') {
        doLast { println 'Verified: selected mobile pilot is outside the default test source set' }
    }
    def classesFolder = new File(evidenceRoot, 'compiled')
    def src = p.sourceSets.create('ws9MobilePilot') {
        java.setSrcDirs([new File(p.projectDir, 'src/mobileTest/java')])
        java.include(selectedClass.replace('.', '/') + '.java')
        resources.setSrcDirs([])
        compileClasspath = deps
        runtimeClasspath = output + deps
    }
    p.tasks.named(src.compileJavaTaskName) { options.release = 17; destinationDirectory = classesFolder }
    src.output.classesDirs.setFrom(p.files(classesFolder))
    p.tasks.register('ws9MobilePilot', Test) {
        dependsOn p.tasks.named(src.classesTaskName)
        testClassesDirs = p.files(classesFolder); classpath = src.runtimeClasspath
        useTestNG(); workingDir = evidenceRoot
        include selectedClass.replace('.', '/') + '.class'
        ['server','udid','app','sha256','package','activity','field','value'].each { key ->
            systemProperty 'mobile.pilot.' + key, System.getProperty('mobile.pilot.' + key, '')
        }
        systemProperty 'mobile.pilot.evidence', new File(evidenceRoot, 'native').absolutePath
        systemProperty 'rp.enable', 'false'; systemProperty 'rp.enabled', 'false'
        reports.junitXml.outputLocation = new File(reportRoot, 'xml')
        reports.html.outputLocation = new File(reportRoot, 'html')
        binaryResultsDirectory = new File(reportRoot, 'binary')
        testLogging { events 'passed', 'failed', 'skipped' }
        outputs.upToDateWhen { false }
    }
}
"""


def prepare_android_pilot(tools, output_dir, *, test_class, plan):
    android_text_source(test_class, plan.get("case_id"))
    validate_android_plan(plan)
    out = Path(output_dir).resolve()
    if not out.is_relative_to(ROOT / "outputs/acceptance") or out == ROOT / "outputs/acceptance":
        raise ValueError("Choose a dedicated mobile evidence folder under outputs/acceptance.")
    build = tools._resolve_file("build.gradle").read_text(encoding="utf-8-sig")
    if any(not re.search(r"\b" + key + r"\s*=", build) for key in ("testngVersion", "jacksonVersion")):
        raise ValueError("This adapter needs the inspected TestNG/Jackson version declarations.")
    tools._resolve_file("src/mobileTest/java/" + test_class.replace(".", "/") + ".java")
    if not any((tools.root / name).is_file() for name in ("gradlew", "gradlew.bat")):
        raise ValueError("The selected project has no Gradle wrapper.")
    out.mkdir(parents=True, exist_ok=True)
    init = out / "mobile-pilot.init.gradle"; init.write_text(INIT_SCRIPT, encoding="utf-8")
    (out / "reviewed-plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    report = "build/ws9-mobile-pilot/" + hashlib.sha256(str(out).encode()).hexdigest()[:12] + "/reports"
    command = ["gradlew", "--offline", "--no-daemon", "--console=plain", "-I", str(init), "ws9MobilePilot",
               "-Dws9.output=" + str(out), "-Dws9.reports=" + str(tools.root / report), "-Dws9.test.class=" + test_class]
    props = {"server": plan["server_url"], "udid": plan["udid"], "app": str(Path(plan["app_file"]).resolve()),
             "sha256": plan["app_file_sha256"], "package": plan["app_package"], "activity": plan["app_activity"],
             "field": plan["field_id"], "value": plan["test_value"]}
    command.extend("-Dmobile.pilot." + key + "=" + value for key, value in props.items())
    return {"command": command, "relative_report_folder": report, "timeout": 300}

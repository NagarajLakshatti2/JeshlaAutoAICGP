"""Prepare an isolated REST Assured/TestNG Gradle recipe; never execute it here."""
from pathlib import Path
import hashlib
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]

INIT_SCRIPT = r'''
gradle.projectsEvaluated {
    def p = gradle.rootProject
    def evidenceRoot = new File(System.getProperty('ws9.output'))
    def reportRoot = new File(System.getProperty('ws9.reports'))
    def selectedClass = System.getProperty('ws9.test.class')
    def selectedSource = selectedClass.replace('.', '/') + '.java'
    def deps = p.configurations.create('ws9ApiPilotDeps')
    p.dependencies.add(deps.name, "io.rest-assured:rest-assured:${p.ext.restassuredVersion}")
    p.dependencies.add(deps.name, "org.testng:testng:${p.ext.testngVersion}")
    p.dependencies.add(deps.name, "com.fasterxml.jackson.core:jackson-databind:${p.ext.jacksonVersion}")
    def classesFolder = new File(evidenceRoot, 'compiled')
    def resourcesFolder = new File(evidenceRoot, 'processed-resources')
    def src = p.sourceSets.create('ws9ApiPilot') {
        java.setSrcDirs([new File(p.projectDir, 'src/main/java'), new File(p.projectDir, 'src/test/java')])
        java.include('config/ConfigReader.java', selectedSource)
        resources.setSrcDirs([new File(evidenceRoot, 'resources')])
        compileClasspath = deps
        runtimeClasspath = output + deps
    }
    p.tasks.named(src.compileJavaTaskName) {
        options.release = 17
        destinationDirectory = classesFolder
    }
    p.tasks.named(src.processResourcesTaskName) { destinationDir = resourcesFolder }
    src.output.classesDirs.setFrom(p.files(classesFolder))
    src.output.resourcesDir = resourcesFolder
    p.tasks.register('ws9ApiPilot', Test) {
        dependsOn p.tasks.named(src.classesTaskName)
        testClassesDirs = p.files(classesFolder)
        classpath = src.runtimeClasspath
        useTestNG()
        workingDir evidenceRoot
        include selectedClass.replace('.', '/') + '.class'
        systemProperty 'api.base.url', System.getProperty('ws9.api.url')
        systemProperty 'api.pilot.user.id', System.getProperty('ws9.user.id')
        systemProperty 'ws9.evidence.dir', new File(evidenceRoot, 'responses').absolutePath
        systemProperty 'rp.enable', 'false'
        systemProperty 'rp.enabled', 'false'
        reports.junitXml.outputLocation = new File(reportRoot, 'xml')
        reports.html.outputLocation = new File(reportRoot, 'html')
        binaryResultsDirectory = new File(reportRoot, 'binary')
        testLogging { events 'passed', 'failed', 'skipped' }
        outputs.upToDateWhen { false }
    }
}
'''


def prepare_api_pilot(tools, output_dir, *, test_class, base_url, user_id):
    """Return args for existing run_tests_and_parse; selection is not approval.

    This adapter supports the inspected config.ConfigReader/Gradle dependency
    convention. It does not migrate arbitrary projects or modify build.gradle.
    """
    if not isinstance(test_class, str) or len(test_class) > 200 or not re.fullmatch(
            r'(?:[A-Za-z_][A-Za-z0-9_]*\.)+[A-Za-z_][A-Za-z0-9_]*', test_class):
        raise ValueError('Choose one qualified Java test-class name.')
    if type(user_id) is not int or not 1 <= user_id <= 2_147_483_647:
        raise ValueError('Select a positive existing user ID.')
    if not isinstance(base_url, str) or len(base_url) > 1500 or any(c.isspace() for c in base_url):
        raise ValueError('Use a bounded explicit API URL.')
    url = urlparse(base_url)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Use an HTTPS API URL without credentials, query or fragment.')
    out = Path(output_dir).resolve()
    if not out.is_relative_to(ROOT / 'outputs' / 'acceptance') or out == ROOT / 'outputs' / 'acceptance':
        raise ValueError('Choose a dedicated evidence folder under outputs/acceptance.')
    build = tools._resolve_file('build.gradle').read_text(encoding='utf-8-sig')
    tools._resolve_file('src/main/java/config/ConfigReader.java')
    tools._resolve_file('src/test/java/' + test_class.replace('.', '/') + '.java')
    if not (tools.root / 'gradlew.bat').is_file() and not (tools.root / 'gradlew').is_file():
        raise ValueError('The selected project has no Gradle wrapper.')
    if any(not re.search(r'\b' + key + r'\s*=', build) for key in
           ('restassuredVersion', 'testngVersion', 'jacksonVersion')):
        raise ValueError('This adapter requires the inspected dependency-version declarations.')
    out.mkdir(parents=True, exist_ok=True)
    resources = out / 'resources' / 'config';resources.mkdir(parents=True, exist_ok=True)
    (resources / 'common.properties').write_text('api.timeout.ms=15000\n', encoding='utf-8')
    init = out / 'api-pilot.init.gradle';init.write_text(INIT_SCRIPT, encoding='utf-8')
    # Distinct evidence folders use distinct target report folders; no stale run reuse.
    report_key = hashlib.sha256(str(out).encode('utf-8')).hexdigest()[:12]
    report_relative = 'build/ws9-api-pilot/' + report_key + '/reports'
    command = ['gradlew', '--offline', '--no-daemon', '--console=plain', '-I', str(init), 'ws9ApiPilot',
               '-Dws9.output=' + str(out), '-Dws9.reports=' + str(tools.root / report_relative),
               '-Dws9.test.class=' + test_class, '-Dws9.api.url=' + base_url, '-Dws9.user.id=' + str(user_id)]
    return {'command': command, 'relative_report_folder': report_relative, 'timeout': 150}


def check_api_pilot_result(result, expected_methods):
    """Require a successful command and exact fresh case inventory; never trust exit zero alone."""
    expected = set(expected_methods)
    if not expected or len(expected) != len(expected_methods):
        raise ValueError('Expected case methods must be unique and nonempty.')
    if (result.get('exit_code') != 0 or result.get('timed_out') or result.get('report_errors')
            or result.get('report_status') != 'fresh_reports_found'):
        return {'status': 'P', 'accepted': False, 'reason': 'Command failed or no valid fresh result report was returned.'}
    reports = result.get('reports', [])
    # One selected TestNG class should yield one JUnit XML report, without overlap.
    if len(reports) != 1 or reports[0].get('details_truncated'):
        return {'status': 'P', 'accepted': False, 'reason': 'Expected one complete non-overlapping class report.'}
    report = reports[0]
    tests = report.get('tests', [])
    actual = [item.get('name') for item in tests]
    if (len(actual) != len(expected) or set(actual) != expected
            or report.get('total') != len(expected) or report.get('passed') != len(expected)
            or report.get('failed') or report.get('skipped') or report.get('incomplete')
            or report.get('configuration_failure_count') or report.get('overall_status') != 'passed'
            or any(item.get('status') != 'passed' for item in tests)):
        return {'status': 'P', 'accepted': False, 'reason': 'Fresh report did not pass the exact selected case inventory.'}
    return {'status': 'Y', 'accepted': True, 'total': len(expected), 'report_file': report['file']}

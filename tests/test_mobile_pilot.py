"""Native plan binding and isolated recipe reject stale/ambiguous/remote inputs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from integrations.mobile import plans, gradle
from integrations.mobile.text_test import android_text_source
from agent.tools.project_tools import ProjectTools


class MobilePilotTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root = Path(folder.name); self.evidence = self.root / 'outputs/acceptance/setup'
        self.evidence.mkdir(parents=True); self.project = self.root / 'target'; self.project.mkdir()
        self.tools = ProjectTools(str(self.project))
        for module in (plans, gradle):
            active = patch.object(module, 'ROOT', self.root); active.start(); self.addCleanup(active.stop)
        self.app = self.evidence / 'demo.apk'; self.app.write_bytes(b'APK test fixture')
        self.xml = self.evidence / 'source.xml'
        self.node = ('<node resource-id="example.demo:id/input" class="android.widget.EditText" '
                     'enabled="true" displayed="true" password="false" input-type="524289" '
                     'showing-hint="false" max-text-length="5000"/>')
        self.xml.write_text('<hierarchy>' + self.node + '</hierarchy>', encoding='utf-8')
        self.baseline = self.evidence / 'baseline.json'
        self.result = {'status': 'passed', 'session_closed': True, 'field_id': 'example.demo:id/input',
                       'initial_value': '', 'entered_value': 'Hello World', 'cleared_value': '',
                       'actual_capabilities': {'udid': 'emulator-5580', 'appPackage': 'example.demo',
                                               'appActivity': 'example.demo.TextFields', 'app': str(self.app)}}
        self.baseline.write_text(json.dumps(self.result), encoding='utf-8')
        self.plan = {'case_id': 'ANDROID-SMOKE-001', 'execution_status': 'not_run',
                     'server_url': 'http://127.0.0.1:4727', 'udid': 'emulator-5580',
                     'app_package': 'example.demo', 'app_activity': 'example.demo.TextFields',
                     'test_value': 'Hello World', 'field_id': 'example.demo:id/input'}
        for key, path in [('app_file', self.app), ('inspection_file', self.xml), ('baseline_file', self.baseline)]:
            self.plan[key] = str(path); self.plan[key + '_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.project / 'build.gradle').write_text("ext { testngVersion = '7.12.0'; jacksonVersion = '2.22.0' }", encoding='utf-8')
        (self.project / 'gradlew.bat').write_text('@echo fixture', encoding='utf-8')
        self.source = self.project / 'src/mobileTest/java/tests/mobile/DemoTest.java'; self.source.parent.mkdir(parents=True)
        self.source.write_text(android_text_source('tests.mobile.DemoTest'), encoding='utf-8')

    def rewrite(self, key, path, content):
        path.write_text(content, encoding='utf-8'); self.plan[key + '_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

    def test_valid_binding_preserves_sources(self):
        before = self.xml.read_bytes(); result = plans.validate_android_plan(self.plan)
        self.assertEqual(result['inspection_binding'], 'Y'); self.assertEqual(result['baseline_binding'], 'Y')
        self.assertEqual(self.xml.read_bytes(), before)

    def test_remote_or_credentialed_or_unbounded_servers_rejected(self):
        for server in ['http://localhost:4727', 'http://192.0.2.1:4727', 'https://127.0.0.1:4727',
                       'http://u:p@127.0.0.1:4727', 'http://127.0.0.1', 'http://127.0.0.1:80',
                       'http://127.0.0.1:4727/wd/hub', 'http://127.0.0.1:4727?q=x']:
            with self.subTest(server=server), self.assertRaises(ValueError):
                plans.validate_android_plan(dict(self.plan, server_url=server))

    def test_each_stale_artifact_is_rejected(self):
        for key in ['app_file', 'inspection_file', 'baseline_file']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                plans.validate_android_plan(dict(self.plan, **{key + '_sha256': '0' * 64}))

    def test_evidence_escape_or_oversize_rejected(self):
        outside = self.root / 'outside.apk'; outside.write_bytes(b'x')
        with self.assertRaises(ValueError): plans.evidence_file(str(outside), 10)
        with self.assertRaises(ValueError): plans.evidence_file(str(self.app), 2)

    def test_duplicate_locator_rejected(self):
        self.rewrite('inspection_file', self.xml, '<hierarchy>' + self.node * 2 + '</hierarchy>')
        with self.assertRaisesRegex(ValueError, 'unique'): plans.validate_android_plan(self.plan)

    def test_disabled_hidden_password_and_wrong_control_rejected(self):
        for old, new in [('enabled="true"', 'enabled="false"'), ('displayed="true"', 'displayed="false"'),
                         ('password="false"', 'password="true"'), ('android.widget.EditText', 'android.widget.Button'),
                         ('input-type="524289"', 'input-type="2"'), ('showing-hint="false"', 'showing-hint="true"')]:
            with self.subTest(change=new):
                self.rewrite('inspection_file', self.xml, '<hierarchy>' + self.node.replace(old, new) + '</hierarchy>')
                with self.assertRaises(ValueError): plans.validate_android_plan(self.plan)

    def test_limit_and_external_xml_rejected(self):
        self.rewrite('inspection_file', self.xml, '<hierarchy>' + self.node.replace('5000', '5') + '</hierarchy>')
        with self.assertRaises(ValueError): plans.validate_android_plan(self.plan)
        self.rewrite('inspection_file', self.xml, '<!DOCTYPE data [<!ENTITY sample SYSTEM "file:///tmp/x">]><hierarchy/>')
        with self.assertRaises(ValueError): plans.validate_android_plan(self.plan)

    def test_incomplete_or_unclosed_baseline_rejected(self):
        for changed in [{'status': 'incomplete'}, {'session_closed': False}, {'entered_value': 'Hello'}, {'cleared_value': 'x'}]:
            with self.subTest(changed=changed):
                result = dict(self.result, **changed); self.rewrite('baseline_file', self.baseline, json.dumps(result))
                with self.assertRaises(ValueError): plans.validate_android_plan(self.plan)

    def test_app_device_locator_and_data_mismatch_rejected(self):
        for key, value in [('udid', 'emulator-5590'), ('udid', 'physical-device'),
                           ('app_activity', 'other.demo.Screen'), ('app_package', 'other.demo'),
                           ('field_id', 'example.demo:id/missing'), ('test_value', 'Different'),
                           ('test_value', 'a\nb'), ('execution_status', 'passed')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                plans.validate_android_plan(dict(self.plan, **{key: value}))

    def test_template_is_configurable_with_native_assertions_and_cleanup(self):
        source = android_text_source('tests.mobile.DemoTest', 'MOB-42')
        self.assertIn('MOB_42_textEntryAndClear', source); self.assertIn('driver.quit()', source)
        self.assertIn('readTimeout(Duration.ofSeconds(60))', source)
        self.assertIn('session_creation_uncertain', source)
        self.assertIn('Assert.assertEquals(field.getText(), expected', source)
        self.assertIn('Assert.assertEquals(count, 1', source); self.assertIn('failure.png', source)
        self.assertIn('appium:autoGrantPermissions", false', source)
        self.assertNotIn('io.appium.android.apis', source); self.assertNotIn('Hello World', source)
        self.assertNotIn('D:\\', source)

    def test_bad_java_identifiers_rejected(self):
        for cls in ['tests.web.Demo', 'tests.mobile.A;import X', 'Demo', '../Demo']:
            with self.subTest(cls=cls), self.assertRaises(ValueError): android_text_source(cls)
        with self.assertRaises(ValueError): android_text_source('tests.mobile.Demo', 'a/b')

    def test_recipe_only_prepares_isolated_task(self):
        before = self.source.read_bytes(); build = (self.project / 'build.gradle').read_bytes()
        result = gradle.prepare_android_pilot(self.tools, self.root / 'outputs/acceptance/run',
                                              test_class='tests.mobile.DemoTest', plan=self.plan)
        self.assertIn('--offline', result['command']); self.assertIn('ws9MobilePilot', result['command'])
        self.assertEqual(result['timeout'], 300); self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual((self.project / 'build.gradle').read_bytes(), build)
        recipe = (self.root / 'outputs/acceptance/run/mobile-pilot.init.gradle').read_text(encoding='utf-8')
        self.assertIn('testClassesDirs = p.files(classesFolder)', recipe)
        self.assertIn('src.output.classesDirs.setFrom', recipe); self.assertIn("options.release = 17", recipe)
        self.assertIn('src/mobileTest/java', recipe); self.assertIn('verifyWs9MobileIsolation', recipe)
        self.assertFalse(self.source.is_relative_to(self.project / 'src/test/java'))
        self.assertIn("'rp.enable', 'false'", recipe); self.assertIn("java-client:11.0.0", recipe)
        self.assertIn("dependency.useVersion '4.50.0'", recipe)

    def test_output_escape_or_missing_source_and_versions_rejected(self):
        with self.assertRaises(ValueError):
            gradle.prepare_android_pilot(self.tools, self.root / 'elsewhere', test_class='tests.mobile.DemoTest', plan=self.plan)
        self.source.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            gradle.prepare_android_pilot(self.tools, self.root / 'outputs/acceptance/run', test_class='tests.mobile.DemoTest', plan=self.plan)
        self.source.write_text('fixture', encoding='utf-8'); (self.project / 'build.gradle').write_text('plugins {}', encoding='utf-8')
        with self.assertRaises(ValueError):
            gradle.prepare_android_pilot(self.tools, self.root / 'outputs/acceptance/run', test_class='tests.mobile.DemoTest', plan=self.plan)

    def test_report_checker_reuses_existing_strict_fresh_report_gate(self):
        from integrations.api.gradle import check_api_pilot_result
        self.assertIs(gradle.check_android_pilot_result, check_api_pilot_result)
        self.assertFalse(gradle.check_android_pilot_result({'exit_code': 0}, ['case'])['accepted'])

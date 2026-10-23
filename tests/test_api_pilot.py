"""Native API recipe and exact fresh-report acceptance; no Gradle or network run."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.project_tools import ProjectTools
from integrations.api import gradle


class ApiPilotTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.base=Path(folder.name)
        self.target=self.base/'target';self.target.mkdir()
        for name,text in {
            'build.gradle':"ext { restassuredVersion = '6.0.1'; testngVersion = '7.12.0'; jacksonVersion = '2.22.0' }",
            'gradlew.bat':'@echo off',
            'src/main/java/config/ConfigReader.java':'package config; class ConfigReader {}',
            'src/test/java/tests/api/ReadTest.java':'package tests.api; class ReadTest {}',
        }.items():
            path=self.target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
        self.tools=ProjectTools(str(self.target));self.output=self.base/'outputs/acceptance/run-one'
        self.patch=patch.object(gradle,'ROOT',self.base);self.patch.start();self.addCleanup(self.patch.stop)
        self.methods=['API_TC_001_direct','API_TC_002_filter','API_TC_003_absent']
        self.result={'exit_code':0,'timed_out':False,'report_errors':[], 'report_status':'fresh_reports_found',
          'reports':[{'file':'build/pilot/TEST-ReadTest.xml','total':3,'passed':3,'failed':0,'skipped':0,
                      'incomplete':0,'overall_status':'passed','configuration_failure_count':0,
                      'details_truncated':False,'tests':[{'name':name,'status':'passed'} for name in self.methods]}]}

    def prepare(self,**changes):
        args={'test_class':'tests.api.ReadTest','base_url':'https://example.test','user_id':1};args.update(changes)
        return gradle.prepare_api_pilot(self.tools,self.output,**args)

    def test_preparation_keeps_target_unchanged_and_never_runs_commands(self):
        before={p.relative_to(self.target):p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        with patch.object(self.tools,'run_command',side_effect=AssertionError('No execution')) as run:
            args=self.prepare();run.assert_not_called()
        self.assertEqual(before,{p.relative_to(self.target):p.read_bytes() for p in self.target.rglob('*') if p.is_file()})
        self.assertEqual(args['command'][0],'gradlew')
        self.assertIn('--offline',args['command'])
        self.assertIn('-Dws9.test.class=tests.api.ReadTest',args['command'])
        self.assertTrue((self.output/'api-pilot.init.gradle').is_file())
        script=(self.output/'api-pilot.init.gradle').read_text(encoding='utf-8')
        self.assertIn('testClassesDirs = p.files(classesFolder)',script)
        self.assertIn('src.output.classesDirs.setFrom(p.files(classesFolder))',script)
        self.assertNotIn('ReportPortalTestNGListener',script)
        self.assertIn("systemProperty 'rp.enable', 'false'",script)
        self.assertIn('workingDir evidenceRoot',script)
        self.assertEqual(args['timeout'],150)

    def test_equal_folder_names_in_different_runs_do_not_share_reports(self):
        one=self.prepare()
        two=gradle.prepare_api_pilot(self.tools,self.base/'outputs/acceptance/other/run-one',
            test_class='tests.api.ReadTest',base_url='https://example.test',user_id=1)
        self.assertNotEqual(one['relative_report_folder'],two['relative_report_folder'])

    def test_invalid_class_and_user_id_are_rejected(self):
        for changes in ({'test_class':'../ReadTest'},{'test_class':'ReadTest'},{'test_class':'tests.api.X; delete'},
                        {'user_id':True},{'user_id':0},{'user_id':-1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.prepare(**changes)
        self.assertFalse(self.output.exists())

    def test_credentials_and_unsupported_api_urls_are_rejected(self):
        for url in ('http://example.test','https://u:p@example.test','https://example.test?key=secret',
                    'https://example.test#route','https://example.test/has space'):
            with self.subTest(url=url),self.assertRaises(ValueError):self.prepare(base_url=url)
        self.assertFalse(self.output.exists())

    def test_output_escape_and_missing_project_convention_are_rejected(self):
        with self.assertRaises(ValueError):
            gradle.prepare_api_pilot(self.tools,self.base/'outside',test_class='tests.api.ReadTest',base_url='https://example.test',user_id=1)
        (self.target/'build.gradle').write_text('plugins {}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'dependency-version'):self.prepare()
        self.assertFalse(self.output.exists())

    def test_exact_fresh_success_is_accepted(self):
        result=gradle.check_api_pilot_result(self.result,self.methods)
        self.assertTrue(result['accepted']);self.assertEqual(result['total'],3)

    def test_exit_zero_and_no_source_never_become_a_pass(self):
        for changes in ({'reports':[],'report_status':'no_fresh_results'}, {'exit_code':1},
                        {'timed_out':True},{'report_errors':[{'file':'bad.xml'}]}):
            value=copy.deepcopy(self.result);value.update(changes)
            with self.subTest(changes=changes):self.assertFalse(gradle.check_api_pilot_result(value,self.methods)['accepted'])

    def test_skipped_failed_incomplete_or_config_failure_cannot_pass(self):
        for changes in ({'failed':1},{'skipped':1},{'incomplete':1},{'configuration_failure_count':1},
                        {'details_truncated':True},{'passed':2},{'overall_status':'failed'}):
            value=copy.deepcopy(self.result);value['reports'][0].update(changes)
            with self.subTest(changes=changes):self.assertFalse(gradle.check_api_pilot_result(value,self.methods)['accepted'])

    def test_missing_duplicate_or_unexpected_cases_cannot_pass(self):
        for names in (self.methods[:2],self.methods[:2]+['OtherTest'],[self.methods[0]]*3):
            value=copy.deepcopy(self.result);value['reports'][0]['tests']=[{'name':name,'status':'passed'} for name in names]
            with self.subTest(names=names):self.assertFalse(gradle.check_api_pilot_result(value,self.methods)['accepted'])
        value=copy.deepcopy(self.result);value['reports'].append(copy.deepcopy(value['reports'][0]))
        self.assertFalse(gradle.check_api_pilot_result(value,self.methods)['accepted'])

    def test_duplicate_expected_methods_are_not_accepted(self):
        with self.assertRaises(ValueError):gradle.check_api_pilot_result(self.result,[self.methods[0]]*3)


if __name__=='__main__':unittest.main()

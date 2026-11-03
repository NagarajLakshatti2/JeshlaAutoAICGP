"""Saved Cucumber failures gain bounded citations without rerunning or guessing cause."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.execution_review import attach_review, review_execution
from tests.test_execution_results import payload, report


class CucumberFailureReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.page = self.put('src/main/java/demo/LoginPage.java',
            'package demo;\nclass LoginPage {\n void validate() {\n  checkRequired();\n }\n}\n')
        self.steps = self.put('src/test/java/steps/LoginSteps.java',
            'package steps;\nclass LoginSteps {\n void verifyRequired() {\n  page.validate();\n }\n}\n')
        self.runner = self.put('src/test/java/runners/LoginRunner.java', 'class LoginRunner {}')
        self.feature = self.put('src/test/resources/features/login/Login Pilot.feature',
            'Feature: Login\n\n Scenario: QPH-012 Empty fields\n  Given the form is open\n  When both fields are submitted empty\n  Then fields are required\n')
        self.errors = ['at demo.LoginPage.validate(LoginPage.java:4)\n'
                       'at steps.LoginSteps.verifyRequired(LoginSteps.java:4)\n'
                       'at step (' + self.feature.as_uri() + ':6)']

    def put(self, name, text):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def data(self):
        return payload(exit_code=1, reports=[report(total=1, passed=0, failed=1,
            tests=[{'name':'runScenario[0]("QPH-012 Empty fields", "Login")',
                    'class':'runners.LoginRunner', 'status':'failed', 'errors':list(self.errors)}])],
            report_status='fresh_reports_found')['result']

    def locations(self, data=None):
        review = review_execution(data or self.data(), self.root)
        return [f['evidence'] for f in review['findings'] if f['kind']=='reported_failure_location']

    def test_reported_feature_page_and_step_have_exact_lines_and_hashes(self):
        locations = self.locations()
        self.assertEqual(len(locations), 3)
        self.assertEqual({item['file'] for item in locations},
            {str(path.relative_to(self.root).as_posix()) for path in (self.page,self.steps,self.feature)})
        for item in locations:
            path = self.root/item['file']
            self.assertEqual(item['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(item['quote'], path.read_text().splitlines()[item['line']-1].strip())
        self.assertEqual(next(item['line'] for item in locations if item['role']=='reported_feature_step'),6)

    def test_passed_case_does_not_get_failed_stack_citations(self):
        data = self.data();data['reports'][0].update(passed=1,failed=0)
        data['reports'][0]['tests'][0]['status']='passed'
        self.assertEqual(self.locations(data), [])

    def test_unassociated_report_never_reads_source(self):
        data=self.data();data['reports'][0]['freshness']='historical'
        with patch('agent.tools.test_failures._load',side_effect=AssertionError('No read')):
            self.assertEqual(self.locations(data), [])

    def test_outside_or_remote_feature_uri_is_not_read(self):
        for uri in ((self.root.parent/'outside.feature').as_uri(),
                    'file://server/share/secret.feature',
                    (self.root/'src/test/resources/features/../../../../../outside.feature').as_uri()):
            with self.subTest(uri=uri):
                self.errors=['at step ('+uri+':6)']
                self.assertEqual(self.locations(), [])

    def test_feature_title_mismatch_outline_or_non_step_is_not_guessed(self):
        for text in ('Feature: Login\n\n Scenario: A different scenario\n  Given form\n  When empty\n  Then required\n',
                     'Feature: Login\n\n Scenario Outline: QPH-012 Empty fields\n  Given form\n  When empty\n  Then required\n',
                     'Feature: Login\n\n Scenario: QPH-012 Empty fields\n  Given form\n  When empty\n  Examples:\n'):
            with self.subTest(text=text):
                self.feature.write_text(text,encoding='utf-8')
                self.assertFalse(any(item['role']=='reported_feature_step' for item in self.locations()))

    def test_docstring_or_non_english_feature_is_not_invented_as_a_step(self):
        for text in ('Feature: Login\n Scenario: QPH-012 Empty fields\n  Given form\n  \"\"\"\n  text\n  Then fake step inside a string\n  \"\"\"\n',
                     '# language: fr\nFeature: Login\n Scenario: QPH-012 Empty fields\n  Given form\n  When empty\n  Then required\n'):
            with self.subTest(text=text):
                self.feature.write_text(text,encoding='utf-8')
                self.assertFalse(any(item['role']=='reported_feature_step' for item in self.locations()))

    def test_java_mismatched_filename_method_or_line_is_not_guessed(self):
        for frame in ('at demo.LoginPage.validate(Other.java:4)',
                      'at demo.LoginPage.absent(LoginPage.java:4)',
                      'at demo.LoginPage.validate(LoginPage.java:99)',
                      'at demo.LoginPage.validate(LoginPage.java:6)'):
            with self.subTest(frame=frame):
                self.errors=[frame]
                self.assertEqual(self.locations(), [])

    def test_overloaded_or_multiline_void_declaration_is_left_unreviewed(self):
        for text in ('class LoginPage { void validate() {} void validate(int n) {} }',
                     'class LoginPage {\n void validate(\n int n) {\n  checkRequired();\n }\n}'):
            with self.subTest(text=text):
                self.page.write_text(text,encoding='utf-8')
                self.errors=['at demo.LoginPage.validate(LoginPage.java:4)']
                self.assertEqual(self.locations(), [])

    def test_duplicate_source_candidates_are_ambiguous(self):
        self.put('src/test/java/demo/LoginPage.java',self.page.read_text())
        self.errors=['at demo.LoginPage.validate(LoginPage.java:4)']
        self.assertEqual(self.locations(), [])

    def test_feature_junction_is_not_followed(self):
        original=Path.is_junction
        with patch.object(Path,'is_junction',lambda p:p.name=='login' or original(p)):
            locations=self.locations()
        self.assertFalse(any(item['role']=='reported_feature_step' for item in locations))

    def test_oversized_source_is_not_loaded(self):
        self.page.write_text('x'*256001,encoding='utf-8')
        self.errors=['at demo.LoginPage.validate(LoginPage.java:4)']
        from agent.tools.test_failures import _load
        def bounded(root, relative, *args, **kwargs):
            self.assertNotEqual(relative, 'src/main/java/demo/LoginPage.java', 'Oversized source must not be read')
            return _load(root, relative, *args, **kwargs)
        with patch('agent.tools.test_failures._load',side_effect=bounded):
            self.assertEqual(self.locations(), [])

    def test_shared_source_file_budget_covers_failure_and_runner_reads(self):
        cases=[]
        for i in range(12):
            self.put('src/test/java/demo/Failure'+str(i)+'.java',
                'class Failure'+str(i)+' {\n void validate() {\n  checkRequired();\n }\n}')
            cases.append({'class':'runners.LoginRunner','name':'runScenario['+str(i)+']("Case '+str(i)+'", "Login")',
                'status':'failed','errors':['at demo.Failure'+str(i)+'.validate(Failure'+str(i)+'.java:3)']})
        data=self.data();data['reports'][0].update(total=12,failed=12,tests=cases)
        from agent.tools.test_failures import _load
        with patch('agent.tools.test_failures._load',wraps=_load) as read:
            locations=self.locations(data)
        self.assertLessEqual(read.call_count,10)
        self.assertLessEqual(len({item['file'] for item in locations}),10)

    def test_review_is_readonly_and_no_causal_or_approval_claim_is_added(self):
        data=self.data();before=copy.deepcopy(data)
        files={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('subprocess.run',side_effect=AssertionError('No execution')):
            reviewed=attach_review(data,self.root)
        self.assertEqual(data,before)
        self.assertEqual({k:v for k,v in reviewed.items() if k!='post_run_review'},before)
        self.assertEqual(files,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        findings=[f for f in reviewed['post_run_review']['findings'] if f['kind']=='reported_failure_location']
        self.assertEqual(len(findings),3)
        self.assertTrue(all('not a proven cause' in f['next_check'] for f in findings))
        self.assertNotIn('approval_granted',reviewed['post_run_review'])


if __name__=='__main__':unittest.main()

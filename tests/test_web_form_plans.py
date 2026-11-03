"""Offline form-binding checks: wrong controls cannot become approved login actions."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.project_tools import ProjectTools
from integrations.web.form_plans import validate_login_plan


class LoginPlanTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.tools = ProjectTools(str(self.root))
        self.quote = 'Valid tester password123 succeeds. Invalid invalid wrong fails with an error. Empty fields require validation.'
        source = self.root / 'requirements.md'
        source.write_text(self.quote + '\n', encoding='utf-8')
        self.reference = {'file': 'requirements.md', 'start_line': 1, 'end_line': 1,
                          'quote': self.quote, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        self.snapshot = {'status': 'inspected', 'url': 'https://example.test/#forms',
            'pinned_address': '1.1.1.1', 'forms_may_be_truncated': False,
            'fields_may_be_truncated': False, 'buttons_may_be_truncated': False,
            'forms': [{'index': 1, 'id': 'login', 'id_unique': True}],
            'fields': [self.field(1, 'username', 'text'), self.field(2, 'password', 'password')],
            'buttons': [{'index': 1, 'tag': 'button', 'type': 'submit', 'name': 'Login',
                'form_index': 1, 'in_form': True, 'disabled': False, 'aria_disabled': False,
                'name_in_form_unique': True}]}
        self.plan = {'inspection_file': 'inspection.json', 'inspection_sha256': '',
            'url': self.snapshot['url'], 'pinned_address': '1.1.1.1',
            'form_index': 1, 'username_index': 1, 'password_index': 2, 'submit_index': 1,
            'cases': [self.case('LOGIN-1', 'tester', 'password123', 'success'),
                      self.case('LOGIN-2', 'invalid', 'wrong', 'error'),
                      self.case('LOGIN-3', '', '', 'required')]}
        self.save()

    @staticmethod
    def field(index, identity, kind):
        return {'index': index, 'id': identity, 'id_unique': True, 'tag': 'input',
                'type': kind, 'form_index': 1, 'disabled': False,
                'aria_disabled': False, 'read_only': False}

    def case(self, identity, username, password, outcome):
        return {'id': identity, 'title': 'Selected login requirement',
                'source_refs': [copy.deepcopy(self.reference)],
                'steps': ['Use the selected form and submit the requirement data.'],
                'expected_results': ['Observe the requirement outcome.'],
                'credentials': {'username': username, 'password': password}, 'outcome': outcome}

    def save(self):
        path = self.root / 'inspection.json'
        path.write_text(json.dumps(self.snapshot), encoding='utf-8')
        self.plan['inspection_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

    def check(self):
        return validate_login_plan(self.tools, self.plan)

    def test_three_cases_bind_without_execution_or_approval(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(self.tools, 'run_command', side_effect=AssertionError('No execution')) as run:
            result = self.check()
        run.assert_not_called()
        self.assertEqual(result['checks']['inspection_binding'], 'Y')
        self.assertEqual(result['checks']['source_traceability'], 'Y')
        self.assertEqual(result['status'], 'P')
        self.assertEqual(result['execution_status'], 'not_run')
        self.assertFalse(result['approval_granted'])
        self.assertEqual(len(result['cases']), 3)
        self.assertTrue(all('credentials' not in case for case in result['cases']))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_foreign_or_unowned_control_is_rejected(self):
        for key, position in (('fields', 0), ('fields', 1), ('buttons', 0)):
            for owner in (None, 2, True):
                with self.subTest(key=key, position=position, owner=owner):
                    snapshot = copy.deepcopy(self.snapshot)
                    self.snapshot[key][position]['form_index'] = owner
                    self.save()
                    with self.assertRaises(ValueError): self.check()
                    self.snapshot = snapshot

    def test_duplicate_or_missing_indices_are_rejected(self):
        for key, index in (('fields', 0), ('buttons', 0), ('forms', 0)):
            for duplicate in (False, True):
                with self.subTest(key=key, duplicate=duplicate):
                    original = copy.deepcopy(self.snapshot)
                    if duplicate: self.snapshot[key].append(copy.deepcopy(self.snapshot[key][index]))
                    else: self.snapshot[key].pop(index)
                    self.save()
                    with self.assertRaises(ValueError): self.check()
                    self.snapshot = original

    def test_unknown_boolean_or_nonpositive_plan_indices_are_rejected(self):
        for key in ('form_index', 'username_index', 'password_index', 'submit_index'):
            for value in (True, 0, -1, 99, '1'):
                with self.subTest(key=key, value=value):
                    plan = {**self.plan, key: value}
                    with self.assertRaises(ValueError): validate_login_plan(self.tools, plan)

    def test_disabled_readonly_or_wrong_type_fields_are_rejected(self):
        for position, change in ((0, {'type': 'password'}), (1, {'type': 'text'}),
                                 (0, {'disabled': True}), (1, {'read_only': True}),
                                 (0, {'aria_disabled': True}), (0, {'disabled': None}),
                                 (1, {'id_unique': False}), (0, {'id': ''})):
            with self.subTest(position=position, change=change):
                original = copy.deepcopy(self.snapshot)
                self.snapshot['fields'][position].update(change)
                self.save()
                with self.assertRaises(ValueError): self.check()
                self.snapshot = original

    def test_anonymous_or_duplicate_form_id_is_rejected(self):
        for change in ({'id': ''}, {'id_unique': False}):
            with self.subTest(change=change):
                self.snapshot['forms'][0].update(change)
                self.save()
                with self.assertRaises(ValueError): self.check()
                self.snapshot['forms'][0] = {'index': 1, 'id': 'login', 'id_unique': True}

    def test_submit_must_be_an_enabled_unambiguous_form_submitter(self):
        for change in ({'type': 'button'}, {'in_form': False}, {'disabled': True},
                       {'aria_disabled': True}, {'name': ''}, {'name_in_form_unique': False}):
            with self.subTest(change=change):
                original = copy.deepcopy(self.snapshot)
                self.snapshot['buttons'][0].update(change)
                self.save()
                with self.assertRaises(ValueError): self.check()
                self.snapshot = original

    def test_incomplete_or_legacy_inspection_requires_new_observations(self):
        for key in ('fields_may_be_truncated', 'buttons_may_be_truncated', 'forms_may_be_truncated'):
            for missing in (False, True):
                with self.subTest(key=key, missing=missing):
                    original = copy.deepcopy(self.snapshot)
                    if missing: self.snapshot.pop(key)
                    else: self.snapshot[key] = True
                    self.save()
                    with self.assertRaises(ValueError): self.check()
                    self.snapshot = original

    def test_stale_inspection_and_source_hashes_are_rejected(self):
        (self.root / 'inspection.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): self.check()
        self.save()
        (self.root / 'requirements.md').write_text('Changed requirement', encoding='utf-8')
        with self.assertRaises(ValueError): self.check()

    def test_http_private_pin_or_different_page_is_rejected(self):
        for change in ({'url': 'https://other.test'}, {'pinned_address': '8.8.8.8'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_login_plan(self.tools, {**self.plan, **change})
        for url, address in (('http://example.test', '1.1.1.1'), ('https://example.test', '127.0.0.1')):
            with self.subTest(url=url):
                self.snapshot.update(url=url, pinned_address=address)
                self.plan.update(url=url, pinned_address=address)
                self.save()
                with self.assertRaises(ValueError): self.check()

    def test_case_data_must_match_cited_source(self):
        self.plan['cases'][0]['credentials']['password'] = 'invented'
        with self.assertRaises(ValueError): self.check()
        self.plan['cases'][0]['credentials']['password'] = 'password123'
        self.plan['cases'][0]['source_refs'][0]['quote'] = 'Invented tester password123'
        with self.assertRaises(ValueError): self.check()

    def test_empty_and_invalid_case_shapes_are_rejected(self):
        for change in ({'credentials': {'username': '', 'password': ''}}, {'outcome': 'approved'},
                       {'credentials': {'username': 'tester', 'password': 'x' * 151}},
                       {'approved': True}, {'outcome': []}):
            with self.subTest(change=change):
                original = copy.deepcopy(self.plan['cases'][0])
                self.plan['cases'][0].update(change)
                with self.assertRaises(ValueError): self.check()
                self.plan['cases'][0] = original
        self.plan['cases'][2]['credentials']['username'] = 'tester'
        with self.assertRaises(ValueError): self.check()

    def test_case_count_duplicates_and_approval_injection_are_rejected(self):
        for cases in ([], self.plan['cases'] * 2, [self.plan['cases'][0]] * 2):
            with self.subTest(count=len(cases)), self.assertRaises(ValueError):
                validate_login_plan(self.tools, {**self.plan, 'cases': cases})
        with self.assertRaises(ValueError): validate_login_plan(self.tools, {**self.plan, 'approved': True})

    def test_inspection_replacement_during_source_check_is_rejected(self):
        from integrations.web import form_plans
        original = form_plans.validate_test_plan
        def replace(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.root / 'inspection.json').write_text('{}', encoding='utf-8')
            return result
        with patch.object(form_plans, 'validate_test_plan', side_effect=replace):
            with self.assertRaisesRegex(ValueError, 'during validation'): self.check()


if __name__ == '__main__': unittest.main()

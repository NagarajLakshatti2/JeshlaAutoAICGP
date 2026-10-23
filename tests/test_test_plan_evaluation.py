"""Execution-disclosure scoring; no hosted requests or app launches."""
import unittest
from evaluations.test_plan_live import _declares_not_run


class ExecutionDisclosureTests(unittest.TestCase):
    def test_recognizes_actual_live_disclaimer_and_normal_paraphrases(self):
        for value in ('Human review is pending, and this test has not been run.',
                      'Tests have not been executed.', 'Tests not run.',
                      '**Execution status:** `not_run`', 'No tests were run.',
                      'The test was not executed.', 'Tests are unexecuted.'):
            with self.subTest(value=value):self.assertTrue(_declares_not_run(value))

    def test_quoted_or_fenced_text_alone_is_not_a_narrative_disclosure(self):
        for value in ('> Tests not run.', '```text\nTests not run.\n```',
                      '~~~text\nThis test has not been run.\n~~~',
                      'The source says:\n> Execution: not run\nThe test passed.'):
            with self.subTest(value=value):self.assertFalse(_declares_not_run(value))

    def test_does_not_confuse_positive_execution_or_unrelated_words(self):
        for value in ('The test has been run.', 'Tests are running.',
                      'This is not runnable source.', 'The draft needs review.'):
            with self.subTest(value=value):self.assertFalse(_declares_not_run(value))

    def test_narrative_disclosure_can_follow_a_quoted_source(self):
        self.assertTrue(_declares_not_run('> Expected results from the source.\n\nThis test has not been run.'))

import unittest
from agent.history_intent import is_history_request

class HistoryIntentTests(unittest.TestCase):
    def test_personal_recency_is_local(self):
        for question in ("What was my latest message in this chat?", "What did I ask last time?", "Summarize our current conversation", "What was my previous question?"):
            with self.subTest(question=question):self.assertTrue(is_history_request(question))

    def test_external_recency_remains_external(self):
        for question in ("Find the latest Java documentation online", "What is the latest news?", "Search the web for our previous chat topic", "What is the current Java version?"):
            with self.subTest(question=question):self.assertFalse(is_history_request(question))

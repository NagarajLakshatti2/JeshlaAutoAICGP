import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.browser_activity import log_browser_event,_logger
from agent.provider_errors import ProviderError

class BrowserActivityTests(unittest.TestCase):
    def tearDown(self):
        import logging
        for name,logger in list(logging.Logger.manager.loggerDict.items()):
            if name.startswith("jeshla.browser.") and isinstance(logger,logging.Logger):
                for handler in logger.handlers[:]:handler.close();logger.removeHandler(handler)
        _logger.cache_clear()

    def test_metadata_log_excludes_private_session_and_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            error=ProviderError("groq","QUOTA_EXHAUSTED","private-token",status=429)
            self.assertTrue(log_browser_event("error",session="private-chat-title",error=error,root=folder))
            text=(Path(folder)/"outputs/logs/browser-activity.jsonl").read_text()
            value=json.loads(text)
            self.assertEqual(value["category"],"QUOTA_EXHAUSTED")
            self.assertEqual(value["http_status"],429)
            self.assertNotIn("private-token",text);self.assertNotIn("private-chat-title",text)
            self.assertEqual(len(value["chat_ref"]),16)
            self.tearDown()

    def test_logging_failure_does_not_break_ui(self):
        with patch("agent.browser_activity._logger",side_effect=OSError("denied")):
            self.assertFalse(log_browser_event("memory_viewed"))
        self.assertFalse(log_browser_event("untrusted-event-secret"))

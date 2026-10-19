"""Provider configuration display cannot leak credentials or issue requests."""
import json
import unittest
from unittest.mock import patch
from agent.interfaces.browser import BrowserBackend


class ProviderPanelTests(unittest.TestCase):
    def test_four_providers_return_metadata_only(self):
        backend=BrowserBackend.__new__(BrowserBackend)
        env={"GROQ_MODEL":"fixture-groq","GEMINI_MODEL":"fixture-gemini",
             "GROQ_API_KEY":"private-test-key","OPENROUTER_API_KEY":"private-test-key",
             "GOOGLE_AI_STUDEO_KEY":"private-test-key"}
        with patch.dict("os.environ",env,clear=True),patch("requests.Session.request",side_effect=AssertionError("No network")):
            for provider in ("groq","openrouter","gemini","ollama"):
                backend.provider=provider
                info=backend.provider_info()
                self.assertTrue(info["supported"])
                self.assertNotIn("private-test-key",json.dumps(info))
                self.assertEqual(info["key_present"],None if provider=="ollama" else True)
            backend.provider="groq"
            with patch.dict("os.environ",{},clear=True):
                self.assertFalse(backend.provider_info()["key_present"])
                self.assertEqual(backend.provider_info()["model"],"")

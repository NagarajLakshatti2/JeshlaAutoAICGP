"""Provider-boundary tests for the optional AutoGen integration."""
import unittest
from integrations.autogen.provider_config import provider_config
from agent.providers.errors import ProviderError


class AutoGenProviderConfigTests(unittest.TestCase):
    def test_hosted_providers_use_compatible_endpoints_and_require_keys(self):
        cases = {
            "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "https://openrouter.ai/api/v1"),
            "groq": ("GROQ_API_KEY", "GROQ_MODEL", "https://api.groq.com/openai/v1"),
            "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        }
        for provider, (key_name, model_name, endpoint) in cases.items():
            with self.subTest(provider=provider):
                with self.assertRaises(ProviderError): provider_config(provider, {})
                config = provider_config(provider, {key_name: "private-test-key", model_name: "test-model"})
                self.assertEqual(config["base_url"], endpoint)
                self.assertEqual(config["model"], "test-model")
                self.assertEqual(config["api_key"], "private-test-key")

    def test_ollama_is_loopback_only(self):
        config = provider_config("ollama", {"OLLAMA_MODEL": "local-model", "OLLAMA_URL": "http://127.0.0.1:11434/api/chat"})
        self.assertEqual(config["base_url"], "http://127.0.0.1:11434/v1")
        with self.assertRaises(ProviderError):
            provider_config("ollama", {"OLLAMA_URL": "https://remote.example/api/chat"})

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ProviderError): provider_config("autogen", {})


if __name__ == "__main__": unittest.main()

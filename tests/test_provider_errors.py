"""Safe failure categories and retry policy with fake responses only."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import requests
from agent.provider_errors import ProviderError,response_error,request_model


def response(status,code="",message="",headers=None):
    return SimpleNamespace(status_code=status,headers=headers or {},json=lambda:{"error":{"code":code,"message":message}})


class ProviderErrorTests(unittest.TestCase):
    def test_http_categories_and_redaction(self):
        for status,code,expected in [(401,"","AUTHENTICATION"),(403,"","ACCESS_DENIED"),(402,"","BILLING"),(404,"","MODEL_OR_ENDPOINT"),(400,"tool_use_failed","TOOL_OUTPUT"),(400,"json_validate_failed","TOOL_OUTPUT"),(400,"context_length_exceeded","CONTEXT_LIMIT"),(422,"","INVALID_REQUEST"),(413,"","REQUEST_TOO_LARGE"),(429,"insufficient_quota","QUOTA_EXHAUSTED"),(429,"","RATE_LIMIT"),(503,"","PROVIDER_TEMPORARY"),(302,"","REDIRECT_BLOCKED")]:
            error=response_error("groq",response(status,code,"private-token-content"))
            self.assertEqual(error.category,expected)
            self.assertEqual(error.status,status)
            self.assertNotIn("private-token",str(error))

    def request(self):
        return request_model("groq","https://example.invalid",headers={},json={},timeout=(10,90))

    def test_short_rate_limit_recovers(self):
        with patch("requests.post",side_effect=[response(429,headers={"Retry-After":"0"}),response(200)]) as post,patch("agent.provider_errors.time.sleep"):
            self.assertEqual(self.request().status_code,200)
            self.assertEqual(post.call_count,2)

    def test_quota_and_long_unknown_delays_do_not_retry(self):
        for item in [response(429,"insufficient_quota"),response(429,headers={"Retry-After":"100"}),response(429),response(401),response(400,"tool_use_failed")]:
            with patch("requests.post",return_value=item) as post:
                with self.assertRaises(ProviderError):self.request()
                self.assertEqual(post.call_count,1)

    def test_temporary_service_failure_bounded(self):
        with patch("requests.post",return_value=response(503)) as post,patch("agent.provider_errors.time.sleep"),patch.dict("os.environ",{"GROQ_CONNECT_ATTEMPTS":"2"}):
            with self.assertRaises(ProviderError) as caught:self.request()
            self.assertEqual(post.call_count,2)
            self.assertEqual(caught.exception.attempts,2)

    def test_proxy_and_timeout_explanations(self):
        for exception,category in [(requests.exceptions.ProxyError("secret-proxy"),"PROXY"),(requests.exceptions.ReadTimeout(),"RESPONSE_TIMEOUT"),(requests.exceptions.SSLError(),"TLS_CERTIFICATE")]:
            with patch("requests.post",side_effect=exception) as post:
                with self.assertRaises(ProviderError) as caught:self.request()
                self.assertEqual(caught.exception.category,category)
                self.assertNotIn("secret-proxy",str(caught.exception))
                self.assertEqual(post.call_count,1)

    def test_invalid_config_fails_before_network(self):
        with patch.dict("os.environ",{"GROQ_CONNECT_ATTEMPTS":"invalid"}),patch("requests.post") as post:
            with self.assertRaises(ProviderError) as caught:self.request()
            self.assertEqual(caught.exception.category,"CONFIGURATION")
            post.assert_not_called()

    def test_malformed_response_is_safe(self):
        from agent.provider_errors import read_model_json
        for fake in [SimpleNamespace(json=lambda:[]),SimpleNamespace(json=lambda:{"error":{"message":"secret"}})]:
            with self.assertRaises(ProviderError) as caught:read_model_json(fake,"groq")
            self.assertNotIn("secret",str(caught.exception))

    def test_text_clients_use_shared_diagnostics(self):
        from agent import llm_client as llm
        for client in [llm.call_groq,llm.call_openrouter,llm.call_ollama]:
            with patch.dict("os.environ",{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","OPENROUTER_BUDGET_MODEL":"","GROQ_BUDGET_MODEL":""}),patch.object(llm,"OPENROUTER_API_KEY","offline-fake"),patch("requests.post",return_value=response(401)) as post:
                with self.assertRaises(ProviderError) as caught:client("offline test")
                self.assertEqual(caught.exception.category,"AUTHENTICATION")
                self.assertEqual(post.call_count,1)


class RateWindowTests(unittest.TestCase):
    def test_billing_upgrade_url_does_not_turn_minute_limit_into_quota(self):
        item=response(429,"rate_limit_exceeded","Tokens per minute (TPM) exceeded. Upgrade at https://console.example/settings/billing?secret=value")
        error=response_error("groq",item)
        self.assertEqual(error.category,"RATE_LIMIT")
        self.assertNotIn("secret",str(error))

    def test_daily_window_remains_quota(self):
        for message in ["Tokens per day (TPD) exceeded", "Daily limit exceeded"]:
            self.assertEqual(response_error("groq",response(429,message=message)).category,"QUOTA_EXHAUSTED")

    def test_minute_error_without_explicit_short_delay_is_not_retried(self):
        item=response(429,"rate_limit_exceeded","Tokens per minute reached. https://console.example/billing")
        with patch("requests.post",return_value=item) as post:
            with self.assertRaises(ProviderError) as caught:
                request_model("groq","https://example.invalid",headers={},json={},timeout=(10,90))
        self.assertEqual(caught.exception.category,"RATE_LIMIT")
        self.assertEqual(post.call_count,1)

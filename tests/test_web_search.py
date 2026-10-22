"""Search adapter bounds, failure honesty and legacy import compatibility."""
import unittest
from unittest.mock import Mock,patch
from agent.tools.web_search import web_search


class WebSearchTests(unittest.TestCase):
    def test_one_engine_attempt_returns_only_public_url_rows(self):
        client=Mock()
        client.text.return_value=[{"href":"https://official.test/rules","body":"Rule"},{"href":"file:///private"}]
        with patch("ddgs.DDGS",return_value=client) as constructor:
            result=web_search("public documentation")
        constructor.assert_called_once_with(timeout=5)
        client.text.assert_called_once_with("public documentation",max_results=5,backend="duckduckgo")
        self.assertEqual(len(result["results"]),1)
        self.assertIn("have not been read",result["note"])

    def test_engine_failure_uses_only_one_changed_backend_and_hides_details(self):
        client=Mock();client.text.side_effect=RuntimeError("SECRET raw transport failure")
        with patch("ddgs.DDGS",return_value=client):result=web_search("public documentation")
        self.assertEqual(client.text.call_count,2)
        self.assertEqual([call.kwargs["backend"] for call in client.text.call_args_list],["duckduckgo","brave"])
        self.assertIn("error",result);self.assertNotIn("SECRET",str(result))
        self.assertEqual(result["task_status"],"incomplete")

    def test_legacy_conversation_import_still_uses_packaged_adapter(self):
        from agent.conversation import web_search as legacy
        self.assertIs(legacy,web_search)


    def test_first_empty_engine_recovers_with_one_alternate(self):
        client=Mock();client.text.side_effect=[[],[{"href":"https://official.test/rules","body":"Rule"}]]
        with patch("ddgs.DDGS",return_value=client):result=web_search("official rules")
        self.assertEqual(client.text.call_count,2)
        self.assertEqual(result["results"][0]["url"],"https://official.test/rules")
        self.assertEqual(result["attempts"],[{"backend":"duckduckgo","status":"empty"},{"backend":"brave","status":"results"}])

    def test_first_failure_can_recover_without_claiming_pages_were_read(self):
        client=Mock();client.text.side_effect=[RuntimeError("SECRET"),[{"href":"https://official.test/rules"}]]
        with patch("ddgs.DDGS",return_value=client):result=web_search("official rules")
        self.assertNotIn("error",result)
        self.assertEqual(result["attempts"][0]["status"],"unavailable")
        self.assertIn("have not been read",result["note"])
        self.assertNotIn("SECRET",str(result))

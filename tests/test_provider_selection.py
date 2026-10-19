"""Per-request choices never alter a concurrent/default provider."""
import concurrent.futures,unittest
from unittest.mock import patch
from agent.providers.selection import current_provider,provider_selection
from agent.interfaces.browser import BrowserBackend

class ProviderSelectionTests(unittest.TestCase):
    def test_context_restores_and_does_not_leak_to_threads(self):
        self.assertEqual(current_provider('ollama'),'ollama')
        with provider_selection('groq'):
            self.assertEqual(current_provider('ollama'),'groq')
            with concurrent.futures.ThreadPoolExecutor() as pool:self.assertEqual(pool.submit(current_provider,'ollama').result(),'ollama')
            with self.assertRaises(RuntimeError):
                with provider_selection('gemini'):raise RuntimeError('fixture')
            self.assertEqual(current_provider('ollama'),'groq')
        self.assertEqual(current_provider('ollama'),'ollama')

    def test_browser_request_selection_is_scoped(self):
        backend=BrowserBackend.__new__(BrowserBackend)
        info={'supported':True,'model':'fixture','local':False,'key_present':True}
        with patch.object(backend,'provider_info',return_value=info),patch.object(backend,'submit',side_effect=lambda *args:current_provider('ollama')):
            self.assertEqual(backend.submit_selected('chat','question','groq'),'groq')
        self.assertEqual(current_provider('ollama'),'ollama')

    def test_text_dispatch_uses_selected_provider(self):
        from agent.providers import text
        with patch.dict(text.PROVIDERS,{'groq':lambda *args,**kwargs:'selected'}):
            with provider_selection('groq'):self.assertEqual(text.call_llm('fixture'),'selected')

    def test_native_tool_dispatch_uses_selected_provider(self):
        from tests.test_tool_llm import AdapterTests
        data={'choices':[{'finish_reason':'stop','message':{'content':'selected hosted response'}}]}
        with provider_selection('groq'):
            result,payload=AdapterTests().run_request('ollama',data)
        self.assertEqual(result['content'],'selected hosted response')
        self.assertEqual(payload['json']['model'],'test-model')
        self.assertIn('max_completion_tokens',payload['json'])

"""Legacy imports must reference the same live policy implementation."""
import importlib
import unittest
from unittest.mock import patch

class PolicyCompatibilityTests(unittest.TestCase):
    def test_legacy_module_and_callable_identity(self):
        for old,new,member in (("agent.history_intent","agent.policies.routing","is_history_request"),("agent.tool_policy","agent.policies.tool_registry","validate_conversation_registry")):
            with self.subTest(module=old):
                legacy=importlib.import_module(old);canonical=importlib.import_module(new)
                self.assertIs(legacy,canonical)
                self.assertIs(getattr(legacy,member),getattr(canonical,member))

    def test_patch_on_old_path_updates_validator_globals(self):
        legacy=importlib.import_module("agent.tool_policy")
        canonical=importlib.import_module("agent.policies.tool_registry")
        original=canonical.CONVERSATION_ACTIONS
        with patch("agent.tool_policy.CONVERSATION_ACTIONS",frozenset({"fixture"})):
            canonical.validate_conversation_registry([{"function":{"name":"fixture"}}])
            self.assertEqual(legacy.CONVERSATION_ACTIONS,frozenset({"fixture"}))
        self.assertIs(canonical.CONVERSATION_ACTIONS,original)

class ProviderCompatibilityTests(unittest.TestCase):
    def test_provider_module_and_member_identity(self):
        cases=(("provider_errors","errors","ProviderError"),("model_budget","budget","apply_model_budget"),("llm_client","text","call_llm"),("tool_llm","tools","call_tool_messages"),("gemini_config","gemini","credentials"))
        for old,new,member in cases:
            with self.subTest(module=old):
                legacy=importlib.import_module("agent."+old)
                canonical=importlib.import_module("agent.providers."+new)
                self.assertIs(legacy,canonical)
                self.assertIs(getattr(legacy,member),getattr(canonical,member))

    def test_old_budget_patch_is_used_by_canonical_transport(self):
        from agent.providers.errors import request_model
        from agent.provider_errors import ProviderError as legacy_error
        from agent.providers.errors import ProviderError as canonical_error
        self.assertIs(legacy_error,canonical_error)
        error=legacy_error("fixture","CONFIGURATION","Fixture failure.")
        with patch("agent.model_budget.apply_model_budget",side_effect=error) as budget,patch("requests.post") as post:
            with self.assertRaises(canonical_error):
                request_model("groq","https://example.invalid",headers={},json={},timeout=(10,90))
            budget.assert_called_once();post.assert_not_called()

class RuntimeCompatibilityTests(unittest.TestCase):
    def test_shared_runtime_objects_keep_identity(self):
        cases=(("chat_runtime","turns","process_turn_lock"),("context_summary","summaries","compact_context"),("summary_model","summary_model","call_summary_messages"),("runtime_context","context","approval_handler"),("conversation","conversation","answer_question"))
        for old,new,member in cases:
            with self.subTest(module=old):
                legacy=importlib.import_module("agent."+old)
                canonical=importlib.import_module("agent.runtime."+new)
                self.assertIs(legacy,canonical)
                self.assertIs(getattr(legacy,member),getattr(canonical,member))

    def test_legacy_approval_scope_reaches_canonical_context(self):
        from agent.runtime_context import local_action_handler
        from agent.runtime.context import approval_handler
        before=approval_handler.get();handler=lambda *args:False
        with local_action_handler(handler):self.assertIs(approval_handler.get(),handler)
        self.assertIs(approval_handler.get(),before)

class StorageActionCompatibilityTests(unittest.TestCase):
    def test_old_and_new_store_classes_share_identity(self):
        for old,new,member in (("agent.chat_catalog","agent.storage.chats","ChatCatalog"),("agent.local_action_receipts","agent.actions.receipts","LocalActionReceipts"),("agent.browser_actions","agent.actions.browser","BrowserActions")):
            with self.subTest(module=old):
                legacy=importlib.import_module(old);canonical=importlib.import_module(new)
                self.assertIs(legacy,canonical)
                self.assertIs(getattr(legacy,member),getattr(canonical,member))

    def test_action_exceptions_and_legacy_patches_stay_shared(self):
        from agent.actions import receipts,browser
        from agent.local_action_receipts import ActionBlocked
        self.assertIs(ActionBlocked,receipts.ActionBlocked)
        self.assertIs(browser.ActionBlocked,receipts.ActionBlocked)
        with patch("agent.local_action_receipts.ACTIONS",frozenset({"fixture"})):
            self.assertEqual(receipts.ACTIONS,frozenset({"fixture"}))

class BrowserInterfaceCompatibilityTests(unittest.TestCase):
    def test_legacy_browser_factory_and_root_share_identity(self):
        legacy=importlib.import_module("agent.browser_backend")
        canonical=importlib.import_module("agent.interfaces.browser")
        self.assertIs(legacy,canonical)
        self.assertIs(legacy.BrowserBackend,canonical.BrowserBackend)
        self.assertEqual(legacy.ROOT,canonical.ROOT)
        marker=object()
        with patch("agent.browser_backend.BrowserBackend",return_value=marker) as constructor:
            self.assertIs(canonical.make_browser_backend(),marker)
            constructor.assert_called_once_with()

class ConsoleInterfaceCompatibilityTests(unittest.TestCase):
    def test_legacy_main_passes_current_dependencies_to_console_adapter(self):
        import ast
        from pathlib import Path
        from unittest.mock import Mock
        source=(Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8")
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=="main")
        graph=object();root=object();session=Mock();restore=Mock();timer=Mock()
        scope={"graph":graph,"PROJECT_ROOT":root,"LLM_PROVIDER":"fixture","session_config":session,"restore_session":restore,"timer":timer}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"legacy-console","exec"),scope)
        with patch("agent.interfaces.console.run_console",return_value="fixture") as run:
            self.assertEqual(scope["main"](),"fixture")
        run.assert_called_once_with(graph=graph,project_root=root,provider="fixture",session_config=session,restore_session=restore,timer_factory=timer)

"""Request-local AutoGen routing tests; no provider or worker is started."""
import unittest
from unittest.mock import patch

from integrations.autogen.selection import agent_mode_selection, current_agent_mode


class AutoGenModeTests(unittest.TestCase):
    def test_mode_is_request_local_and_restored(self):
        self.assertEqual(current_agent_mode(), "autogen")
        with agent_mode_selection("autogen"):
            self.assertEqual(current_agent_mode(), "autogen")
        self.assertEqual(current_agent_mode(), "autogen")

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            with agent_mode_selection("unknown"):
                pass

    def test_provider_tool_adapter_is_used_only_in_autogen_mode(self):
        from agent.providers.tools import call_tool_messages
        result = {"content": "answer", "tool_calls": []}
        with patch("integrations.autogen.selection.current_agent_mode", return_value="autogen"), \
             patch("integrations.autogen.bridge.call_tool_messages", return_value=result) as adapter:
            self.assertIs(call_tool_messages([{"role": "user", "content": "hello"}], []), result)
        adapter.assert_called_once()


    def test_worker_enables_native_json_mode_for_supported_provider(self):
        import asyncio
        import sys
        import types
        from types import SimpleNamespace
        from integrations.autogen.worker import _run
        from integrations.autogen import provider_config

        captured = {}
        class FakeClient:
            def __init__(self, **kwargs):
                captured["client_kwargs"] = kwargs
            async def create(self, *args, **kwargs):
                captured["create_kwargs"] = kwargs
                return SimpleNamespace(finish_reason="stop")
            async def close(self): pass

        class FakeAssistant:
            def __init__(self, name, model_client, **kwargs): self.client = model_client
            async def run(self, task):
                await self.client.create([], json_output=False)
                return SimpleNamespace(messages=[SimpleNamespace(content='{"ok":true}')])

        agentchat = types.ModuleType("autogen_agentchat")
        agentchat.__path__ = []
        agents = types.ModuleType("autogen_agentchat.agents")
        agents.AssistantAgent = FakeAssistant
        ext = types.ModuleType("autogen_ext")
        ext.__path__ = []
        models = types.ModuleType("autogen_ext.models")
        models.__path__ = []
        openai_models = types.ModuleType("autogen_ext.models.openai")
        openai_models.OpenAIChatCompletionClient = FakeClient
        modules = {"autogen_agentchat": agentchat, "autogen_agentchat.agents": agents,
                   "autogen_ext": ext, "autogen_ext.models": models,
                   "autogen_ext.models.openai": openai_models}
        request = {"provider": "groq", "messages": [{"role": "user", "content": "Return JSON"}],
                   "tools": [], "max_tokens": 128, "json_mode": True}
        with patch.dict(sys.modules, modules), \
             patch.object(provider_config, "provider_config",
                          return_value={"model": "fixture", "api_key": "fixture", "base_url": "https://fixture.invalid"}):
            result = asyncio.run(_run(request))
        self.assertEqual(result["content"], '{"ok":true}')
        self.assertIs(captured["client_kwargs"]["model_info"]["json_output"], True)
        self.assertIs(captured["create_kwargs"]["json_output"], True)
    def test_langgraph_tool_request_uses_native_adapter_and_skips_autogen(self):
        from agent.providers.tools import call_tool_messages
        native_result = {"content": "", "tool_calls": [{"id": "fixture", "type": "function",
            "function": {"name": "list_files", "arguments": "{}"}}]}
        tool = {"type": "function", "function": {"name": "list_files",
            "parameters": {"type": "object", "properties": {}}}}
        with patch("integrations.autogen.selection.current_agent_mode", return_value="langgraph"), \
             patch("agent.providers.tools.LLM_PROVIDER", "groq"), \
             patch("agent.providers.fallback.call_with_fallback",
                   side_effect=lambda _provider, invoke, **_kwargs: invoke("groq")), \
             patch("agent.providers.fallback.messages_for_provider",
                   side_effect=lambda messages, *_args, **_kwargs: messages), \
             patch("agent.providers.selection.current_provider", return_value="groq"), \
             patch("agent.providers.tools._call_tool_provider", return_value=native_result) as native, \
             patch("integrations.autogen.bridge.call_tool_messages") as autogen_adapter:
            result = call_tool_messages([{"role": "user", "content": "List files"}], [tool])
        self.assertIs(result, native_result)
        native.assert_called_once()
        autogen_adapter.assert_not_called()
    def test_langgraph_mode_keeps_json_request_on_native_provider_adapter(self):
        from agent.providers.text import call_llm_messages
        from unittest.mock import Mock
        native = Mock(return_value="{\"ok\":true}")
        with patch("integrations.autogen.selection.current_agent_mode", return_value="langgraph"), \
             patch("agent.providers.text.LLM_PROVIDER", "groq"), \
             patch("agent.providers.text.PROVIDERS", {"groq": native}), \
             patch("agent.providers.fallback.call_with_fallback",
                   side_effect=lambda _provider, invoke, **_kwargs: invoke("groq")), \
             patch("agent.providers.tools.call_tool_messages") as autogen_adapter:
            result = call_llm_messages([{"role": "user", "content": "Return JSON"}], json_mode=True)
        self.assertEqual(result, "{\"ok\":true}")
        self.assertIs(native.call_args.kwargs["json_mode"], True)
        autogen_adapter.assert_not_called()
    def test_text_json_mode_uses_selected_autogen_adapter(self):
        from agent.providers.text import call_llm_messages
        result = {"content": "{}", "tool_calls": []}
        with patch("integrations.autogen.selection.current_agent_mode", return_value="autogen"), \
             patch("agent.providers.tools.call_tool_messages", return_value=result) as adapter:
            self.assertEqual(call_llm_messages([{"role": "user", "content": "Return JSON"}],
                                               json_mode=True), "{}")
        self.assertIs(adapter.call_args.kwargs["json_mode"], True)
    def test_autogen_json_mode_is_forwarded_to_worker(self):
        from integrations.autogen.bridge import call_tool_messages
        with patch("agent.providers.fallback.call_with_fallback",
                   side_effect=lambda _provider, invoke, **_kwargs: invoke("groq")), \
             patch("agent.providers.selection.current_provider", return_value="groq"), \
             patch("integrations.autogen.bridge._worker.request",
                   return_value={"content": "{}", "tool_calls": []}) as request:
            call_tool_messages([{"role": "user", "content": "Return JSON"}], [],
                               max_tokens=128, json_mode=True)
        self.assertIs(request.call_args.args[1]["json_mode"], True)

    def test_native_json_mode_is_limited_to_groq_and_gemini(self):
        from integrations.autogen.worker import _supports_native_json_output
        self.assertTrue(_supports_native_json_output("groq", True))
        self.assertTrue(_supports_native_json_output("gemini", True))
        self.assertFalse(_supports_native_json_output("openrouter", True))
        self.assertFalse(_supports_native_json_output("groq", False))
    def test_console_selects_autogen_by_default_and_langgraph_when_requested(self):
        import tempfile
        from contextlib import contextmanager
        from pathlib import Path
        from types import SimpleNamespace
        from agent.interfaces.console import run_console

        class Catalog:
            def __init__(self, *args, **kwargs): pass
            def register(self, *args, **kwargs): pass

        @contextmanager
        def timer_factory(_label):
            yield SimpleNamespace(observe=lambda _result: None)

        def run_once(argv, expected_mode):
            observed = []
            def fake_turn(*args):
                observed.append(current_agent_mode())
                return {"final_answer": "ok", "route": "direct", "history": "", "summary": "", "notices": []}
            with tempfile.TemporaryDirectory() as folder, \
                 patch("sys.argv", argv), \
                 patch("agent.chat_catalog.ChatCatalog", Catalog), \
                 patch("agent.chat_catalog.choose_chat", return_value="default"), \
                 patch("agent.interfaces.terminal_input.configure_input"), \
                 patch("agent.interfaces.terminal_input.read_message", side_effect=["Hi", "EXIT"]), \
                 patch("agent.chat_runtime.run_turn", side_effect=fake_turn), \
                 patch("builtins.print"):
                run_console(graph=object(), project_root=Path(folder), provider="groq",
                            session_config=lambda *args: {},
                            restore_session=lambda *args: ({}, "", "", ""),
                            timer_factory=timer_factory)
            self.assertEqual(observed, [expected_mode])

        run_once(["agent"], "autogen")
        run_once(["agent", "--agent-mode", "langgraph"], "langgraph")
if __name__ == "__main__":
    unittest.main()

"""Real SQLite restart/isolation plus scripted provider limits; no network/actions."""
from contextlib import closing, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import TypedDict
import unittest
from unittest.mock import Mock, patch

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.runtime.conversation import answer_question
from agent.runtime.continuations import make_ledger, validate_ledger, progress_scope, command
from agent.runtime.long_answers import compose_long_answer
from agent.runtime.turns import run_turn
from agent.storage.answer_continuations import AnswerContinuations
from agent.storage.chats import ChatCatalog
from agent.providers.errors import ProviderError
from agent.providers.selection import provider_selection,current_provider
from tests.test_named_sessions import config as session_config


class State(TypedDict, total=False):
    question: str
    route: str
    answer: str
    task_status: str
    execution_outcome: str
    answer_available: bool
    history: str
    summary: str
    summary_turns: int
    summary_retry_at: float
    previous_exchange: dict
    previous_response_status: dict
    conversation_session: str


class ScriptedSections:
    def __init__(self, stop=None, bad=None, crash=False):
        self.stop = stop; self.bad = bad; self.crash = crash; self.ids = []; self.providers = []; self.outlines = 0; self.initial = 0
        self.plan = {"mode": "answer", "title": "A topic guide", "scope": "A bounded general explanation.", "sections": [
            {"title": "Foundations", "purpose": "Explain the basics"}, {"title": "Rules", "purpose": "Explain the rules"},
            {"title": "Pitfalls", "purpose": "Explain common mistakes"}]}

    def __call__(self, messages, specs):
        if not specs:
            self.initial += 1
            raise ProviderError("openrouter", "OUTPUT_LIMIT", "Scripted output boundary")
        name = specs[0]["function"]["name"]
        if name == "submit_answer_outline":
            self.outlines += 1; value = self.plan
        elif name == "submit_answer_section":
            prompt = next(message["content"] for message in reversed(messages) if "Section assignment: " in message.get("content", ""))
            assignment = json.loads(prompt.split("Section assignment: ", 1)[1])
            identity = assignment["assigned_section_id"]; self.ids.append(identity); self.providers.append(current_provider("openrouter"))
            if identity == self.stop:
                if self.crash: raise KeyboardInterrupt("Scripted interruption after a durable prefix")
                raise ProviderError("gemini", "RATE_LIMIT", "Scripted end-of-provider-chain quota", status=429)
            value = {"section_id": identity, "content": "Complete unique explanation for " + identity + ".", "covered_points": [identity]}
            if "complete" in specs[0]["function"]["parameters"]["properties"]: value["complete"] = True
            if self.bad is not None: value = self.bad(identity, value)
        else: raise AssertionError("Only registered text-data functions may be offered")
        return {"role": "assistant", "tool_calls": [{"id": "data", "function": {"name": name, "arguments": json.dumps(value)}}]}


class ContinuationTests(unittest.TestCase):
    question = "Explain a long topic."

    def setUp(self):
        env = patch.dict(os.environ, {"LLM_FALLBACK_ENABLED": "true", "LLM_FALLBACK_ORDER": "openrouter,groq,gemini",
            "AI_LONG_ANSWERS_ENABLED": "true", "AI_LONG_ANSWER_MAX_CALLS": "8", "AI_LONG_ANSWER_MAX_SECTIONS": "3",
            "AI_LONG_ANSWER_MAX_CHARS": "60000", "AI_CHAT_MAX_CONVERSATION_CHARS": "36000",
            "AI_TECHNICAL_VERIFICATION": "off", "AI_SUMMARY_THRESHOLD_CHARS": "100000"})
        env.start(); self.addCleanup(env.stop)
        quiet = redirect_stdout(io.StringIO()); quiet.__enter__(); self.addCleanup(quiet.__exit__, None, None, None)
        provider = provider_selection("openrouter"); provider.__enter__(); self.addCleanup(provider.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.catalog = ChatCatalog(self.root / "chats.sqlite3", "u", "p"); self.catalog.register("a")
        self.config = session_config("a", "u", "p")
        self.scope = hashlib.sha256(self.config["configurable"]["thread_id"].encode()).hexdigest()
        self.store = AnswerContinuations(self.root / "outputs/memory/answer_continuations.sqlite3")
        self.source_tools = Mock()
        self.source_tools.root = "fixture"

    def graph(self, connection, model):
        builder = StateGraph(State)
        def answer(state):
            result = answer_question({**state, "route": "direct"}, model=model, tools=self.source_tools,
                project_root=".", document_search=Mock(side_effect=AssertionError("No source work")))
            return {**result, "route": "direct"}
        builder.add_node("answer", answer); builder.add_edge(START, "answer"); builder.add_edge("answer", END)
        return builder.compile(checkpointer=SqliteSaver(connection))

    def turn(self, graph, question, model=None, config=None, catalog=None, session="a"):
        return run_turn(graph, config or self.config, catalog or self.catalog, session, question, self.root, continuation_model=model)

    def prefix(self, model=None):
        model = model or ScriptedSections(stop="section-2")
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            result = self.turn(self.graph(db, model), self.question)
        return result, model

    def test_quota_failure_keeps_only_complete_sections_and_saves_cursor(self):
        result, model = self.prefix()
        self.assertEqual(result["execution_outcome"], "partial")
        self.assertTrue(result["answer_available"])
        self.assertIn("## Foundations", result["answer"])
        self.assertNotIn("## Rules", result["answer"])
        self.assertIn("Type CONTINUE", result["answer"])
        saved = self.store.load(self.scope)
        self.assertEqual(len(saved["completed"]), 1); self.assertEqual(saved["published"], 1)
        self.assertEqual(saved["status"], "pending")
        self.assertEqual(len(self.catalog.transcript("a")), 1)

    def test_real_sqlite_restart_resumes_without_replanning_or_repeating_sections(self):
        self.prefix()
        model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, model)
            with patch.object(graph, "invoke", side_effect=AssertionError("Resume must not replay workflows")):
                result = self.turn(graph, "CONTINUE", model)
                consolidated = self.turn(graph, "FULL ANSWER", Mock(side_effect=AssertionError("Consolidation is local")))
        self.assertEqual(model.ids, ["section-2", "section-3"])
        self.assertEqual(model.outlines, 0); self.assertEqual(model.initial, 0)
        self.assertNotIn("## Foundations", result["answer"])
        self.assertIn("## Rules", result["answer"]); self.assertIn("## Pitfalls", result["answer"])
        self.assertEqual(result["execution_outcome"], "completed")
        for title in ("Foundations", "Rules", "Pitfalls"):
            self.assertEqual(consolidated["answer"].count("## " + title), 1)
        self.assertEqual(self.store.load(self.scope)["status"], "complete")
        self.assertEqual(len(self.catalog.transcript("a")), 3)
        self.source_tools.list_files.assert_not_called(); self.source_tools.read_file.assert_not_called()

    def test_sessions_users_and_memory_spaces_cannot_resume_each_others_answer(self):
        self.prefix()
        for session, user, space in (("b", "u", "p"), ("a", "other", "p"), ("a", "u", "other")):
            with self.subTest(session=session, user=user, space=space), closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
                catalog = ChatCatalog(self.root / "chats.sqlite3", user, space); catalog.register(session)
                graph = self.graph(db, Mock(side_effect=AssertionError("No cross-scope generation")))
                with patch.object(graph, "invoke", side_effect=AssertionError("Explicit control stays local")):
                    result = self.turn(graph, "CONTINUE ANSWER", config=session_config(session, user, space), catalog=catalog, session=session)
                self.assertIn("no saved text answer", result["answer"])
        self.assertEqual(len(self.store.load(self.scope)["completed"]), 1)

    def test_repeat_continue_after_completion_makes_no_model_or_graph_call(self):
        self.prefix(); model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, model); self.turn(graph, "continue", model)
            with patch.object(graph, "invoke", side_effect=AssertionError("No workflow replay")):
                result = self.turn(graph, "continue", Mock(side_effect=AssertionError("Already complete")))
        self.assertIn("already complete", result["answer"])
        self.assertNotIn("## Rules", result["answer"])

    def test_zero_completed_sections_keep_an_outline_without_inventing_content(self):
        result, _ = self.prefix(ScriptedSections(stop="section-1"))
        self.assertFalse(result["answer_available"])
        self.assertNotIn("## Foundations", result["answer"])
        self.assertEqual(self.store.load(self.scope)["completed"], [])
        model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            resumed = self.turn(self.graph(db, model), "continue", model)
        self.assertEqual(model.ids, ["section-1", "section-2", "section-3"])
        self.assertEqual(model.outlines, 0)
        self.assertEqual(resumed["execution_outcome"], "completed")

    def test_interruption_preserves_unpublished_prefix_and_never_regenerates_it(self):
        model = ScriptedSections(stop="section-2", crash=True)
        with self.assertRaises(KeyboardInterrupt): self.prefix(model)
        saved = self.store.load(self.scope)
        self.assertEqual(len(saved["completed"]), 1); self.assertEqual(saved["published"], 0)
        resumed = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            result = self.turn(self.graph(db, resumed), "CONTINUE ANSWER", resumed)
        self.assertEqual(resumed.ids, ["section-2", "section-3"])
        self.assertIn("## Foundations", result["answer"])
        self.assertEqual(result["answer"].count("## Foundations"), 1)

    def test_incomplete_code_or_false_completion_flag_is_held_back(self):
        for kind in ("code", "flag"):
            def bad(identity, value):
                if identity == "section-2":
                    if kind == "code": value["content"] = "```python\nprint('unfinished')"
                    else: value["complete"] = False
                return value
            with self.subTest(kind=kind):
                result, _ = self.prefix(ScriptedSections(bad=bad))
                self.assertIn("## Foundations", result["answer"])
                self.assertNotIn("unfinished", result["answer"])
                self.assertNotIn("## Rules", result["answer"])
                self.assertEqual(len(self.store.load(self.scope)["completed"]), 1)

    def test_repeated_section_content_is_not_appended_twice(self):
        def bad(identity, value):
            if identity == "section-2": value["content"] = "Complete unique explanation for section-1."
            return value
        result, _ = self.prefix(ScriptedSections(bad=bad))
        self.assertEqual(result["answer"].count("Complete unique explanation for section-1."), 1)
        self.assertNotIn("## Rules", result["answer"])

    def test_failed_section_save_does_not_publish_or_skip_the_uncommitted_section(self):
        model = ScriptedSections()
        original = AnswerContinuations.save
        def save(store, scope, value):
            if len(value["completed"]) == 2: raise sqlite3.OperationalError("Scripted save failure")
            return original(store, scope, value)
        with patch.object(AnswerContinuations, "save", save):
            result, _ = self.prefix(model)
        self.assertIn("CONTINUATION_SAVE", result["answer"])
        self.assertNotIn("## Rules", result["answer"])
        self.assertEqual(len(self.store.load(self.scope)["completed"]), 1)
        resumed = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            result = self.turn(self.graph(db, resumed), "continue", resumed)
        self.assertEqual(resumed.ids, ["section-2", "section-3"])
        self.assertNotIn("## Foundations", result["answer"])

    def test_cancel_and_new_question_stop_old_continuation_without_actions(self):
        self.prefix()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, ScriptedSections())
            with patch.object(graph, "invoke", side_effect=AssertionError("Cancel must stay local")):
                result = self.turn(graph, "CANCEL ANSWER")
            self.assertIn("cancelled", result["answer"]); self.assertIsNone(self.store.load(self.scope))
        self.prefix()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, Mock(return_value={"content": "Hello"}))
            result = self.turn(graph, "Hello")
        self.assertIsNone(self.store.load(self.scope))
        self.assertNotIn("Type CONTINUE", result["answer"])

    def test_bare_continue_without_text_progress_keeps_existing_workflow_handling(self):
        graph = Mock(); graph.get_state.return_value.values = {}
        graph.invoke.return_value = {"answer": "Existing pending workflow proposal", "route": "jira", "task_status": "incomplete"}
        result = self.turn(graph, "continue")
        graph.invoke.assert_called_once()
        self.assertEqual(result["answer"], "Existing pending workflow proposal")

    def test_corrupt_saved_progress_cannot_fall_into_action_routing(self):
        self.prefix()
        with closing(sqlite3.connect(self.store.path)) as db:
            db.execute("UPDATE answer_continuations SET payload=? WHERE scope=?", ('{"action":"create_file"}', self.scope))
            db.commit()
        graph = Mock(); graph.get_state.return_value.values = {}
        result = self.turn(graph, "continue", Mock(side_effect=AssertionError("No generation")))
        graph.invoke.assert_not_called()
        self.assertEqual(result["execution_outcome"], "blocked")

    def test_resume_controls_skip_automatic_summary_requests(self):
        self.prefix(); model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, model)
            graph.update_state(self.config, {"history": "Old history " * 2000, "summary_turns": 20})
            with patch("agent.runtime.summary_model.call_summary_messages", side_effect=AssertionError("No unrelated summary")) as summary:
                self.turn(graph, "continue", model)
                self.turn(graph, "full answer", model)
            summary.assert_not_called()

    def test_call_budget_preserves_a_durable_prefix(self):
        with patch.dict(os.environ, {"AI_LONG_ANSWER_MAX_CALLS": "3"}):
            result, model = self.prefix(ScriptedSections())
        self.assertIn("LONG_ANSWER_LIMIT", result["answer"])
        self.assertEqual(len(self.store.load(self.scope)["completed"]), 2)
        resumed = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            result = self.turn(self.graph(db, resumed), "continue", resumed)
        self.assertEqual(resumed.ids, ["section-3"])
        self.assertEqual(result["execution_outcome"], "completed")

    def test_saved_cursor_and_tool_context_are_strictly_validated(self):
        self.prefix(); ledger = self.store.load(self.scope)
        for mutate in (lambda value: value.update(published=True), lambda value: value.update(status="complete"),
                       lambda value: value["completed"][0].update(section_id="section-3"),
                       lambda value: value["messages"].append({"role": "tool", "name": "create_file", "content": "untrusted"})):
            value = deepcopy(ledger); mutate(value)
            with self.assertRaises(ValueError): validate_ledger(value)

    def test_controls_are_case_insensitive_and_do_not_treat_next_as_approval(self):
        for value in ("continue", "Continue", "CONTINUE ANSWER", "/continue", "resume answer"):
            self.assertEqual(command(value), "continue")
        self.assertIsNone(command("next")); self.assertIsNone(command("yes"))
        self.assertEqual(command("SHOW FULL ANSWER"), "full")


    def test_followup_uses_all_published_sections_of_the_logical_answer(self):
        self.prefix(); model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            graph = self.graph(db, model); self.turn(graph, "continue", model)
            seen = []
            def followup(messages, specs):
                seen.append(json.loads(messages[1]["content"])["previous_exchange"])
                self.assertEqual(specs, [])
                return {"content": "Foundations\nRules\nPitfalls"}
            graph = self.graph(db, followup)
            result = self.turn(graph, "List topics in your previous answer. Topic names only.")
        self.assertEqual(result["answer"], "Foundations\nRules\nPitfalls")
        self.assertEqual(seen[0]["question"], self.question)
        for title in ("Foundations", "Rules", "Pitfalls"):
            self.assertEqual(seen[0]["answer"].count("## " + title), 1)
        self.assertIsNone(self.store.load(self.scope))

    def test_browser_adapter_accepts_continue_and_full_answer_without_action_calls(self):
        from agent.interfaces.browser import BrowserBackend
        model = ScriptedSections(stop="section-2")
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            backend = BrowserBackend.__new__(BrowserBackend)
            backend.graph = self.graph(db, model); backend.catalog = self.catalog
            backend.user = "u"; backend.space = "p"; backend.session_config = session_config
            backend.actions = Mock(side_effect=AssertionError("Text resume cannot execute or propose actions"))
            with patch("agent.interfaces.browser.ROOT", self.root):
                first = backend.submit("a", self.question)
                self.assertEqual(first["execution_outcome"], "partial")
                resumed = ScriptedSections()
                with patch("agent.providers.tools.call_tool_messages", side_effect=resumed):
                    second = backend.submit("a", "CONTINUE")
                    full = backend.submit("a", "FULL ANSWER")
        self.assertEqual(resumed.ids, ["section-2", "section-3"])
        self.assertNotIn("## Foundations", second["answer"])
        self.assertEqual(full["answer"].count("## Foundations"), 1)
        backend.actions.assert_not_called()

    def test_progress_writer_does_not_leak_into_another_thread(self):
        from concurrent.futures import ThreadPoolExecutor
        from agent.runtime.continuations import save_progress
        self.prefix(); ledger = self.store.load(self.scope)
        writer = Mock()
        with progress_scope(self.question, writer), ThreadPoolExecutor() as pool:
            self.assertFalse(pool.submit(save_progress, ledger).result())
        writer.assert_not_called()


    def test_resume_starts_at_the_current_provider_and_preserves_manual_selection(self):
        self.prefix(); model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db:
            self.turn(self.graph(db, model), "continue", model)
        self.assertEqual(model.providers, ["openrouter", "groq"])
        self.prefix(); model = ScriptedSections()
        with closing(sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)) as db, provider_selection("gemini"):
            self.turn(self.graph(db, model), "continue", model)
        self.assertEqual(model.providers, ["gemini", "gemini"])

    def test_code_case_and_significant_blank_lines_are_preserved(self):
        def code(identity, value):
            if identity in {"section-1", "section-2"}:
                label = "A" if identity == "section-1" else "a"
                value["content"] = "```python\nvalue = '" + label + "'\n\n\nprint(value)\n```"
                value["covered_points"] = ["case-sensitive code"]
            return value
        result, _ = self.prefix(ScriptedSections(bad=code))
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertIn("value = 'A'\n\n\nprint(value)", result["answer"])
        self.assertIn("value = 'a'\n\n\nprint(value)", result["answer"])


    def test_text_continuation_cannot_bypass_enabled_technical_review(self):
        def code(identity, value):
            if identity == "section-2": value["content"] = "```python\nprint('held for review')\n```"
            return value
        with patch.dict(os.environ, {"AI_TECHNICAL_VERIFICATION": "auto"}):
            result, _ = self.prefix(ScriptedSections(bad=code))
        self.assertIn("ANSWER_REVIEW_REQUIRED", result["answer"])
        self.assertNotIn("held for review", result["answer"])
        self.assertEqual(len(self.store.load(self.scope)["completed"]), 1)

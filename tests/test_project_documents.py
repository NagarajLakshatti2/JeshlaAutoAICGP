"""Per-project keyword collections do not read global indexes or load models."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.storage.project_documents import ProjectDocuments, MAX_DOCUMENTS
from agent.storage.projects import ProjectConfigurationError
from agent.policies.citations import visible_document_refs
from rag.project_retrieval import collection_for_state, search_project_documents
from tests import test_projects as fixtures


def document(name="rules.md", text="Alpha project uses TestNG for its test framework.", truncated=False):
    return {"name": name, "text": text, "truncated": truncated}


class ProjectDocumentStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ProjectDocuments(self.root, "u", "s", "project-" + "a" * 32)

    def test_import_and_missing_collection_reads_never_create_an_index(self):
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.search(["framework"]), [])
        self.assertEqual(list(self.root.iterdir()), [])
        with self.assertRaises(ProjectConfigurationError): self.store.remove("missing", "a" * 64)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_save_persists_searches_replaces_and_removes_only_the_snapshot(self):
        source = self.root / "rules.md"; source.write_text("original source unchanged")
        saved = self.store.save([document(text="UniqueOldMarker uses TestNG")])[0]
        self.assertTrue(self.store.search(["UniqueOldMarker"]))
        reopened = ProjectDocuments(self.root, "u", "s", "project-" + "a" * 32)
        updated = reopened.save([document(text="UniqueNewMarker uses pytest")])[0]
        self.assertEqual(updated["id"], saved["id"])
        self.assertNotEqual(updated["sha256"], saved["sha256"])
        self.assertEqual(reopened.search(["UniqueOldMarker"]), [])
        self.assertTrue(reopened.search(["UniqueNewMarker"]))
        with self.assertRaises(ProjectConfigurationError): reopened.remove(saved["id"], saved["sha256"])
        reopened.remove(updated["id"], updated["sha256"])
        self.assertEqual(reopened.list(), []); self.assertEqual(reopened.search(["pytest"]), [])
        self.assertEqual(source.read_text(), "original source unchanged")

    def test_owner_namespace_and_project_each_have_a_separate_index(self):
        self.store.save([document()])
        for user, namespace, project in (("other", "s", "a"), ("u", "other", "a"), ("u", "s", "b")):
            with self.subTest(scope=(user, namespace, project)):
                other = ProjectDocuments(self.root, user, namespace, "project-" + project * 32)
                self.assertNotEqual(other.path, self.store.path)
                self.assertEqual(other.search(["TestNG"]), []); self.assertEqual(other.list(), [])
                other.path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.store.path, other.path)
                with self.assertRaises(ProjectConfigurationError): other.list()

    def test_invalid_batch_does_not_create_storage_or_silently_truncate(self):
        for data in ([], [document(text="")], [document(text="x" * 12001)], [document(name="../rules.md")],
                     [document(name="..")], [document(truncated="false")], [document(), document(name="RULES.MD")]):
            with self.subTest(data=str(data)[:100]):
                with self.assertRaises(ProjectConfigurationError): self.store.save(data)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_document_count_and_updates_are_transactional(self):
        for start in range(0, MAX_DOCUMENTS, 5):
            self.store.save([document(str(i) + ".md", "rule " + str(i)) for i in range(start, start + 5)])
        before = self.store.list()
        with self.assertRaises(ProjectConfigurationError):
            self.store.save([document("0.md", "new value"), document("extra.md")])
        self.assertEqual(self.store.list(), before)

    def test_search_rejects_fts_operators_and_invalid_limits(self):
        self.store.save([document()])
        for tokens in (["x OR y"], ['" OR *'], [None], "TestNG", ["x"] * 25):
            with self.subTest(tokens=tokens):
                with self.assertRaises(ProjectConfigurationError): self.store.search(tokens)
        for limit in (0, 6, True):
            with self.assertRaises(ProjectConfigurationError): self.store.search(["TestNG"], limit)


class ScopedDocumentBackendTests(unittest.TestCase):
    setUp = fixtures.ProjectBackendTests.setUp

    def test_selected_project_shares_documents_across_its_chats_not_other_scopes(self):
        self.view_a.project_documents().save([document()])
        ca = self.view_a.create_chat("One"); self.view_a.create_chat("Two")
        reopened = self.base.for_project(self.pa["id"])
        found = reopened.search_project_documents("framework")
        self.assertEqual(found["sources"][0]["source"], "rules.md")
        self.assertEqual(reopened.turns(ca), [])
        self.assertEqual(self.view_b.search_project_documents("framework")["sources"], [])
        other = copy.copy(self.view_a); other.user = "other"
        with self.assertRaises(ProjectConfigurationError): other.project_documents()
        with self.assertRaises(ProjectConfigurationError): self.base.project_documents()
        self.assertEqual(self.invocations, [])

    def test_sources_have_stable_project_bound_references_and_honest_limits(self):
        self.view_a.project_documents().save([document(text="framework " * 400, truncated=True)])
        self.view_b.project_documents().save([document(text="framework " * 400, truncated=True)])
        first = self.view_a.search_project_documents("framework")
        repeated = self.view_a.search_project_documents("framework")
        other = self.view_b.search_project_documents("framework")
        self.assertEqual(first, repeated)
        self.assertNotEqual(first["sources"][0]["ref"], other["sources"][0]["ref"])
        for source in first["sources"]:
            self.assertLessEqual(len(source["text"]), 1200)
            self.assertTrue(source["truncated"])
            self.assertTrue(source["location"].startswith("extracted characters"))
        self.assertEqual(visible_document_refs(first, json.dumps(first, ensure_ascii=False)), {s["ref"] for s in first["sources"]})

    def test_different_filenames_with_identical_text_do_not_share_a_source_ref(self):
        self.view_a.project_documents().save([document("one.md"), document("two.md")])
        sources = self.view_a.search_project_documents("framework")["sources"]
        self.assertEqual(len({source["ref"] for source in sources}), 2)

    def test_default_hybrid_request_is_explicit_keyword_without_global_or_ml_loading(self):
        self.view_a.project_documents().save([document()])
        with patch("rag.retrieval._load_resources", side_effect=AssertionError("no ML")), \
             patch("rag.retrieval._load_keyword_resources", side_effect=AssertionError("no global pickle")):
            result = search_project_documents("framework", state=self.view_a.request_scope(), application_root=self.root, mode="hybrid")
        self.assertEqual(result["retrieval_mode"], "keyword")
        self.assertEqual(result["requested_mode"], "hybrid")
        self.assertIn("not configured", result["note"])
        with self.assertRaises(ProjectConfigurationError): collection_for_state({"project_id": self.pa["id"]}, self.root)

    def test_real_conversation_pipeline_uses_only_selected_collection_and_citations(self):
        from agent.langgraph import langgraph_agent as module
        self.view_a.project_documents().save([document(text="Alpha framework is TestNG.")])
        self.view_b.project_documents().save([document(text="BetaSecret framework is pytest.")])
        reference = self.view_a.search_project_documents("framework")["sources"][0]["ref"]
        messages_seen = []
        def model(messages, tools):
            messages_seen.append(json.dumps(messages, ensure_ascii=False))
            self.assertNotIn("BetaSecret", messages_seen[-1])
            if len(messages_seen) == 1:
                return {"role": "assistant", "content": "", "tool_calls": [{"id": "doc1", "type": "function", "function": {"name": "search_documents", "arguments": json.dumps({"query": "framework", "mode": "keyword"})}}]}
            return {"role": "assistant", "content": "Alpha uses TestNG [" + reference + "] rules.md, extracted characters."}
        state = {**self.view_a.request_scope(), "question": "Which framework is in my project documents?", "route": "rag", "conversation_session": "fixture", "history": ""}
        with patch.object(module, "PROJECT_ROOT", self.root), patch("agent.tool_llm.call_tool_messages", side_effect=model), \
             patch.object(module, "search_documents", side_effect=AssertionError("no global documents")), \
             patch.dict("os.environ", {"AI_LONG_ANSWERS_ENABLED": "false", "AI_TECHNICAL_VERIFICATION": "off"}):
            result = module.conversational_answer_node(state)
        self.assertIn(reference, result["answer"])
        self.assertIn("TestNG", result["answer"])
        self.assertEqual(len(messages_seen), 2)


    def test_full_shared_graph_restores_project_scope_and_publishes_grounded_answer(self):
        from langgraph.checkpoint.sqlite import SqliteSaver
        from agent.langgraph import langgraph_agent as module
        self.view_a.project_documents().save([document(text="Alpha selected framework is TestNG.")])
        self.view_b.project_documents().save([document(text="BetaPrivate selected framework is pytest.")])
        ref = self.view_a.search_project_documents("framework")["sources"][0]["ref"]
        seen = []
        def model(messages, specs):
            seen.append(json.dumps(messages, ensure_ascii=False))
            self.assertNotIn("BetaPrivate", seen[-1])
            if len(seen) == 1:
                return {"role": "assistant", "content": "", "tool_calls": [{"id": "project-doc", "type": "function", "function": {"name": "search_documents", "arguments": json.dumps({"query": "framework"})}}]}
            return {"role": "assistant", "content": "The selected project uses TestNG [" + ref + "] (rules.md, extracted characters)."}
        chat = self.view_a.create_chat("Scoped document workflow")
        with SqliteSaver.from_conn_string(str(self.root / "document-graph.sqlite3")) as saver, \
             patch.object(module, "PROJECT_ROOT", self.root), \
             patch("agent.tool_llm.call_tool_messages", side_effect=model), \
             patch.object(module, "search_documents", side_effect=AssertionError("Global documents must not load")), \
             patch.dict("os.environ", {"AI_LONG_ANSWERS_ENABLED": "false", "AI_TECHNICAL_VERIFICATION": "off"}):
            self.view_a.graph = module.build_graph(saver)
            result = self.view_a.submit(chat, "From my saved project documents, which framework is specified?")
            self.assertEqual(result["task_status"], "completed")
            self.assertIn(ref, result["answer"])
            checkpoint = self.view_a.graph.get_state(self.view_a.session_config(chat, "u", self.view_a.space)).values
            self.assertEqual(checkpoint["project_id"], self.pa["id"])
        self.assertEqual(len(seen), 2)
        self.assertIn(ref, self.view_a.turns(chat)[0]["answer"])
        self.assertEqual(self.view_b.turns(chat), [])


class ProjectDocumentUITests(unittest.TestCase):
    setUp = fixtures.ProjectUITests.setUp
    open_projects = fixtures.ProjectUITests.open_projects

    def details(self, row):
        self.open_projects()
        self.app.button(key="project_settings_" + row["id"]).click().run()
        self.assertFalse(self.app.exception)

    def test_explicit_preview_save_search_and_remove_with_original_file_unchanged(self):
        self.app.run(); self.details(self.pa)
        backend = self.base.for_project(self.pa["id"])
        prefix = "project_knowledge_" + self.pa["id"] + "_"
        upload = SimpleNamespace(name="rules.md", getvalue=lambda: b"Alpha framework is TestNG.")
        self.assertEqual(backend.project_documents().list(), [])
        with patch("streamlit.file_uploader", return_value=[upload]):
            self.app.button(key=prefix + "preview").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(backend.project_documents().list(), [])
            self.app.button(key=prefix + "save").click().run()
        self.assertFalse(self.app.exception)
        saved = backend.project_documents().list(); self.assertEqual(len(saved), 1)
        self.app.text_input(key=prefix + "query").set_value("framework").run()
        self.app.button(key=prefix + "search").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Alpha framework is TestNG" in item.value for item in self.app.text))
        self.app.button(key=prefix + "remove_" + saved[0]["id"]).click().run()
        self.assertFalse(self.app.exception); self.assertEqual(backend.project_documents().list(), [])
        self.assertFalse((self.a / "rules.md").exists())
        self.assertEqual(self.invocations, [])

    def test_project_switch_discards_staged_text_and_other_project_search_results(self):
        self.app.run(); self.open_projects()
        self.app.button(key="choose_project_" + self.pa["id"]).click().run()
        prefix = "project_knowledge_" + self.pa["id"] + "_"
        self.app.session_state[prefix + "draft"] = [document(text="AlphaPrivate")]
        self.app.session_state[prefix + "results"] = {"sources": [{"text": "AlphaPrivate"}]}
        self.open_projects(); self.app.button(key="choose_project_" + self.pb["id"]).click().run()
        self.assertFalse(self.app.exception)
        self.assertNotIn(prefix + "draft", self.app.session_state)
        self.assertNotIn(prefix + "results", self.app.session_state)
        self.assertEqual(self.base.for_project(self.pb["id"]).project_documents().list(), [])
        self.assertEqual(self.invocations, [])

    def test_empty_or_general_views_do_not_create_indexes(self):
        self.app.run(); self.assertFalse(self.app.exception)
        self.details(self.pa)
        self.assertFalse((self.root / "outputs/knowledge").exists())
        self.assertTrue(any("Keyword search runs locally" in item.value for item in self.app.caption))
        self.assertEqual(self.invocations, [])

"""Offline checks: no Jira login, remote writes, or LLM calls."""
import asyncio
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.langgraph import jira_workflow_node as module


def proposal():
    return {"epic": {"key": "TEST-1"}, "story": {"key": "TEST-2"},
            "test_cases": [{"summary": "Select independently", "preconditions": ["Open control"],
                            "steps": [{"action": "Select A", "expected": "A selected"}],
                            "acceptance_criteria": ["Other values unchanged"]}], "assumptions": []}


INVENTORY = {"epic": [{"key": "TEST-1", "summary": "Controls"}],
             "story": [{"key": "TEST-2", "summary": "Selection"}]}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"JIRA_PROJECT_KEY": "TEST", "JIRA_SITE_URL": "https://example.atlassian.net",
                                          "AI_PROJECT_ROOT": str(self.root)})
        self.env.start()
        self.app = patch.object(module, "APP_ROOT", self.root)
        self.app.start()

    def tearDown(self):
        self.app.stop()
        self.env.stop()
        self.temp.cleanup()

    def request(self):
        return module.build_request(proposal(), "TEST", INVENTORY)[0]

    def test_natural_creation_routing(self):
        self.assertTrue(module.workflow_intent("Create a Jira test case for checking independent selections."))
        self.assertTrue(module.workflow_intent("Write new test cases for the page"))
        self.assertFalse(module.workflow_intent("Read build.gradle and explain it"))

    def test_defaults_deny_parent_creation(self):
        request = self.request()
        self.assertFalse(request["allow_create_epic"])
        self.assertFalse(request["allow_create_story"])

    def test_model_cannot_grant_permission(self):
        p = proposal()
        p["allow_create_epic"] = True
        with self.assertRaises(module.Blocked):
            module.build_request(p, "TEST", INVENTORY)

    def test_model_cannot_invent_parent_key(self):
        p = proposal()
        p["story"]["key"] = "TEST-99"
        with self.assertRaises(module.Blocked):
            module.build_request(p, "TEST", INVENTORY)

    def test_null_parent_echo_is_ignored(self):
        p = proposal()
        p["epic"]["parent"] = None
        p["story"]["parent"] = None
        request, _ = module.build_request(p, "TEST", INVENTORY)
        self.assertEqual(request["epic"]["key"], "TEST-1")
        self.assertNotIn("parent", request["story"])
        self.assertIsNone(p["story"]["parent"])

    def test_model_parent_link_is_rejected(self):
        p = proposal()
        p["story"]["parent"] = "TEST-99"
        with self.assertRaises(module.Blocked):
            module.build_request(p, "TEST", INVENTORY)

    def test_wrapped_validation_message_is_visible(self):
        error = ExceptionGroup("MCP", [ExceptionGroup("nested", [module.Blocked("Invalid draft parent: epic")])])
        self.assertIn("Invalid draft parent: epic", module.explain_error(error))

    def test_unknown_exception_text_is_not_exposed(self):
        error = ExceptionGroup("MCP", [RuntimeError("secret-callback-code")])
        self.assertNotIn("secret-callback-code", module.explain_error(error))

    def test_import_draft_cannot_enable_creation_permissions(self):
        request = self.request()
        request["allow_create_epic"] = True
        path = self.root / "draft.json"
        module.save(path, request)
        imported = module.import_draft(module.Store(), "draft.json")
        self.assertFalse(imported["allow_create_epic"])

    def test_import_other_project_is_blocked(self):
        request = self.request()
        request["project_key"] = "OTHER"
        module.save(self.root / "draft.json", request)
        with self.assertRaises(module.Blocked):
            module.import_draft(module.Store(), "draft.json")

    def test_import_path_outside_project_is_blocked(self):
        with self.assertRaises(module.Blocked):
            module.import_draft(module.Store(), "../draft.json")

    def test_model_cannot_bind_duplicate(self):
        p = proposal()
        p["test_cases"][0]["key"] = "TEST-3"
        with self.assertRaises(module.Blocked):
            module.build_request(p, "TEST", INVENTORY)

    def test_existing_parent_title_is_authoritative(self):
        p = proposal()
        p["story"]["summary"] = "Invented change"
        r, _ = module.build_request(p, "TEST", INVENTORY)
        self.assertEqual(r["story"]["summary"], "Selection")

    def test_state_survives_restart(self):
        module.Store().write({"status": "draft", "request": self.request()})
        self.assertEqual(module.Store().read()["request"]["project_key"], "TEST")
        self.assertIn("Draft saved", module.handle("RESUME"))

    def test_project_switch_does_not_reuse_state(self):
        module.Store().write({"status": "draft", "request": self.request()})
        with patch.dict(os.environ, {"JIRA_PROJECT_KEY": "OTHER"}):
            self.assertEqual(module.Store().read()["status"], "empty")

    def test_permission_command_invalidates_approval(self):
        module.Store().write({"status": "awaiting_approval", "request": self.request(), "plan": {"old": True}})
        module.handle("ALLOW CREATE STORY TRUE")
        state = module.Store().read()
        self.assertTrue(state["request"]["allow_create_story"])
        self.assertNotIn("plan", state)
        self.assertEqual(state["status"], "draft")

    def test_wrong_approval_no_connection(self):
        state = {"status": "awaiting_approval", "plan": {"blocked": [], "approval_sha256": "a" * 64}}
        with self.assertRaises(module.Blocked):
            asyncio.run(module.approve_connected(module.Store(), state, "b" * 64))

    def test_tampered_plan_no_connection(self):
        state = {"status": "awaiting_approval", "plan": {"blocked": [], "approval_sha256": "a" * 64}}
        with self.assertRaises(module.Blocked):
            asyncio.run(module.approve_connected(module.Store(), state, "a" * 64))

    def test_lock_prevents_concurrent_session(self):
        store = module.Store()
        with module.exclusive(store.lock):
            with self.assertRaises(module.Blocked):
                module.handle("STATUS")

    def test_cancel_keeps_receipt(self):
        module.Store().write({"status": "needs_review", "journal": "receipt.json"})
        module.handle("CANCEL")
        self.assertEqual(module.Store().read()["journal"], "receipt.json")

    def test_pending_plan_cannot_be_silently_overwritten(self):
        module.Store().write({"status": "draft", "request": self.request()})
        with patch.object(module, "discuss_or_revise", return_value="Saved proposal discussion. No actions executed.") as discussion:
            self.assertIn("No actions executed", module.handle("Create another testcase"))
        discussion.assert_called_once()
        self.assertEqual(module.Store().read()["request"], self.request())

    def test_run_request_cannot_add_shell_flags(self):
        self.assertIn("Use RUN QA", module.run_qa("RUN QA TEST-3 --extra"))

    def test_natural_execution_routing(self):
        self.assertTrue(module.workflow_intent("Run existing automation for TEST-3."))
        self.assertFalse(module.RUN_REQUEST.fullmatch("Do not run automation for TEST-3"))

    def test_prompt_plan_approve_complete_without_llm_writes(self):
        from test_jira_creation import G, req
        gateway = G()

        @asynccontextmanager
        async def session():
            yield object()

        async def cloud(session):
            return gateway.cloud_id

        async def drafted(gateway, question, previous=None):
            return module.validate_request(req()), []

        client = types.ModuleType("integrations.jira.jira_mcp_client")
        client.jira_session, client.get_cloud_id = session, cloud
        with patch.dict(os.environ, {"JIRA_PROJECT_KEY": "T", "JIRA_ALLOW_CREATE": "true"}), \
             patch.dict(sys.modules, {client.__name__: client}), \
             patch.object(module, "JiraGateway", lambda *args: gateway), \
             patch.object(module, "draft", drafted):
            output = module.handle("Create a Jira test case for independent checkbox clearing")
            self.assertIn("APPROVE", output)
            self.assertEqual(gateway.writes, [])
            pending = module.Store().read()
            digest = pending["plan"]["approval_sha256"]
            result = module.handle("APPROVE " + digest)
            self.assertIn("complete", result)
            self.assertEqual(len(gateway.writes), 1)
            self.assertEqual(module.Store().read()["status"], "complete")
            with self.assertRaises(module.Blocked):
                module.handle("APPROVE " + digest)
            self.assertEqual(len(gateway.writes), 1)


if __name__ == "__main__":
    unittest.main()

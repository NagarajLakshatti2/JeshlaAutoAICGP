import tempfile
import unittest
from pathlib import Path

from agent.orchestration.controls import RunControl
from agent.orchestration.coordinator import Coordinator, Specialist
from agent.orchestration.handoff import Handoff
from agent.orchestration.runtime import dispatch_project_filesystem
from integrations.autogen.selection import agent_mode_selection, current_agent_mode


class ProjectDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "selected"
        self.root.mkdir()
        (self.root / "notes.md").write_text("selected-project evidence", encoding="utf-8")
        self.outside = Path(self.temp.name) / "outside.md"
        self.outside.write_text("outside project secret", encoding="utf-8")
        self.scope = {
            "memory_user_id": "fixture-owner",
            "memory_namespace": "fixture-space",
            "project_id": "project-" + "a" * 32,
            "bound_project_root": str(self.root.resolve()),
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_dispatch_reads_selected_project_and_returns_host_evidence(self):
        for mode in ("autogen", "langgraph"):
            with self.subTest(mode=mode), agent_mode_selection(mode):
                result = dispatch_project_filesystem(
                    request_scope=self.scope, chat_id="chat-fixture", task_id="task-fixture",
                    goal="Read the project note", executor=lambda goal, tools: tools["read_file"](
                        relative_path="notes.md"))
                self.assertEqual(current_agent_mode(), mode)
                self.assertEqual(result["status"], "completed")
                self.assertIn("selected-project evidence", result["result"]["content"])
                self.assertEqual(len(result["evidence_refs"]), 1)
                self.assertIn("read_file", result["evidence_refs"][0])

    def test_chat_file_read_uses_coordinator_and_consolidates_evidence(self):
        from agent.runtime.conversation import answer_question
        from agent.tools.project_tools import ProjectTools

        state = {"question": "Read notes.md and summarize it", "route": "direct",
                 "conversation_session": "chat-fixture", **self.scope}
        requested = []
        def model(messages, specs):
            if specs and not requested:
                requested.append(True)
                return {"role": "assistant", "content": "", "tool_calls": [{
                    "id": "read-fixture", "type": "function",
                    "function": {"name": "read_file", "arguments": '{"relative_path":"notes.md"}'}}]}
            return {"role": "assistant", "content": "The note says selected-project evidence."}

        for mode in ("autogen", "langgraph"):
            with self.subTest(mode=mode), agent_mode_selection(mode):
                requested.clear()
                state["question"] = "Read notes.md and summarize it"
                result = answer_question(
                    state, model=model, project_root=str(self.root),
                    tools=ProjectTools(str(self.root)), document_search=lambda **kwargs: {})
                self.assertEqual(result["execution_outcome"], "completed", result)
                self.assertIn("selected-project evidence", result["answer"])
                self.assertTrue(result["claims"][0]["evidence_refs"])

    def test_project_action_handoff_in_each_mode(self):
        from agent.orchestration.project_actions import project_action_turn, route_project_action
        state = {**self.scope, "question": "Inspect this project", "conversation_session": "fixture"}
        for mode in ("autogen", "langgraph"):
            with agent_mode_selection(mode):
                for action, role in (("inspect_browser_page", "Browser"),
                                     ("discover_jira_traceability", "Jira")):
                    with self.subTest(mode=mode, role=role):
                        control, task = project_action_turn(1)
                        proposal = route_project_action(state, action, control, task)
                        self.assertEqual((proposal.name, proposal.capability, proposal.goal),
                                         (action, role, state["question"]))
                        with self.assertRaises(ValueError):
                            route_project_action(state, action, control, task)

    def test_dispatch_cannot_read_outside_selected_project(self):
        result = dispatch_project_filesystem(
            request_scope=self.scope, chat_id="chat-fixture", goal="Read outside",
            executor=lambda goal, tools: tools["read_file"](relative_path="../outside.md"))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["evidence_refs"], ())

    def test_api_specialist_search_is_read_only_and_project_scoped(self):
        from agent.orchestration.runtime import dispatch_project_api
        for mode in ("autogen", "langgraph"):
            with self.subTest(mode=mode), agent_mode_selection(mode):
                def inspect(goal, tools):
                    self.assertEqual(set(tools), {"list_files", "read_file", "search_text"})
                    return tools["search_text"](query="selected-project")
                result = dispatch_project_api(
                    request_scope=self.scope, chat_id="chat-fixture", goal="Inspect API endpoint",
                    executor=inspect)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(len(result["evidence_refs"]), 1)

    def test_api_question_routes_through_api_specialist_in_chat(self):
        from agent.runtime.conversation import answer_question
        from agent.tools.project_tools import ProjectTools
        state = {"question": "Search the API endpoint in this project", "route": "direct",
                 "conversation_session": "chat-fixture", **self.scope}
        requested = []
        def model(messages, specs):
            if specs and not requested:
                requested.append(True)
                return {"role": "assistant", "content": "", "tool_calls": [{
                    "id": "api-search-fixture", "type": "function",
                    "function": {"name": "search_text", "arguments": '{"query":"selected-project"}'}}]}
            return {"role": "assistant", "content": "The API source contains the selected-project marker."}
        for mode in ("autogen", "langgraph"):
            with self.subTest(mode=mode), agent_mode_selection(mode):
                requested.clear()
                result = answer_question(
                    state, model=model, project_root=str(self.root),
                    tools=ProjectTools(str(self.root)),
                    document_search=lambda **kwargs: {})
                self.assertEqual(result["execution_outcome"], "completed")
                self.assertTrue(result["claims"][0]["evidence_refs"])

    def test_cancelled_dispatch_does_not_invoke_executor(self):
        control = RunControl({"delegations": 1, "tool_calls": 1, "time_seconds": 30})
        control.cancel()
        called = []
        result = dispatch_project_filesystem(
            request_scope=self.scope, chat_id="chat-fixture", goal="Read note",
            executor=lambda goal, tools: called.append(True), control=control,
            budget=dict(control.remaining))
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(called, [])

    def test_tool_call_budget_is_charged_before_read(self):
        control = RunControl({"delegations": 1, "tool_calls": 0, "time_seconds": 30})
        result = dispatch_project_filesystem(
            request_scope=self.scope, chat_id="chat-fixture", goal="Read note",
            executor=lambda goal, tools: tools["read_file"](relative_path="notes.md"),
            control=control, budget=dict(control.remaining))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["evidence_refs"], ())

    def test_coordinator_returns_unsupported_for_unregistered_capability(self):
        handoff = Handoff.create(
            owner_id="fixture-owner", project_id=self.scope["project_id"],
            chat_id="chat-fixture", task_id="task-fixture",
            allowed_capabilities=("File System",), remaining_budget={"delegations": 1})
        coordinator = Coordinator({"File System": Specialist("File System", lambda goal, _handoff, _control: {})})
        result = coordinator.dispatch("Need database access", "Database", handoff,
                                      RunControl({"delegations": 1, "time_seconds": 30}))
        self.assertEqual(result["status"], "unsupported")

    def test_consolidation_deduplicates_claims_and_reports_missing_evidence(self):
        from agent.orchestration.results import consolidate
        result = consolidate(
            [{"status": "completed", "capability": "File System",
              "claims": ["Same finding", "Same finding"]},
             {"status": "incomplete", "capability": "API", "message": "Unavailable"}],
            evidence_by_capability={"File System": ["evidence-1"]})
        self.assertEqual(len(result["claims"]), 1)
        self.assertEqual(result["claims"][0]["evidence_refs"], ["evidence-1"])
        self.assertEqual(result["incomplete_branches"][0]["capability"], "API")
        ungrounded = consolidate(
            [{"status": "completed", "capability": "File System", "claims": ["Unverified"]}])
        self.assertEqual(ungrounded["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()

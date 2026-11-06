"""Project-scoped Jira traceability guards; all Jira reads are mocked."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.storage.projects import ProjectConfigurationError
from agent.tools.project_tools import ProjectTools


class JiraTraceabilityToolTests(unittest.TestCase):
    def test_traceability_is_read_only_and_jira_mutations_are_not_project_actions(self):
        from agent.tool_policy import CONTROLLED_PROJECT_ACTIONS, PROJECT_ACTIONS, READ_ONLY_PROJECT_ACTIONS
        self.assertIn("discover_jira_traceability", READ_ONLY_PROJECT_ACTIONS)
        self.assertNotIn("discover_jira_traceability", CONTROLLED_PROJECT_ACTIONS)
        jira_mutations={name for name in PROJECT_ACTIONS
                        if name.startswith(("create_jira", "update_jira", "delete_jira"))}
        self.assertEqual(jira_mutations, set())

    def test_exact_tags_verify_only_existing_subtasks_and_titles_stay_suggestions(self):
        from integrations.jira.feature_jira_mapping import build_mapping_report
        inventory = {"project_root": "fixture", "feature_files_scanned": 1,
            "scenario_definitions": 4, "scenarios": [
                {"scenario": "Login form", "jira_keys": ["QAP-1"]},
                {"scenario": "Payment flow", "jira_keys": []},
                {"scenario": "Ambiguous", "jira_keys": ["QAP-1", "QAP-3"]},
                {"scenario": "Missing", "jira_keys": ["QAP-99"]}]}
        issues = [
            {"key": "QAP-1", "fields": {"summary": "Login check", "issuetype": {"name": "Sub-task", "subtask": True},
                "parent": {"key": "QAP-10"}, "status": {"name": "To Do"}}},
            {"key": "QAP-2", "fields": {"summary": "Payment flow", "issuetype": {"name": "Sub-task", "subtask": True},
                "parent": {"key": "QAP-11"}, "status": {"name": "To Do"}}},
            {"key": "QAP-3", "fields": {"summary": "Ambiguous issue", "issuetype": {"name": "Task", "subtask": False},
                "parent": None, "status": {"name": "To Do"}}}]
        report = build_mapping_report(inventory, issues, {"QAP-1", "QAP-2", "QAP-3"})
        rows = {row["scenario"]: row for row in report["scenarios"]}
        self.assertEqual(rows["Login form"]["verification"], "verified_subtask")
        self.assertTrue(rows["Login form"]["jira_subtask_verified"])
        self.assertEqual(rows["Payment flow"]["verification"], "suggestion_needs_review")
        self.assertFalse(rows["Payment flow"]["jira_subtask_verified"])
        self.assertEqual(rows["Ambiguous"]["verification"], "ambiguous_tags")
        self.assertEqual(rows["Missing"]["verification"], "not_found_in_eligible_scope")
        self.assertEqual(report["verified_tag_mappings"], 1)
    def test_missing_assignment_or_unconnected_profile_stops_before_jira(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for project_id, scope in ((None, None), ("project-" + "a" * 32,
                    {"connection_id": "connection-" + "b" * 32,
                     "site_url": "https://example.atlassian.net", "project_key": "QAP",
                     "connected": False, "connection_namespace": "general"})):
                tool = ProjectTools(root, project_id=project_id, jira_scope=scope,
                    jira_user="local-user", jira_connection_namespace="general",
                    jira_catalog_path=root / "connections.sqlite3")
                with self.subTest(project_id=project_id), \
                     patch("integrations.jira.feature_jira_mapping.discover_jira_mappings") as discover, \
                     self.assertRaises(ProjectConfigurationError):
                    tool.discover_jira_traceability()
                discover.assert_not_called()

    def test_verified_assigned_profile_is_bound_to_selected_project_key(self):
        import asyncio
        connection_id = "connection-" + "b" * 32
        site = "https://example.atlassian.net"
        profile = {"id": connection_id, "kind": "jira_mcp", "status": "verified",
                   "details": {"jira_site_url": site}}
        storage = type("FakeStorage", (), {"tokens": object(), "client_info": object()})()
        captured = {}

        class FakeCatalog:
            def __init__(self, path, user, namespace):
                captured.update(path=path, user=user, namespace=namespace)
            def get(self, requested):
                captured["connection_id"] = requested
                return profile if requested == connection_id else None

        async def discover(root, project_key, **kwargs):
            captured.update(root=root, project_key=project_key, kwargs=kwargs)
            return {"mappings": [], "status": "ok"}

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = ProjectTools(root, project_id="project-" + "a" * 32,
                jira_scope={"connection_id": connection_id, "site_url": site,
                    "project_key": "QAP", "connected": True,
                    "connection_namespace": "general"},
                jira_user="local-user", jira_connection_namespace="general",
                jira_catalog_path=root / "connections.sqlite3")
            with patch("agent.storage.connections.ConnectionCatalog", FakeCatalog), \
                 patch("integrations.jira.jira_mcp_client.CatalogOAuthTokenStorage",
                       return_value=storage), \
                 patch("integrations.jira.feature_jira_mapping.discover_jira_mappings",
                       side_effect=discover):
                result = tool.discover_jira_traceability()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(captured["project_key"], "QAP")
        self.assertEqual(captured["kwargs"]["jira_site_url"], site)
        self.assertIs(captured["kwargs"]["token_storage"], storage)
        self.assertEqual(captured["root"], str(root))
        self.assertEqual(captured["namespace"], "general")


if __name__ == "__main__":
    unittest.main()

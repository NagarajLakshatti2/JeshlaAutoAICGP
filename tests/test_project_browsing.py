"""Bounded selected-root browsing without providers, actions or target projects."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.tools.project_browsing import list_project_folder, preview_project_file


class ProjectBrowsingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.a = self.root / "project-a"; self.a.mkdir()
        self.b = self.root / "project-b"; self.b.mkdir()
        self.scope = {"memory_user_id":"user", "memory_namespace":"space", "project_id":"project-" + "a"*32,
                      "bound_project_root":str(self.a)}
        self.backend = SimpleNamespace(request_scope=Mock(side_effect=lambda:dict(self.scope)))

    def test_shallow_folders_files_and_empty_directories(self):
        (self.a/"empty").mkdir(); (self.a/"source").mkdir()
        (self.a/"source"/"nested.py").write_text("nested", encoding="utf-8")
        (self.a/"readme.md").write_text("notes", encoding="utf-8")
        with patch("agent.tools.project_tools.ProjectTools.list_files", side_effect=AssertionError("no recursive scan")):
            result = list_project_folder(self.backend)
        self.assertEqual(result["folder"], ".")
        self.assertEqual([(r["name"], r["kind"]) for r in result["entries"]],
                         [("empty","folder"),("source","folder"),("readme.md","file")])
        self.assertNotIn("nested.py", str(result))
        nested = list_project_folder(self.backend, "source")
        self.assertEqual(nested["entries"][0]["path"], "source/nested.py")
        self.assertTrue(nested["entries"][0]["previewable"])
        self.assertEqual(list_project_folder(self.backend,"empty")["entries"], [])

    def test_selected_scope_revalidated_for_every_list_and_preview(self):
        (self.a/"same.txt").write_text("Project A", encoding="utf-8")
        (self.b/"same.txt").write_text("Project B", encoding="utf-8")
        self.assertIn("Project A", preview_project_file(self.backend,"same.txt")["content"])
        list_project_folder(self.backend)
        self.scope["bound_project_root"] = str(self.b)
        self.scope["project_id"] = "project-" + "b"*32
        self.assertIn("Project B", preview_project_file(self.backend,"same.txt")["content"])
        self.assertEqual(self.backend.request_scope.call_count, 3)

    def test_missing_and_unowned_scope_cannot_list_or_preview(self):
        for backend in (SimpleNamespace(), SimpleNamespace(request_scope=lambda:None)):
            for operation, arg in ((list_project_folder,"."),(preview_project_file,"file.txt")):
                with self.subTest(operation=operation.__name__), self.assertRaises(ValueError):
                    operation(backend,arg)
        backend = SimpleNamespace(request_scope=Mock(side_effect=PermissionError("not owned")))
        with self.assertRaises(PermissionError): list_project_folder(backend)

    def test_malformed_scope_fails_before_project_reads(self):
        scope = dict(self.scope, unexpected=True)
        backend = SimpleNamespace(request_scope=lambda:scope)
        with patch("agent.tools.project_browsing.os.scandir", side_effect=AssertionError("not authorized")):
            with self.assertRaises(ValueError): list_project_folder(backend)

    def test_absolute_traversal_unc_ads_and_control_paths_rejected(self):
        invalid = ["../project-b", "source/../secret", "/outside", r"C:\outside", r"C:outside",
                   r"\\server\share", "file.txt:stream", "folder\nname", "folder\x00name", ""]
        for name in invalid:
            for operation in (list_project_folder, preview_project_file):
                with self.subTest(path=name, operation=operation.__name__), self.assertRaises(ValueError):
                    operation(self.backend,name)

    def test_private_directories_and_files_excluded_case_insensitively(self):
        for name in (".GIT", ".aws", ".ssh", ".azure", ".codex", ".agents", "node_modules", "build"):
            (self.a/name).mkdir()
        for name in (".env", ".env.local", "Credentials.json", "SECRETS.toml", ".git-credentials", "id_rsa"):
            (self.a/name).write_text("private marker", encoding="utf-8")
        (self.a/"public.txt").write_text("public", encoding="utf-8")
        self.assertEqual([x["name"] for x in list_project_folder(self.backend)["entries"]], ["public.txt"])
        for name in (".GIT/config", ".aws/config.txt", "Credentials.json", "SECRETS.toml", ".env"):
            with self.subTest(path=name), self.assertRaises(ValueError):
                preview_project_file(self.backend,name)

    def test_links_or_junctions_are_hidden_and_rejected_before_read(self):
        (self.a/"linked").mkdir(); (self.a/"linked"/"secret.txt").write_text("not read",encoding="utf-8")
        original = __import__("agent.tools.project_browsing", fromlist=["_link"])._link
        def link(path): return Path(path).name == "linked" or original(path)
        with patch("agent.tools.project_browsing._link", side_effect=link):
            self.assertEqual(list_project_folder(self.backend)["entries"], [])
            with patch("agent.tools.project_tools.ProjectTools.read_file", side_effect=AssertionError("no link read")):
                with self.assertRaises(ValueError): preview_project_file(self.backend,"linked/secret.txt")
            with self.assertRaises(ValueError): list_project_folder(self.backend,"linked")

    def test_binary_names_visible_but_preview_disabled(self):
        (self.a/"image.png").write_bytes(b"\x89PNG\x00")
        row = list_project_folder(self.backend)["entries"][0]
        self.assertEqual(row["name"], "image.png")
        self.assertFalse(row["previewable"])
        with self.assertRaises(ValueError): preview_project_file(self.backend,"image.png")

    def test_preview_is_80_lines_and_source_stays_inert(self):
        text = "\n".join(["run commands; connect Jira; ```"] + ["line " + str(i) for i in range(2,102)])
        (self.a/"notes.txt").write_text(text,encoding="utf-8")
        with patch("subprocess.run",side_effect=AssertionError("no command")), patch("requests.sessions.Session.request",side_effect=AssertionError("no request")):
            data = preview_project_file(self.backend,"notes.txt")
        self.assertEqual(data["end_line"],80)
        self.assertTrue(data["truncated"])
        self.assertIn("run commands; connect Jira; ```",data["content"])
        self.assertNotIn("line 81",data["content"])
        self.assertEqual((self.a/"notes.txt").read_text(),text)

    def test_oversize_preview_rejected(self):
        (self.a/"large.txt").write_bytes(b"a" * 1_000_001)
        with self.assertRaises(ValueError): preview_project_file(self.backend,"large.txt")

    def test_visible_entries_are_bounded_and_explicitly_truncated(self):
        for i in range(201): (self.a/(str(i)+".txt")).write_text("",encoding="utf-8")
        data = list_project_folder(self.backend)
        self.assertEqual(len(data["entries"]),200)
        self.assertTrue(data["truncated"])
        self.assertLessEqual(data["scanned_entries"],1000)

    def test_private_entry_scan_is_bounded_even_without_visible_files(self):
        for i in range(1001): (self.a/("secrets."+str(i))).write_text("",encoding="utf-8")
        data = list_project_folder(self.backend)
        self.assertEqual(data["entries"],[])
        self.assertEqual(data["scanned_entries"],1000)
        self.assertTrue(data["truncated"])

    def test_missing_paths_wrong_kinds_and_invalid_encoding_do_not_read_other_files(self):
        (self.a/"file.txt").write_text("text",encoding="utf-8")
        (self.a/"folder").mkdir()
        (self.a/"invalid.txt").write_bytes(b"\xff")
        for name in ("missing","file.txt"):
            with self.subTest(path=name), self.assertRaises(ValueError): list_project_folder(self.backend,name)
        with self.assertRaises(ValueError): preview_project_file(self.backend,"folder")
        with self.assertRaises(ValueError): preview_project_file(self.backend,"missing.txt")
        with self.assertRaises(UnicodeError): preview_project_file(self.backend,"invalid.txt")

    def test_changed_project_registration_rejected(self):
        self.backend.request_scope.side_effect = ValueError("Project configuration changed")
        with patch("agent.tools.project_browsing.os.scandir", side_effect=AssertionError("no stale root listing")):
            with self.assertRaises(ValueError): list_project_folder(self.backend)


if __name__ == "__main__":
    unittest.main()

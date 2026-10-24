"""Smart Projects UI and free-only repository setup; all data is temporary."""
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch,Mock
from agent.storage.projects import ProjectCatalog,ProjectConfigurationError
from agent.storage.connections import ConnectionCatalog
from agent.runtime.workspace import WorkspaceSupport
from integrations.git import repositories as git
from tests import test_projects as fixtures


class Workspace:
    pass


class ConnectionTests(unittest.TestCase):
    def test_owned_metadata_env_credentials_and_disconnect(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"TEST_PROJECT_TOKEN":"fake-private-token"}):
            path=Path(folder)/"c.sqlite3";store=ConnectionCatalog(path,"u","s")
            row=store.save("github","Account","https://api.github.com",env_name="TEST_PROJECT_TOKEN")
            self.assertNotIn("sealed",row);self.assertNotIn("fake-private-token",str(row))
            self.assertEqual(store.credential(row["id"]),"fake-private-token")
            self.assertEqual(ConnectionCatalog(path,"other","s").list(),[])
            self.assertEqual(ConnectionCatalog(path,"u","other").list(),[])
            store.checked(row["id"],{"account":"fixture-user"})
            self.assertEqual(store.get(row["id"])["status"],"verified")
            store.disconnect(row["id"]);self.assertIsNone(store.get(row["id"]))
            with self.assertRaises(ProjectConfigurationError):store.credential(row["id"])

    @unittest.skipUnless(os.name=="nt","Windows user-bound credential storage")
    def test_token_is_encrypted_and_roundtrips_without_public_disclosure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"c.sqlite3";store=ConnectionCatalog(path,"u","s")
            row=store.save("gitlab","Private","https://gitlab.com",token="fixture-very-private-token")
            self.assertEqual(store.credential(row["id"]),"fixture-very-private-token")
            self.assertNotIn(b"fixture-very-private-token",path.read_bytes())
            self.assertNotIn("sealed",str(store.list()))

    def test_mcp_parked_before_any_network_or_secret_lookup(self):
        support=WorkspaceSupport()
        with patch("requests.get") as request:
            for kind in ("jira_mcp","github_mcp","custom_mcp"):
                with self.assertRaisesRegex(ProjectConfigurationError,"parked"):support.save_connection(kind,"MCP")
            from integrations.mcp.connections import discover
            with self.assertRaisesRegex(ProjectConfigurationError,"parked"):discover("https://example.org/mcp")
            request.assert_not_called()

    def test_account_check_is_explicit_and_does_not_echo_remote_errors(self):
        from integrations.git.accounts import check_account
        response=Mock(status_code=200);response.json.return_value={"login":"fixture"}
        with patch("requests.get",return_value=response) as request:
            self.assertEqual(check_account("github","private"),{"account":"fixture"})
            self.assertFalse(request.call_args.kwargs["allow_redirects"])
        with patch("requests.get",return_value=Mock(status_code=401)):
            with self.assertRaises(ProjectConfigurationError) as error:check_account("github","private")
            self.assertNotIn("private",str(error.exception))

    def test_legacy_registry_migration_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"p.sqlite3";source=Path(folder)/"source";source.mkdir()
            key="project-"+"a"*32
            with closing(sqlite3.connect(path)) as db,db:
                db.execute("CREATE TABLE local_projects(id TEXT,user TEXT,space TEXT,name TEXT,root TEXT,root_key TEXT,created_at TEXT,updated_at TEXT,PRIMARY KEY(user,space,id),UNIQUE(user,space,root_key))")
                db.execute("INSERT INTO local_projects VALUES(?,?,?,?,?,?,?,?)",(key,"u","s","Before",str(source),str(source),"before","before"))
            store=ProjectCatalog(path,"u","s")
            self.assertEqual(store.get(key)["name"],"Before");self.assertEqual(store.get(key)["source"],"local")
            self.assertEqual(store.get(key)["created_at"],"before")
            row=store.add_local("Next",folder);self.assertEqual(len(store.list()),2)
            store.set_binding(row["id"],"jira_mcp","connection-fixture",{"project_key":"TEST"})
            self.assertEqual(store.bindings(row["id"])["jira_mcp"]["options"]["project_key"],"TEST")
            with self.assertRaises(ProjectConfigurationError):ProjectCatalog(path,"other","s").bindings(row["id"])


class GitTests(unittest.TestCase):
    def test_only_credential_free_github_gitlab_https_repository_urls(self):
        self.assertEqual(git.repository_url("https://github.com/owner/repository"),"https://github.com/owner/repository.git")
        self.assertEqual(git.repository_url("https://gitlab.com/group/team/repository.git"),"https://gitlab.com/group/team/repository.git")
        for value in ("http://github.com/a/b","https://token@github.com/a/b","https://github.com/a/b?token=secret",
                      "file:///x","https://other.example/a/b","https://github.com/a/../b","https://github.com/a/b/tree/master"):
            with self.subTest(value=value),self.assertRaises(ProjectConfigurationError):git.repository_url(value)

    def test_credentials_stay_out_of_process_arguments_and_inherited_accounts(self):
        with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",return_value=Mock(returncode=0,stdout="ok")) as run:
            git.git_command(["clone","--","https://github.com/a/b.git","target"],host="github.com",token="fixture-secret")
            command=run.call_args.args[0];env=run.call_args.kwargs["env"]
            self.assertNotIn("fixture-secret"," ".join(command))
            self.assertEqual(env["GIT_TERMINAL_PROMPT"],"0")
            self.assertEqual(env["GIT_CONFIG_GLOBAL"],os.devnull)
            self.assertEqual(env["GIT_CONFIG_VALUE_0"],"")
            self.assertTrue(env["GIT_CONFIG_VALUE_1"].startswith("Authorization: Basic "))

    def test_clone_refuses_existing_target_before_starting_git(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(git,"git_command") as run:
            with self.assertRaises(ProjectConfigurationError):git.clone_repository("https://github.com/a/b",folder)
            run.assert_not_called()

    def test_git_errors_and_timeouts_do_not_expose_remote_output(self):
        with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",return_value=Mock(returncode=1,stdout="",stderr="private-secret")):
            with self.assertRaises(ProjectConfigurationError) as error:git.git_command(["status"])
            self.assertNotIn("private-secret",str(error.exception))
        with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",side_effect=subprocess.TimeoutExpired("git",1)):
            with self.assertRaisesRegex(ProjectConfigurationError,"time limit"):git.git_command(["status"])

    @unittest.skipUnless(shutil.which("git"),"Git executable")
    def test_actual_local_git_clone_sync_and_dirty_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);origin=base/"origin.git";seed=base/"seed";target=base/"checkout"
            env=os.environ.copy();env.update({"GIT_CONFIG_GLOBAL":os.devnull,"GIT_CONFIG_NOSYSTEM":"1","GIT_TERMINAL_PROMPT":"0"})
            def run(args,cwd=None):
                result=subprocess.run(["git","-c","maintenance.auto=false","-c","gc.auto=0","-c","core.fsmonitor=false","-c","user.name=Fixture","-c","user.email=fixture@example.invalid",*args],
                                      cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30,
                                      creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                self.assertEqual(result.returncode,0,result.stderr);return result.stdout.strip()
            run(["init","--bare",str(origin)]);run(["init",str(seed)])
            (seed/"sample.txt").write_text("first");run(["add","sample.txt"],seed);run(["commit","-m","fixture"],seed)
            run(["remote","add","origin",str(origin)],seed);run(["push","-u","origin","HEAD"],seed)
            real=git.git_command;public="https://github.com/fixture/repository.git"
            def local_transport(args,**kwargs):
                # Only the synthetic fixture URL maps to this private local bare repository.
                if args[:2]==["clone","--"]:args=["clone","--",str(origin),args[-1]]
                if args==["remote","get-url","origin"]:return public
                return real(args,**kwargs)
            with patch.object(git,"git_command",side_effect=local_transport),patch.dict(os.environ,env,clear=True):
                cloned=git.clone_repository(public,str(target))
                self.assertEqual((target/"sample.txt").read_text(),"first")
                project={**cloned,"id":"project-"+"c"*32}
                (seed/"sample.txt").write_text("second");run(["add","sample.txt"],seed);run(["commit","-m","update"],seed);run(["push"],seed)
                self.assertTrue(git.synchronize_repository(project)["synced"])
                self.assertEqual((target/"sample.txt").read_text(),"second")
                (target/"sample.txt").write_text("local edit")
                with self.assertRaisesRegex(ProjectConfigurationError,"local changes"):git.synchronize_repository(project)
                self.assertEqual((target/"sample.txt").read_text(),"local edit")
            import gc,time
            gc.collect();time.sleep(.3)


class SmartProjectUITests(fixtures.ProjectUITests):
    # ProjectUITests' fixtures use a synthetic graph and temporary scoped databases.
    def test_first_load_is_empty_and_projects_are_only_in_composer(self):
        self.app.run();self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state.get("selected_project_id",""))
        self.assertFalse(self.app.session_state["chat_opened"])
        self.assertFalse(any(w.key=="project_picker" for w in self.app.selectbox))
        self.assertTrue(any(e.proto.popover.label=="Projects" for e in self.app.container(key="message_composer").get("popover")))
        self.assertFalse(any(e.proto.popover.label=="Projects" for e in self.app.sidebar.get("popover")))
        self.assertTrue(any(b.key=="create_new_chat" for b in self.app.container(key="sidebar_chat_actions").button))
        self.assertTrue(any(e.proto.popover.label=="Search chats" for e in self.app.container(key="sidebar_chat_actions").get("popover")))
        self.assertEqual(self.invocations,[])

    def test_source_filter_does_not_activate_a_project(self):
        self.base.project_store().configure_git(self.pa["id"],"https://github.com/fixture/project")
        self.app.run()
        self.app.segmented_control(key="project_source_filter").set_value("Git").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any(b.key=="choose_project_"+self.pa["id"] for b in self.app.button))
        self.assertFalse(any(b.key=="choose_project_"+self.pb["id"] for b in self.app.button))
        self.assertFalse(self.app.session_state.get("selected_project_id",""))
        self.assertEqual(self.invocations,[])

    def test_folder_browse_keeps_name_and_saves_selected_folder(self):
        source=self.root/"browser-project";source.mkdir();(source/"keep.txt").write_text("keep")
        self.app.run();self.app.button(key="add_project_menu").click().run()
        self.app.text_input(key="new_project_name").set_value("Browsed project")
        self.app.button(key="choose_local_folder").click().run()
        self.assertFalse(self.app.exception)
        self.app.session_state["folder_browser_path"]=str(source)
        self.app.run();self.app.button(key="use_browsed_folder").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input(key="new_project_name").value,"Browsed project")
        self.assertEqual(self.app.text_input(key="new_project_folder").value,str(source))
        self.app.button(key="save_local_project").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.base.project_store().get(self.app.session_state["selected_project_id"])["root"],str(source))
        self.assertEqual((source/"keep.txt").read_text(),"keep")
        self.assertEqual(self.invocations,[])

    def test_connections_mcp_controls_are_disabled_and_no_requests_are_made(self):
        with patch("requests.get") as request:
            self.app.run();self.app.button(key="open_settings").click().run()
            self.assertFalse(self.app.exception)
            for label in ("Jira MCP","GitHub MCP","Custom MCP server"):
                self.assertTrue(self.app.button(key="parked_"+label).disabled)
            request.assert_not_called()
        self.assertEqual(self.invocations,[])

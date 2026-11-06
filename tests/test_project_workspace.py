"""Smart Projects UI and free-only repository setup; all data is temporary."""
import os
from contextlib import closing,contextmanager
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

    def test_jira_profile_is_local_only_and_other_mcp_stays_parked(self):
        with tempfile.TemporaryDirectory() as folder,patch("requests.get") as request:
            support=WorkspaceSupport();support.user="u";support.space="s"
            database=Path(folder)/"workspace.sqlite3"
            support.connection_store=lambda:ConnectionCatalog(database,"u","s")
            jira=support.save_connection("jira_mcp","Work Jira","https://example.atlassian.net")
            self.assertEqual(jira["kind"],"jira_mcp")
            self.assertEqual(jira["endpoint"],"https://mcp.atlassian.com/v2/mcp")
            self.assertEqual(jira["details"]["jira_site_url"],"https://example.atlassian.net")
            self.assertFalse(jira["credential_present"])
            for kind in ("github_mcp","custom_mcp"):
                with self.assertRaisesRegex(ProjectConfigurationError,"parked"):support.save_connection(kind,"MCP")
            for bad_url in ("","http://example.atlassian.net","https://example.com","https://user:pw@example.atlassian.net","https://example.atlassian.net:bad"):
                with self.subTest(jira_url=bad_url),self.assertRaisesRegex(ProjectConfigurationError,"Jira site URL"):
                    support.save_connection("jira_mcp","Bad URL",bad_url)
            with self.assertRaisesRegex(ProjectConfigurationError,"do not accept API tokens"):
                support.save_connection("jira_mcp","Bad profile",token="not-stored")
            from integrations.mcp.connections import discover
            with self.assertRaisesRegex(ProjectConfigurationError,"parked"):discover("https://example.org/mcp")
            request.assert_not_called()

    def test_jira_profile_connect_test_is_explicit_and_site_scoped(self):
        from contextlib import asynccontextmanager
        from integrations.jira import jira_mcp_client
        from tests.test_jira_mcp_storage import run_storage_coroutine
        with tempfile.TemporaryDirectory() as folder:
            support=WorkspaceSupport();support.user="u";support.space="s"
            database=Path(folder)/"connections.sqlite3"
            support.connection_store=lambda:ConnectionCatalog(database,"u","s")
            profile=support.save_connection("jira_mcp","Work Jira","https://example.atlassian.net")
            captured={}
            @asynccontextmanager
            async def session(*,token_storage=None,jira_site_url=None):
                captured.update(storage=token_storage,site=jira_site_url)
                yield object()
            async def accessible(session,*,jira_site_url=None):
                captured["verified_site"]=jira_site_url
                return "fixture-cloud-id"
            with patch.object(jira_mcp_client,"jira_session",side_effect=session), \
                 patch.object(jira_mcp_client,"get_cloud_id",side_effect=accessible), \
                 patch("asyncio.run",side_effect=run_storage_coroutine):
                checked=support.test_connection(profile["id"])
            self.assertEqual(checked["status"],"verified")
            self.assertEqual(checked["details"],{"jira_site_url":"https://example.atlassian.net","cloud_id":"fixture-cloud-id"})
            self.assertEqual(captured["site"],"https://example.atlassian.net")
            self.assertEqual(captured["verified_site"],"https://example.atlassian.net")
            self.assertIsInstance(captured["storage"],jira_mcp_client.CatalogOAuthTokenStorage)

    def test_jira_project_binding_is_project_scoped_and_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            support=WorkspaceSupport();support.user="u";support.space="s"
            database=Path(folder)/"workspace.sqlite3"
            catalog=ProjectCatalog(database,"u","s")
            connections=ConnectionCatalog(database,"u","s")
            support.project_store=lambda:catalog
            support.connection_store=lambda:connections
            first_root=Path(folder)/"first";second_root=Path(folder)/"second"
            first_root.mkdir();second_root.mkdir()
            first=catalog.add_local("First",str(first_root));second=catalog.add_local("Second",str(second_root))
            profile=support.save_connection("jira_mcp","Work Jira","https://example.atlassian.net")
            second_profile=support.save_connection("jira_mcp","Personal Jira","https://personal.atlassian.net")
            support.assign_connection(first["id"],"jira_mcp",profile["id"],{"project_key":"DEMO"})
            support.assign_connection(second["id"],"jira_mcp",second_profile["id"],{"project_key":"OTHER"})
            self.assertEqual(catalog.bindings(first["id"])["jira_mcp"],
                             {"connection_id":profile["id"],"options":{"project_key":"DEMO"}})
            self.assertEqual(catalog.bindings(second["id"])["jira_mcp"],
                             {"connection_id":second_profile["id"],"options":{"project_key":"OTHER"}})
            for invalid in ("demo","A-B","",None):
                with self.subTest(project_key=invalid),self.assertRaises(ProjectConfigurationError):
                    support.assign_connection(first["id"],"jira_mcp",profile["id"],{"project_key":invalid})
            with self.assertRaisesRegex(ProjectConfigurationError,"saved Jira MCP profile"):
                support.assign_connection(first["id"],"jira_mcp","connection-other-workspace",{"project_key":"DEMO"})
            support.remove_connection_assignment(first["id"],"jira_mcp")
            self.assertNotIn("jira_mcp",catalog.bindings(first["id"]))

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


@contextmanager
def temporary_git_workspace():
    """Retry only transient Windows sharing locks on this owned fixture."""
    import time
    temporary=tempfile.TemporaryDirectory()
    target=Path(temporary.name).resolve()
    parent=Path(tempfile.gettempdir()).resolve()
    if target==parent or not target.is_relative_to(parent):
        raise RuntimeError("Unexpected temporary Git workspace location.")
    try:
        yield temporary.name
    finally:
        for attempt in range(6):
            try:
                temporary.cleanup()
                break
            except PermissionError as error:
                if getattr(error,"winerror",None) not in {32,33} or attempt==5:raise
                time.sleep(.25*(attempt+1))


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

    def test_private_access_failures_are_actionable_and_never_echo_remote_secrets(self):
        for message in ("fatal: could not read Username for https://secret@github.com: terminal prompts disabled",
                        "remote: Repository not found. private-secret",
                        "fatal: Authentication failed for private-secret"):
            with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",return_value=Mock(returncode=128,stdout="",stderr=message)):
                with self.assertRaises(ProjectConfigurationError) as error:
                    git.git_command(["clone","--","https://github.com/owner/private.git","target"],host="github.com")
                self.assertIn("Settings → Connections",str(error.exception))
                self.assertIn("Repository access",str(error.exception))
                self.assertNotIn("private-secret",str(error.exception))
                self.assertNotIn("secret@",str(error.exception))
        with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",return_value=Mock(returncode=128,stdout="",stderr="fatal: Authentication failed private-secret")):
            with self.assertRaises(ProjectConfigurationError) as error:
                git.git_command(["pull"],host="github.com",token="fixture-token")
            self.assertIn("selected account",str(error.exception))
            self.assertNotIn("fixture-token",str(error.exception))
            self.assertNotIn("private-secret",str(error.exception))

    def test_network_failure_is_not_misreported_as_missing_authentication(self):
        with patch.object(shutil,"which",return_value="git"),patch.object(subprocess,"run",return_value=Mock(returncode=128,stdout="",stderr="fatal: unable to access private-secret: Could not resolve host: github.com")):
            with self.assertRaises(ProjectConfigurationError) as error:git.git_command(["clone"],host="github.com")
            self.assertIn("network",str(error.exception))
            self.assertNotIn("add a GitHub",str(error.exception))
            self.assertNotIn("private-secret",str(error.exception))

    @unittest.skipUnless(shutil.which("git"),"Git executable")
    def test_actual_local_git_clone_sync_and_dirty_protection(self):
        with temporary_git_workspace() as folder:
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
        self.assertTrue(any(b.key=="projects_menu" for b in self.app.container(key="message_composer").button))
        self.assertFalse(any(e.proto.popover.label=="Projects" for e in self.app.get("popover")))
        self.assertFalse(any(e.proto.popover.label=="Projects" for e in self.app.sidebar.get("popover")))
        self.assertTrue(any(b.key=="create_new_chat" for b in self.app.container(key="sidebar_chat_actions").button))
        self.assertTrue(any(e.proto.popover.label=="Search chats" for e in self.app.container(key="sidebar_chat_actions").get("popover")))
        self.assertEqual(self.invocations,[])

    def test_saved_projects_mix_sources_without_filters_and_close_on_selection(self):
        self.base.project_store().configure_git(self.pa["id"],"https://github.com/fixture/project")
        self.app.run();self.open_projects()
        self.assertTrue(any(b.key=="choose_project_"+self.pa["id"] for b in self.app.button))
        self.assertTrue(any(b.key=="choose_project_"+self.pb["id"] for b in self.app.button))
        self.assertFalse(any(w.key=="project_source_filter" for w in self.app.segmented_control))
        self.assertFalse(self.app.session_state.get("selected_project_id",""))
        self.assertEqual(self.app.button(key="choose_project_"+self.pa["id"]).proto.icon,":material/account_tree:")
        self.assertEqual(self.app.button(key="choose_project_"+self.pb["id"]).proto.icon,":material/folder:")
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertIsNone(self.app.session_state["ui_dialog"])
        self.open_projects()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertIsNone(self.app.session_state["ui_dialog"])
        self.assertEqual(self.invocations,[])

    def test_one_panel_back_navigation_and_setup_fields_survive(self):
        self.app.run();self.open_projects()
        self.app.button(key="add_project_menu").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.get("dialog")),1)
        self.assertFalse(any(e.proto.popover.label=="Projects" for e in self.app.get("popover")))
        self.app.text_input(key="new_project_name").set_value("Keep this name").run()
        self.app.button(key="back_saved_projects").click().run()
        self.assertTrue(any(b.key=="choose_project_"+self.pa["id"] for b in self.app.button))
        self.app.button(key="add_project_menu").click().run()
        self.assertEqual(self.app.text_input(key="new_project_name").value,"Keep this name")
        self.app.segmented_control(key="setup_project_type").set_value("Git repositories").run()
        self.app.text_input(key="git_project_name").set_value("Git fixture").run()
        self.app.text_input(key="git_repository_url").set_value("https://github.com/fixture/example").run()
        self.app.button(key="choose_git_destination").click().run()
        self.assertEqual(len(self.app.get("dialog")),1)
        self.app.button(key="cancel_folder_browser").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.segmented_control(key="setup_project_type").value,"Git repositories")
        self.assertEqual(self.app.text_input(key="git_project_name").value,"Git fixture")
        self.assertEqual(self.app.text_input(key="git_repository_url").value,"https://github.com/fixture/example")
        self.assertEqual(self.invocations,[])

    def test_sidebar_retains_controls_and_shows_only_selected_project_sessions(self):
        ca=self.view_a.create_chat("Saved Alpha conversation")
        cb=self.view_b.create_chat("Saved Beta conversation")
        self.app.run();self.open_projects()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertTrue(any(b.key=="create_new_chat" for b in self.app.sidebar.button))
        self.assertTrue(any(b.key=="open_chat_"+ca for b in self.app.sidebar.button))
        self.assertFalse(any(b.key=="open_chat_"+cb for b in self.app.sidebar.button))
        self.assertFalse(self.app.session_state["chat_opened"])
        self.assertTrue(any(c.value=="Chats and tasks · Project A" for c in self.app.sidebar.caption))
        self.open_projects();self.app.button(key="choose_project_"+self.pb["id"]).click().run()
        self.assertTrue(any(b.key=="open_chat_"+cb for b in self.app.sidebar.button))
        self.assertFalse(any(b.key=="open_chat_"+ca for b in self.app.sidebar.button))
        self.assertTrue(any(b.key=="open_memory" for b in self.app.sidebar.button))
        self.assertTrue(any(b.key=="open_settings" for b in self.app.sidebar.button))
        self.assertEqual(self.invocations,[])

    def test_chat_button_restores_earlier_list_without_merging_or_opening_a_chat(self):
        self.base.catalog.register("default")
        self.base.catalog.append("default","Earlier question","Earlier answer")
        old=self.base.create_chat("Existing unscoped chat")
        ca=self.view_a.create_chat("Project-only conversation")
        self.app.run();self.open_projects()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertTrue(any(b.key=="open_chat_"+ca for b in self.app.sidebar.button))
        self.assertFalse(any(b.key=="open_chat_"+old for b in self.app.sidebar.button))
        self.app.button(key="chat_mode").click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state["selected_project_id"])
        self.assertFalse(self.app.session_state["chat_opened"])
        self.assertTrue(any(b.key=="open_chat_"+old for b in self.app.sidebar.button))
        self.assertTrue(any(b.key=="open_chat_default" for b in self.app.sidebar.button))
        self.assertFalse(any(b.key=="open_chat_"+ca for b in self.app.sidebar.button))
        self.app.button(key="open_chat_default").click().run()
        self.assertTrue(any(m.value=="Earlier answer" for m in self.app.markdown))
        session=self.app.session_state["active_chat"]
        self.app.button(key="chat_mode").click().run()
        self.assertEqual(self.app.session_state["active_chat"],session)
        self.open_projects();self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertTrue(any(b.key=="open_chat_"+ca for b in self.app.sidebar.button))
        self.assertEqual(self.invocations,[])

    def test_same_named_projects_show_their_distinct_roots(self):
        self.base.add_project("Project A",str(self.root))
        self.app.run();self.open_projects()
        paths={c.value for c in self.app.caption}
        self.assertIn(str(self.a.resolve()),paths)
        self.assertIn(str(self.root.resolve()),paths)
        self.assertEqual(self.invocations,[])

    def test_empty_project_sidebar_is_clear_and_new_chat_remains_available(self):
        self.app.run();self.open_projects()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.assertTrue(any(c.value=="No chats yet. Start with New chat." for c in self.app.sidebar.caption))
        self.assertTrue(any(b.key=="create_new_chat" for b in self.app.sidebar.button))
        self.assertFalse(self.app.session_state["chat_opened"])
        self.assertEqual(self.invocations,[])

    def test_folder_browse_keeps_name_and_saves_selected_folder(self):
        source=self.root/"browser-project";source.mkdir();(source/"keep.txt").write_text("keep")
        self.app.run();self.open_projects();self.app.button(key="add_project_menu").click().run()
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

    def test_git_setup_passes_only_the_explicitly_selected_account_to_clone(self):
        self.app.run()
        with patch.dict(os.environ,{"FIXTURE_GITHUB_TOKEN":"fixture-private-token"}):
            account=self.base.save_connection("github","Private GitHub fixture",env_name="FIXTURE_GITHUB_TOKEN")
            self.open_projects();self.app.button(key="add_project_menu").click().run()
            self.app.segmented_control(key="setup_project_type").set_value("Git repositories").run()
            self.assertEqual(self.app.selectbox(key="git_project_account").value,"")
            self.app.selectbox(key="git_project_account").set_value(account["id"]).run()
            self.app.text_input(key="git_project_name").set_value("Private project")
            self.app.text_input(key="git_repository_url").set_value("https://github.com/fixture/private")
            target=self.root/"private-checkout";target.mkdir()
            self.app.text_input(key="git_destination").set_value(str(target))
            with patch.object(git,"clone_repository",return_value={"root":str(target),"source":"git","remote_url":"https://github.com/fixture/private.git"}) as clone:
                self.app.button(key="save_git_project").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(clone.call_args.kwargs["token"],"fixture-private-token")
            selected=self.app.session_state["selected_project_id"]
            project=self.base.project_store().get(selected)
            self.assertEqual(project["account_id"],account["id"])
            self.assertEqual(project["source"],"git")
            self.assertNotIn("fixture-private-token",str(self.base.connection_store().list()))
            self.assertNotIn("fixture-private-token",str([m.value for m in self.app.markdown]))
            self.assertEqual(self.invocations,[])

    def test_jira_profile_setup_is_local_and_other_mcp_controls_are_disabled(self):
        with patch("requests.get") as request:
            self.app.run();self.app.button(key="open_settings").click().run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any(f.key=="save_jira_mcp_profile" for f in self.app.get("form")))
            for label in ("GitHub MCP","Custom MCP server"):
                self.assertTrue(self.app.button(key="parked_"+label).disabled)
            self.app.text_input(key="jira_mcp_label").set_value("Work Jira")
            self.app.text_input(key="jira_mcp_url").set_value("https://example.atlassian.net")
            self.app.button(key="save_jira_mcp_profile-Submit").click().run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any(m.value=="Jira profile saved locally. No Jira request was made." for m in self.app.success))
            request.assert_not_called()
        self.assertEqual(self.invocations,[])

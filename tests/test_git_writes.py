"""Owned local Git repositories verify approvals without publishing user code."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from integrations.git import writes
from integrations.git.repositories import git_command
from agent.storage.projects import ProjectConfigurationError
from agent.actions.browser import BrowserActions
from agent.actions.receipts import ActionBlocked
from agent.tools.project_tools import ProjectTools
from tests.test_project_workspace import temporary_git_workspace
from tests import test_projects as fixtures


def seed(root):
    git_command(["init","-b","main",str(root)])
    git_command(["config","user.name","Fixture"],cwd=root)
    git_command(["config","user.email","fixture@example.invalid"],cwd=root)
    (root/"existing.py").write_text("value = 1\n",encoding="utf-8")
    git_command(["add","--","existing.py"],cwd=root)
    git_command(["commit","-m","Initial fixture"],cwd=root)
    git_command(["remote","add","origin","https://github.com/fixture/repository.git"],cwd=root)


class GitWriteTests(unittest.TestCase):
    def test_branch_review_creates_once_and_preserves_checkout(self):
        review = writes.prepare_branch(self.project, "codex/fixture")
        result = writes.create_branch(self.project, review)
        self.assertTrue(result["created"])
        self.assertEqual(git_command(["symbolic-ref", "--short", "HEAD"], cwd=self.root), "main")
        self.assertEqual(git_command(["rev-parse", "refs/heads/codex/fixture"], cwd=self.root), self.before)
        with self.assertRaises(ProjectConfigurationError):
            writes.create_branch(self.project, review)

    def test_branch_approval_is_owned_and_replay_safe(self):
        review = writes.prepare_branch(self.project, "codex/reviewed")
        token = self.queue(review)
        with self.assertRaises(ActionBlocked):
            self.store.execute("other", "space", "chat", token)
        self.assertFalse(git_command(["for-each-ref", "--format=%(refname)", "refs/heads/codex/reviewed"], cwd=self.root))
        first, replayed = self.store.execute("u", "space", "chat", token)
        self.assertTrue(first["created"])
        second, replayed = self.store.execute("u", "space", "chat", token)
        self.assertTrue(replayed)
        self.assertEqual(first, second)

    def test_pr_preparation_binds_commits_and_diff(self):
        git_command(["checkout", "-b", "codex/pr-fixture"], cwd=self.root)
        git_command(["add", "new.py"], cwd=self.root)
        git_command(["commit", "-m", "Fixture change"], cwd=self.root)
        draft = writes.prepare_pull_request(self.project, "main", "codex/pr-fixture", "Fixture PR", "Reviewed description")
        self.assertIn("new.py", draft["diff"])
        self.assertEqual(draft["base_commit"], self.before)
        self.assertEqual(self.network_calls, [])
        with self.assertRaises(ProjectConfigurationError):
            writes.prepare_pull_request(self.project, "main", "main", "Invalid", "")

    def setUp(self):
        self.folder=temporary_git_workspace();self.base=Path(self.folder.__enter__())
        self.addCleanup(lambda:self.folder.__exit__(None,None,None))
        self.root=self.base/"work";self.remote=self.base/"remote.git"
        seed(self.root)
        git_command(["init","--bare",str(self.remote)])
        git_command(["push",str(self.remote),"HEAD:refs/heads/main"],cwd=self.root)
        self.project={"id":"project-"+"a"*32,"root":str(self.root),"source":"git",
                      "remote_url":"https://github.com/fixture/repository.git","account_id":"fixture-account"}
        self.before=git_command(["rev-parse","HEAD"],cwd=self.root)
        (self.root/"new.py").write_text("print('approved')\n",encoding="utf-8")
        self.network_calls=[]
        def transport(arguments,**kwargs):
            args=list(arguments)
            if args[0]=="ls-remote":
                self.assertEqual(args[2],self.project["remote_url"]);args[2]=str(self.remote)
                self.network_calls.append("read")
            if args[0]=="push":
                self.assertNotIn("--force",args);self.assertNotIn("--all",args)
                self.assertEqual(args[2],self.project["remote_url"]);args[2]=str(self.remote)
                self.network_calls.append("push")
            return git_command(args,**kwargs)
        self.transport=patch.object(writes,"git_command",side_effect=transport);self.transport.start();self.addCleanup(self.transport.stop)
        project=self.project
        class Tools(ProjectTools):
            def git_branch(inner,review:dict):return writes.create_branch(project,review)
            def git_commit(inner,review:dict):return writes.commit(project,review)
            def git_push(inner,review:dict):return writes.push(project,review,"fixture-token")
        self.store=BrowserActions(self.base/"receipts.sqlite3",tools_factory=Tools)

    def review(self):
        return writes.prepare_commit(self.project,["new.py"],"Add reviewed script","Chosen Author","chosen@example.invalid")

    def queue(self,review):
        return self.store.propose("u","space","chat",review["kind"],
            {"project_root":str(self.root),"action":review["kind"],"arguments":{"review":review}})

    def test_exact_files_commit_only_after_approval_and_replay_returns_receipt(self):
        (self.root/"other.py").write_text("unselected = True\n")
        review=self.review();token=self.queue(review)
        self.assertEqual(git_command(["rev-parse","HEAD"],cwd=self.root),self.before)
        result,replayed=self.store.execute("u","space","chat",token)
        self.assertTrue(result["committed"]);self.assertFalse(result["pushed"]);self.assertFalse(replayed)
        self.assertEqual(git_command(["show","--format=","--name-only","HEAD"],cwd=self.root),"new.py")
        self.assertEqual(git_command(["log","-1","--format=%an <%ae>"],cwd=self.root),"Chosen Author <chosen@example.invalid>")
        self.assertIn("other.py",git_command(["ls-files","--others","--exclude-standard"],cwd=self.root))
        self.assertNotIn("new.py",git_command(["status","--short"],cwd=self.root))
        again,replayed=self.store.execute("u","space","chat",token)
        self.assertEqual(result,again);self.assertTrue(replayed);self.assertEqual(self.network_calls,[])

    def test_decline_and_wrong_user_cannot_commit(self):
        token=self.queue(self.review())
        with self.assertRaises(ActionBlocked):self.store.execute("other","space","chat",token)
        self.store.decline("u","space","chat",token)
        with self.assertRaises(ActionBlocked):self.store.execute("u","space","chat",token)
        self.assertEqual(git_command(["rev-parse","HEAD"],cwd=self.root),self.before)

    def test_changed_file_invalidates_pending_review_before_commit(self):
        token=self.queue(self.review())
        (self.root/"new.py").write_text("changed after approval request\n")
        with self.assertRaises(ActionBlocked):self.store.execute("u","space","chat",token)
        self.assertEqual(git_command(["rev-parse","HEAD"],cwd=self.root),self.before)

    def test_existing_staged_change_and_credential_paths_are_rejected(self):
        git_command(["add","--","existing.py"],cwd=self.root)
        (self.root/"existing.py").write_text("changed = True\n")
        git_command(["add","--","existing.py"],cwd=self.root)
        with self.assertRaisesRegex(ProjectConfigurationError,"staged"):self.review()
        for name in (".env","../outside.py",".git/config","outputs/private.txt","key.pem"):
            with self.subTest(name=name),self.assertRaises(ProjectConfigurationError):writes.safe_path(self.root,name)

    def test_exact_commit_push_is_separately_approved_and_non_force(self):
        self.store.execute("u","space","chat",self.queue(self.review()))
        head=git_command(["rev-parse","HEAD"],cwd=self.root)
        self.assertEqual(git_command(["rev-parse","refs/heads/main"],cwd=self.remote),self.before)
        review=writes.prepare_push(self.project,"fixture-token");token=self.queue(review)
        self.assertNotIn("fixture-token",json.dumps(review));self.assertNotIn("push",self.network_calls)
        result,replayed=self.store.execute("u","space","chat",token)
        self.assertTrue(result["pushed"]);self.assertFalse(replayed)
        self.assertEqual(git_command(["rev-parse","refs/heads/main"],cwd=self.remote),head)
        self.assertEqual(self.network_calls.count("push"),1)
        self.store.execute("u","space","chat",token)
        self.assertEqual(self.network_calls.count("push"),1)

    def test_missing_push_account_is_actionable_without_network(self):
        with self.assertRaisesRegex(ProjectConfigurationError,"write access"):
            writes.prepare_push({**self.project,"account_id":""},"")
        self.assertEqual(self.network_calls,[])

    def test_remote_change_blocks_old_push_without_overwriting_it(self):
        self.store.execute("u","space","chat",self.queue(self.review()))
        review=writes.prepare_push(self.project,"fixture-token");token=self.queue(review)
        tree=git_command(["rev-parse",self.before+"^{tree}"],cwd=self.root)
        other=git_command(["-c","user.name=Other","-c","user.email=other@example.invalid","commit-tree",tree,"-p",self.before,"-m","External change"],cwd=self.remote)
        git_command(["update-ref","refs/heads/main",other,self.before],cwd=self.remote)
        with self.assertRaises(ProjectConfigurationError):self.store.execute("u","space","chat",token)
        self.assertEqual(git_command(["rev-parse","refs/heads/main"],cwd=self.remote),other)
        self.assertNotIn("push",self.network_calls)
        with patch("integrations.git.repositories.git_command",side_effect=writes.git_command):
            with self.assertRaisesRegex(ActionBlocked,"Remote branch changed"):
                self.store.reconcile_git_push_review("u","space",review,credential="fixture-token")
        self.assertEqual(self.store.receipts.get(token)["status"],"uncertain")

    def test_large_old_blob_stops_review_before_loading_content(self):
        (self.root/"existing.py").write_text("x"*(writes.LIMIT+1),encoding="utf-8")
        git_command(["add","--","existing.py"],cwd=self.root)
        git_command(["commit","-m","Large old fixture"],cwd=self.root)
        (self.root/"existing.py").write_text("small = True\n",encoding="utf-8")
        with self.assertRaisesRegex(ProjectConfigurationError,"original file is too large"):
            writes.prepare_commit(self.project,["existing.py"],"Small replacement","Author","a@example.invalid")
        self.assertEqual(self.network_calls,[])

    def test_push_transport_failure_reports_uncertainty_without_false_no_push_claim(self):
        import subprocess
        from integrations.git import repositories
        completed=subprocess.CompletedProcess([],1,"","failed to connect")
        with patch.object(repositories.subprocess,"run",return_value=completed):
            with self.assertRaisesRegex(ProjectConfigurationError,"Push was not confirmed") as error:
                repositories.git_command(["push","--porcelain","https://github.com/fixture/repository.git","a:refs/heads/main"],
                                         host="github.com",token="fixture-token",cwd=self.root)
        self.assertNotIn("no push was performed",str(error.exception).casefold())

    def test_failed_push_reconciles_only_after_remote_check_and_needs_new_approval(self):
        self.store.execute("u","space","chat",self.queue(self.review()))
        review=writes.prepare_push(self.project,"fixture-token");old=self.queue(review)
        with patch.object(writes,"push",side_effect=ProjectConfigurationError("Permission rejected")):
            with self.assertRaises(ProjectConfigurationError):self.store.execute("u","space","chat",old)
        self.assertEqual(self.store.receipts.get(old)["status"],"uncertain")
        duplicate=self.queue(review)
        with self.assertRaises(ActionBlocked):self.store.execute("u","space","chat",duplicate)
        self.assertEqual(self.store.reconcile_git_push_review("other","space",review),[])
        with self.store.receipts.connect() as db:db.execute("UPDATE actions SET status='running' WHERE id=?",(old,))
        self.assertEqual(self.store.reconcile_git_push_review("u","space",review),[])
        with self.store.receipts.connect() as db:db.execute("UPDATE actions SET status='uncertain' WHERE id=?",(old,))
        with patch("integrations.git.repositories.git_command",side_effect=writes.git_command):
            recovered=self.store.reconcile_git_push_review("u","space",review,credential="fixture-token")
        self.assertEqual(set(recovered),{old,duplicate})
        self.assertEqual(self.store.receipts.get(old)["status"],"reconciled_not_applied")
        self.assertEqual(self.network_calls.count("push"),0)
        self.assertEqual(git_command(["rev-parse","refs/heads/main"],cwd=self.remote),self.before)
        with self.assertRaises(ActionBlocked):self.store.execute("u","space","chat",old)
        with self.store.receipts.connect() as db:
            audit=json.loads(db.execute("SELECT evidence FROM git_push_reconciliations WHERE receipt_id=?",(old,)).fetchone()[0])
        self.assertEqual(audit["observed_remote_tip"],self.before)
        self.assertNotIn("fixture-token",json.dumps(audit))
        fresh=self.queue(writes.prepare_push(self.project,"fixture-token"))
        self.assertEqual(self.network_calls.count("push"),0)
        result,replayed=self.store.execute("u","space","chat",fresh)
        self.assertTrue(result["pushed"]);self.assertFalse(replayed)
        self.assertEqual(self.network_calls.count("push"),1)

    def test_workspace_writes_are_not_generic_model_tools(self):
        from agent.policies.tool_registry import WORKSPACE_CONTROLLED_ACTIONS,PROJECT_ACTIONS,CONVERSATION_ACTIONS
        self.assertEqual(WORKSPACE_CONTROLLED_ACTIONS,{"git_commit","git_push"})
        self.assertFalse(WORKSPACE_CONTROLLED_ACTIONS & (PROJECT_ACTIONS|CONVERSATION_ACTIONS))
        with self.assertRaises(ActionBlocked):
            BrowserActions(self.base/"plain.sqlite3").propose("u","space","chat","git_commit",
                {"project_root":str(self.root),"action":"git_commit","arguments":{"review":self.review()}})


class GitIntentTests(unittest.TestCase):
    def test_natural_create_requests_route_to_project_without_model(self):
        from agent.langgraph.langgraph_agent import router_node
        for question in ("can you reate a nagatest.py file under project root and commit and push if possible",
                         "atleast add this file","please save notes.txt in the project root"):
            with self.subTest(question=question):
                self.assertEqual(router_node({"question":question})["route"],"project")

    def test_quoted_copied_instructions_and_author_metadata_choose_requested_action(self):
        from agent.policies.routing import git_write_mode
        cases={
            "“Push this branch.” Review and approve separately.":"Push",
            "“Commit these changes.” Select nagatest.py, enter author/message, review and approve.":"Commit",
            'the author name: Test Author and commit message: test message, you would like to use for committing nagatest.py.\n\n“Push this branch.” Review and approve separately.':"Push",
            "Commit nagatest.py and push this branch":"Commit",
            "“Why can't I push?”":None,
            "Do not push this branch.":None,
            "Create new.py then commit and push":None,
        }
        for question,expected in cases.items():
            with self.subTest(question=question):self.assertEqual(git_write_mode(question),expected)

    def test_git_review_intent_excludes_explanations_uploads_and_prohibitions(self):
        from agent.policies.routing import is_git_write_request
        from agent.interfaces.attachments import attachment_question
        for question in ("Commit these changes","Can you push this branch?","git push"):
            self.assertTrue(is_git_write_request(question),question)
        for question in ("Why can't I push?","What is git push?","Do not push anything.",
                         "Create new.py then commit and push",
                         attachment_question("Summarize this document",[{"name":"a.txt","text":"git push","truncated":False}])):
            self.assertFalse(is_git_write_request(question),question)


class GitCommandProposalTests(unittest.TestCase):
    def test_invalid_git_commands_are_rejected_before_proposal_without_execution(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);store=BrowserActions(root/"actions.sqlite3")
            for action,args in (
                ("run_command",{"command":["git","push"],"timeout":60}),
                ("run_tests_and_parse",{"command":["git","push"],"relative_report_folder":"reports","timeout":60})):
                with self.subTest(action=action),patch("agent.tools.project_tools.subprocess.run") as run:
                    with self.assertRaisesRegex(ActionBlocked,"Git review panel"):
                        store.propose("u","space","chat",action,{"project_root":str(root),"action":action,"arguments":args})
                    self.assertEqual(store.pending("u","space","chat"),[])
                    run.assert_not_called()

    def test_legacy_invalid_approval_is_blocked_without_uncertain_receipt_or_execution(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);store=BrowserActions(root/"actions.sqlite3")
            proposal={"project_root":str(root),"action":"run_command","arguments":{"command":["git","push"],"timeout":60}}
            # Emulate a pending proposal persisted by the old adapter.
            with patch.object(BrowserActions,"_validate_command"):
                token=store.propose("u","space","chat","run_command",proposal)
            with patch("agent.tools.project_tools.subprocess.run") as run:
                with self.assertRaisesRegex(ActionBlocked,"Git review panel"):
                    store.execute("u","space","chat",token)
                run.assert_not_called()
            self.assertEqual(store._row("u","space","chat",token)["status"],"blocked")
            self.assertIsNone(store.receipts.get(token))

    def test_valid_command_preview_never_executes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);store=BrowserActions(root/"actions.sqlite3")
            with patch("agent.tools.project_tools.subprocess.run") as run:
                token=store.propose("u","space","chat","run_command",{"project_root":str(root),"action":"run_command",
                    "arguments":{"command":["python","-c","print('fixture')"],"timeout":60}})
                run.assert_not_called()
            self.assertEqual(store.pending("u","space","chat")[0]["id"],token)


class GitWriteUITests(unittest.TestCase):
    open_projects=fixtures.ProjectUITests.open_projects

    def setUp(self):
        fixtures.ProjectUITests.setUp(self)
        cleanup=self.temp.cleanup
        def retry_cleanup():
            import tempfile,time
            target=Path(self.temp.name).resolve()
            parent=Path(tempfile.gettempdir()).resolve()
            if target==parent or not target.is_relative_to(parent):raise RuntimeError("Unexpected Git fixture location.")
            for attempt in range(6):
                try:cleanup();return
                except PermissionError as error:
                    if getattr(error,"winerror",None) not in {32,33} or attempt==5:raise
                    time.sleep(.25*(attempt+1))
        self._cleanups=[(retry_cleanup,args,kwargs) if function==cleanup else (function,args,kwargs)
                        for function,args,kwargs in self._cleanups]
        seed(self.a)
        self.base.project_store().configure_git(self.pa["id"],"https://github.com/fixture/repository")
        (self.a/"new.py").write_text("print('UI approval fixture')\n")
        self.initial=git_command(["rev-parse","HEAD"],cwd=self.a)

    def test_chat_opens_review_and_approval_commits_once(self):
        self.app.run();self.open_projects();self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.app.chat_input[0].set_value("Commit these changes").run()
        self.assertFalse(self.app.exception);self.assertEqual(self.invocations,[])
        self.assertEqual(self.app.session_state["ui_dialog"],"project_git")
        self.app.multiselect(key="git_commit_paths").set_value(["new.py"])
        self.app.text_input(key="git_commit_message").set_value("UI reviewed change")
        self.app.text_input(key="git_commit_author").set_value("UI Author")
        self.app.text_input(key="git_commit_email").set_value("ui@example.invalid")
        self.app.button(key="prepare_git_commit").click().run()
        self.assertFalse(self.app.exception)
        self.app.button(key="request_git_approval").click().run()
        self.assertFalse(self.app.exception);self.assertEqual(git_command(["rev-parse","HEAD"],cwd=self.a),self.initial)
        approve=next(button for button in self.app.button if str(button.key).startswith("approve_"))
        approve.click().run();self.assertFalse(self.app.exception)
        committed=git_command(["rev-parse","HEAD"],cwd=self.a)
        self.assertNotEqual(committed,self.initial)
        self.app.run();self.assertEqual(git_command(["rev-parse","HEAD"],cwd=self.a),committed)
        self.assertEqual(self.invocations,[])
        self.app.chat_input[0].set_value("i will approve").run()
        self.assertFalse(self.app.exception);self.assertEqual(self.invocations,[])
        answer=self.base.for_project(self.pa["id"]).turns(self.app.session_state["active_chat"])[-1]["answer"]
        self.assertIn("No push has been queued or confirmed",answer)
        self.assertIn("A chat message does not approve",answer)

    def test_quoted_push_after_author_details_opens_push_review_without_model_or_approval(self):
        self.app.run();self.open_projects();self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        question='the author name: Test Author and commit message: test message, you would like to use for committing nagatest.py.\n\n“Push this branch.” Review and approve separately.'
        self.app.chat_input[0].set_value(question).run()
        self.assertFalse(self.app.exception);self.assertEqual(self.invocations,[])
        self.assertEqual(self.app.session_state["ui_dialog"],"project_git")
        self.assertEqual(self.app.session_state["git_review_mode"],"Push")
        self.app.button(key="prepare_git_push").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("write access" in warning.value for warning in self.app.warning))
        self.assertFalse(any(str(button.key).startswith("approve_") for button in self.app.button))
        self.assertEqual(self.invocations,[])


    def test_push_panel_selects_saved_provider_account_only_for_selected_project(self):
        import os
        with patch.dict(os.environ,{"GIT_ACCOUNT_FIXTURE":"fixture-only"}):
            account=self.base.save_connection("github","GitHub fixture",env_name="GIT_ACCOUNT_FIXTURE")
            other=self.base.save_connection("gitlab","Other provider",env_name="GIT_ACCOUNT_FIXTURE")
            self.app.run();self.open_projects();self.app.button(key="choose_project_"+self.pa["id"]).click().run()
            self.app.chat_input[0].set_value("Push this branch").run()
            self.assertFalse(self.app.exception)
            picker=self.app.selectbox(key="git_push_account_"+self.pa["id"])
            self.assertNotIn("Other provider",picker.options)
            self.assertIn("GitHub fixture",picker.options)
            picker.set_value(account["id"]).run()
            with patch("integrations.git.writes.git_command",wraps=writes.git_command) as git:
                self.app.button(key="git_push_save_account").click().run()
                self.assertFalse(self.app.exception)
                self.assertFalse(any(call.args[0][0] in {"push","ls-remote"} for call in git.call_args_list))
            self.assertEqual(self.base.project_store().get(self.pa["id"])["account_id"],account["id"])
            self.assertEqual(self.base.project_store().get(self.pb["id"])["account_id"],"")
            self.assertEqual(self.invocations,[])

    def test_status_followup_does_not_cross_chat_or_capture_technical_explanations(self):
        from agent.runtime.git_workspace import git_status_reply
        backend=self.base.for_project(self.pa["id"])
        first=backend.create_chat("Git review chat");second=backend.create_chat("Unrelated chat")
        backend.submit(first,"Push this branch")
        answer=backend.submit(first,"i will approve")
        self.assertIn("No Git action has been queued or confirmed",answer["answer"])
        self.assertEqual(self.invocations,[])
        self.assertIsNone(git_status_reply(backend,second,"i will approve"))
        self.assertIsNone(git_status_reply(backend,first,"Explain committed transactions in Java"))
        self.assertIsNone(git_status_reply(backend,first,"How does git push work?"))


        actions=backend.actions()
        proposal=json.dumps({"action":"git_push"})
        result=json.dumps({"pushed":True,"commit":"a"*40,"branch":"main","remote_url":"https://github.com/fixture/repository.git"})
        with actions.receipts.connect() as db:
            db.execute("INSERT INTO browser_proposals VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("fixture-push",backend.user,backend.space,first,proposal,"fixture",None,"pending",actions.clock()+600,None))
        pending=backend.submit(first,"i will approve")["answer"]
        self.assertIn("waiting for its exact-action approval",pending)
        self.assertIn("It has not executed",pending)
        with actions.receipts.connect() as db:db.execute("UPDATE browser_proposals SET status='uncertain' WHERE id='fixture-push'")
        self.assertIn("running or uncertain",backend.submit(first,"push status")["answer"])
        with actions.receipts.connect() as db:db.execute("UPDATE browser_proposals SET status='completed',result=? WHERE id='fixture-push'",(result,))
        confirmed=backend.submit(first,"how to confirm")["answer"]
        self.assertIn("Saved receipt confirms push of "+"a"*40,confirmed)
        self.assertIn("no fresh remote check",confirmed)
        self.assertIn("No Git action has been queued or confirmed",git_status_reply(backend,second,"push status")["answer"])
        self.assertEqual(self.invocations,[])

"""Expired file reviews remain visible and refresh without execution or models."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.actions.browser import BrowserActions
from agent.actions.downloads import read_created_file
from agent.actions.receipts import ActionBlocked, canonical
from tests import test_browser_action_ui as ui_fixtures, test_projects


class ExpiredFileReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.now=[100.0]
        self.store=BrowserActions(self.root/"actions.sqlite3",clock=lambda:self.now[0])
        self.proposal={"project_root":str(self.root),"action":"create_file","arguments":{"relative_path":"report.md","content":"# Historical report\nExact reviewed bytes.\n"}}
        self.old=self.store.propose("u","p","chat","create_file",self.proposal)

    def expire(self):
        self.now[0]+=601
        self.store.pending("u","p","chat")

    def test_pending_not_shown_as_expired_and_scope_is_preserved(self):
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])
        self.expire()
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[{"id":self.old,"path":"report.md","project_root":str(self.root)}])
        for user,space,chat in [("other","p","chat"),("u","other","chat"),("u","p","other")]:
            self.assertEqual(self.store.expired_file_reviews(user,space,chat),[])
            with self.assertRaises(ActionBlocked):self.store.refresh_file_review(user,space,chat,self.old)
        self.assertFalse((self.root/"report.md").exists())

    def test_refresh_preserves_exact_action_and_requires_new_explicit_approval(self):
        self.expire()
        with patch("agent.tools.project_tools.ProjectTools.create_file",autospec=True,side_effect=AssertionError("no write before approval")):
            fresh=self.store.refresh_file_review("u","p","chat",self.old)
            same=self.store.refresh_file_review("u","p","chat",self.old)
        self.assertEqual(same,fresh);self.assertNotEqual(fresh,self.old)
        pending=self.store.pending("u","p","chat");self.assertEqual(len(pending),1)
        self.assertEqual(canonical(pending[0]["proposal"]),canonical(self.proposal))
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])
        self.assertIsNone(self.store.receipts.get(self.old));self.assertIsNone(self.store.receipts.get(fresh))
        with self.assertRaises(ActionBlocked):self.store.execute("u","p","chat",self.old)
        with self.assertRaises(ActionBlocked):read_created_file(self.store,"u","p","chat",fresh)
        result,replayed=self.store.execute("u","p","chat",fresh)
        self.assertTrue(result["created"]);self.assertFalse(replayed)
        self.assertEqual(read_created_file(self.store,"u","p","chat",fresh)["data"],self.proposal["arguments"]["content"].encode("utf-8"))
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])

    def test_another_expiration_leaves_one_latest_review_not_an_endless_list(self):
        self.expire();first=self.store.refresh_file_review("u","p","chat",self.old)
        self.expire();rows=self.store.expired_file_reviews("u","p","chat")
        self.assertEqual([r["id"] for r in rows],[first])
        second=self.store.refresh_file_review("u","p","chat",first)
        self.assertNotEqual(first,second);self.assertEqual(len(self.store.pending("u","p","chat")),1)

    def test_changed_target_is_not_overwritten_or_reproposed(self):
        self.expire();(self.root/"report.md").write_text("User's new file",encoding="utf-8")
        with self.assertRaisesRegex(ActionBlocked,"target changed"):
            self.store.refresh_file_review("u","p","chat",self.old)
        self.assertEqual((self.root/"report.md").read_text(),"User's new file")
        self.assertEqual(self.store.pending("u","p","chat"),[])

    def test_tamper_or_execution_receipt_blocks_refresh(self):
        self.expire()
        with self.store.receipts.connect() as db:
            db.execute("UPDATE browser_proposals SET digest='corrupt' WHERE id=?",(self.old,))
        with self.assertRaisesRegex(ActionBlocked,"changed"):
            self.store.refresh_file_review("u","p","chat",self.old)
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])
        another=self.store.propose("u","p","chat","create_file",self.proposal)
        self.expire()
        with self.store.receipts.connect() as db:
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?,NULL)",(another,"fixture","uncertain",0,0))
        with self.assertRaisesRegex(ActionBlocked,"execution receipt"):
            self.store.refresh_file_review("u","p","chat",another)

    def test_pending_declined_and_nonfile_actions_cannot_be_refreshed(self):
        with self.assertRaisesRegex(ActionBlocked,"expired"):
            self.store.refresh_file_review("u","p","chat",self.old)
        self.store.decline("u","p","chat",self.old)
        with self.assertRaises(ActionBlocked):self.store.refresh_file_review("u","p","chat",self.old)
        command={"project_root":str(self.root),"action":"run_command","arguments":{"command":["python","-c","print('fixture')"],"timeout":1}}
        token=self.store.propose("u","p","chat","run_command",command)
        self.expire()
        with self.assertRaisesRegex(ActionBlocked,"action type"):
            self.store.refresh_file_review("u","p","chat",token)
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])

    def test_declined_new_review_hides_older_expired_duplicate(self):
        self.expire();new=self.store.refresh_file_review("u","p","chat",self.old)
        self.store.decline("u","p","chat",new)
        self.assertEqual(self.store.expired_file_reviews("u","p","chat"),[])
        with self.assertRaisesRegex(ActionBlocked,"newer review"):
            self.store.refresh_file_review("u","p","chat",self.old)


class ScopedBackendReviewTests(unittest.TestCase):
    setUp=test_projects.ProjectBackendTests.setUp

    def test_real_backend_keeps_refresh_and_listing_inside_selected_chat_project(self):
        session=self.view_a.create_chat("Expired source export")
        proposal={"project_root":str(self.a),"action":"create_file","arguments":{"relative_path":"report.md","content":"Exact report"}}
        store=self.view_a.actions();token=store.propose("u",self.view_a.space,session,"create_file",proposal)
        with store.receipts.connect() as db:db.execute("UPDATE browser_proposals SET expires=0 WHERE id=?",(token,))
        self.assertEqual(self.view_a.expired_file_reviews(session)[0]["id"],token)
        self.assertEqual(self.view_b.expired_file_reviews(session),[])
        with self.assertRaises(ActionBlocked):self.view_b.refresh_file_review(session,token)
        fresh=self.view_a.refresh_file_review(session,token)
        self.assertNotEqual(fresh,token);self.assertFalse((self.a/"report.md").exists())
        forged={**proposal,"project_root":str(self.b)}
        bad=store.propose("u",self.view_a.space,session,"create_file",forged)
        with store.receipts.connect() as db:db.execute("UPDATE browser_proposals SET expires=0 WHERE id=?",(bad,))
        self.assertFalse(any(v["id"]==bad for v in self.view_a.expired_file_reviews(session)))
        with self.assertRaisesRegex(ActionBlocked,"different project"):
            self.view_a.refresh_file_review(session,bad)


class ExpiredBackend(ui_fixtures.ActionBackend):
    def __init__(self,folder):
        super().__init__(folder);self.now=[100.0];self.store=BrowserActions(self.root/"actions.sqlite3",clock=lambda:self.now[0])
    def expired_file_reviews(self,session):return self.store.expired_file_reviews("u","p",session)
    def refresh_file_review(self,session,token):return self.store.refresh_file_review("u","p",session,token)
    def generated_files(self,session):
        from agent.actions.downloads import list_created_files
        return list_created_files(self.store,"u","p",session)
    def generated_file(self,session,token):return read_created_file(self.store,"u","p",session,token)


class ExpiredFileReviewUITests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.backend=ExpiredBackend(self.tmp.name);self.token=self.backend.propose();self.backend.now[0]+=601
        st.cache_resource.clear();self.addCleanup(st.cache_resource.clear)
        patcher=patch("agent.browser_backend.make_browser_backend",return_value=self.backend);patcher.start();self.addCleanup(patcher.stop)
        activity=patch("agent.browser_activity.log_browser_event");activity.start();self.addCleanup(activity.stop)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=15)
        self.app.session_state["active_chat"]="default";self.app.session_state["chat_opened"]=True;self.app.session_state["chat_draft"]=False

    def test_real_entrypoint_shows_expiration_refreshes_then_requires_approval_and_download(self):
        self.app.run();self.assertFalse(self.app.exception)
        self.assertTrue(any("File approval expired" in x.value for x in self.app.warning))
        self.assertFalse(any(b.label=="Approve exact action" for b in self.app.button))
        self.assertFalse((self.backend.root/"note.txt").exists())
        self.app.button(key="refresh_file_review_"+self.token).click().run()
        self.assertFalse(self.app.exception)
        fresh=self.backend.pending_actions("default")[0]["id"]
        self.assertTrue(any(b.key=="approve_"+fresh for b in self.app.button))
        self.app.run();self.assertEqual(self.backend.decisions,[])
        self.assertFalse((self.backend.root/"note.txt").exists())
        self.app.button(key="approve_"+fresh).click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.decisions,[True])
        self.app.button(key="conversation_prepare_generated_"+fresh).click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["generated_downloads"][("default",fresh)]["data"],b"draft")
        self.assertTrue(any(x.proto.label=="Download note.txt" for x in self.app.get("download_button")))
        self.app.run();self.assertEqual(self.backend.decisions,[True])
        self.assertFalse(any("File approval expired" in x.value for x in self.app.warning))

    def test_changed_target_explains_why_refresh_is_blocked_without_writing(self):
        self.app.run();(self.backend.root/"note.txt").write_text("Keep this",encoding="utf-8")
        self.app.button(key="refresh_file_review_"+self.token).click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("target changed" in x.value for x in self.app.warning))
        self.assertEqual((self.backend.root/"note.txt").read_text(),"Keep this")
        self.assertEqual(self.backend.decisions,[])


if __name__=="__main__":unittest.main()

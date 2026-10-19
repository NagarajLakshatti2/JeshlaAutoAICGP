import tempfile
import unittest
from pathlib import Path
from agent.chat_catalog import ChatCatalog, choose_chat, clean_title

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"chats.sqlite3"
        self.catalog=ChatCatalog(self.path,"u","p")

    def choose(self,replies,title=""):
        answers=iter(replies)
        return choose_chat(self.catalog,title,reader=lambda prompt:next(answers),writer=lambda text:None)

    def test_yes_variants_create_new_chat(self):
        for answer in ["Y","y","yes","YES"]:
            session=self.choose([answer,"Java learning"])
            self.assertEqual(self.catalog.get(session)["title"],"Java learning")
        self.assertEqual(len(self.catalog.list()),4)

    def test_no_variants_resume_default(self):
        for answer in ["N","n","no","NO",""]:
            self.assertEqual(self.choose([answer]),"default")
        self.assertEqual(len(self.catalog.list()),1)

    def test_empty_title_automatic(self):
        session=self.choose(["y",""])
        self.assertTrue(self.catalog.get(session)["title"].startswith("New chat "))

    def test_title_limit(self):
        self.assertEqual(clean_title("x"*100),"x"*100)
        with self.assertRaises(ValueError):clean_title("x"*101)
        session=self.choose(["y","replacement"],title="x"*101)
        self.assertEqual(self.catalog.get(session)["title"],"replacement")

    def test_duplicate_titles_have_unique_ids(self):
        self.assertNotEqual(self.catalog.create("same"),self.catalog.create("same"))

    def test_full_transcript_survives_restart(self):
        session=self.catalog.create("Long chat")
        text="a"*20000
        self.catalog.append(session,text,"answer")
        reopened=ChatCatalog(self.path,"u","p")
        self.assertEqual(reopened.transcript(session)[0]["question"],text)
        self.assertEqual(reopened.get(session)["title"],"Long chat")

    def test_user_and_space_isolation(self):
        session=self.catalog.create("private")
        self.catalog.append(session,"question","answer")
        for user,space in [("v","p"),("u","q")]:
            other=ChatCatalog(self.path,user,space)
            self.assertIsNone(other.get(session))
            self.assertEqual(other.list(),[])
            self.assertEqual(other.transcript(session),[])

    def test_invalid_confirmation_retries(self):
        self.assertEqual(self.choose(["maybe","n"]),"default")

if __name__=="__main__":unittest.main()

import tempfile,unittest
from pathlib import Path
from agent.actions.browser import BrowserActions
from agent.actions.downloads import list_created_files,read_created_file
from agent.actions.receipts import ActionBlocked

class GeneratedDownloadTests(unittest.TestCase):
    def test_only_scoped_completed_unchanged_creations_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);actions=BrowserActions(root/'actions.sqlite3')
            proposal={'project_root':str(root),'action':'create_file','arguments':{'relative_path':'export.txt','content':'Approved export'}}
            token=actions.propose('u','p','chat','create_file',proposal)
            self.assertEqual(list_created_files(actions,'u','p','chat'),[])
            with self.assertRaises(ActionBlocked):read_created_file(actions,'u','p','chat',token)
            actions.execute('u','p','chat',token)
            self.assertEqual(list_created_files(actions,'u','p','chat'),[{'id':token,'path':'export.txt'}])
            self.assertEqual(read_created_file(actions,'u','p','chat',token)['data'],b'Approved export')
            for user,space,chat in [('other','p','chat'),('u','other','chat'),('u','p','other')]:
                self.assertEqual(list_created_files(actions,user,space,chat),[])
                with self.assertRaises(ActionBlocked):read_created_file(actions,user,space,chat,token)
            (root/'export.txt').write_text('Changed content',encoding='utf-8')
            with self.assertRaises(ActionBlocked):read_created_file(actions,'u','p','chat',token)

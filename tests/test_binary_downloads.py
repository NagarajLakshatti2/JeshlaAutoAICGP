"""Owned approved PNG/ZIP delivery; only synthetic captures, never a browser."""
import base64,hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import Mock,patch
from agent.actions.browser import BrowserActions
from agent.actions.receipts import ActionBlocked,canonical
from agent.actions.downloads import list_downloadable_files,read_downloadable_file,read_created_file,zip_snapshot
from integrations.web import inspection

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j/WQAAAAASUVORK5CYII=')


class BinaryDownloadTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.actions=BrowserActions(self.root/'actions.sqlite3')

    def capture(self,execute=True):
        value={'project_root':str(self.root),'action':'inspect_browser_page',
               'arguments':{'url':'https://example.test','evidence_folder':'evidence','limit':1}}
        token=self.actions.propose('u','p','chat','inspect_browser_page',value)
        if not execute:return token,None
        worker=Mock();worker.returncode=0;worker.poll.return_value=0
        def communicate(payload,timeout):
            Path(json.loads(payload)['screenshot']).write_bytes(PNG)
            return json.dumps({'status':'inspected','fields':[]}),''
        worker.communicate.side_effect=communicate
        with patch.object(inspection.subprocess,'Popen',return_value=worker):
            result,_=self.actions.execute('u','p','chat',token)
        return token,result

    def replace_result(self,token,result):
        with self.actions.receipts.connect() as db:
            db.execute('UPDATE browser_proposals SET result=? WHERE id=?',(canonical(result),token))
            db.execute('UPDATE actions SET result=? WHERE id=?',(canonical(result),token))

    def read(self,token):return read_downloadable_file(self.actions,'u','p','chat',token)

    def test_completed_capture_downloads_exact_bytes_without_reexecution(self):
        token,result=self.capture()
        with patch.object(inspection.subprocess,'Popen',side_effect=AssertionError('no browser')):
            self.assertEqual(list_downloadable_files(self.actions,'u','p','chat'),[{'id':token,'path':result['screenshot']}])
            self.assertEqual(self.read(token),{'name':'inspection.png','data':PNG,'mime':'image/png'})
        with self.assertRaises(ActionBlocked):read_created_file(self.actions,'u','p','chat',token)

    def test_pending_or_cross_owner_capture_cannot_download(self):
        pending,_=self.capture(False)
        with self.assertRaises(ActionBlocked):self.read(pending)
        token,_=self.capture()
        for user,space,chat in [('other','p','chat'),('u','other','chat'),('u','p','other')]:
            self.assertEqual(list_downloadable_files(self.actions,user,space,chat),[])
            with self.assertRaises(ActionBlocked):read_downloadable_file(self.actions,user,space,chat,token)

    def test_legacy_capture_without_hash_is_not_backfilled(self):
        token,result=self.capture();result.pop('screenshot_sha256');result.pop('screenshot_size_bytes')
        self.replace_result(token,result)
        self.assertEqual(list_downloadable_files(self.actions,'u','p','chat'),[])
        with self.assertRaises(ActionBlocked):self.read(token)

    def test_changed_png_and_manifest_are_blocked(self):
        token,result=self.capture();path=self.root/result['screenshot'];path.write_bytes(PNG+b'changed')
        with self.assertRaises(ActionBlocked):self.read(token)
        path.write_bytes(PNG);(self.root/result['inspection_file']).write_text('{}',encoding='utf-8')
        with self.assertRaises(ActionBlocked):self.read(token)

    def test_tampered_proposal_receipt_and_result_are_blocked(self):
        for field,table in [('digest','browser_proposals'),('fingerprint','actions')]:
            token,_=self.capture()
            with self.actions.receipts.connect() as db:db.execute('UPDATE '+table+' SET '+field+'=? WHERE id=?',('bad',token))
            with self.assertRaises(ActionBlocked):self.read(token)
        token,result=self.capture();result['screenshot_size_bytes']+=1
        with self.actions.receipts.connect() as db:db.execute('UPDATE browser_proposals SET result=? WHERE id=?',(canonical(result),token))
        with self.assertRaises(ActionBlocked):self.read(token)

    def test_invalid_paths_hashes_counts_and_types_are_ineligible(self):
        token,original=self.capture()
        mutations=[('screenshot','../inspection.png'),('screenshot','evidence/not-a-uuid/inspection.png'),
                   ('screenshot','.aws/credentials'),('inspection_file','evidence/wrong/inspection.json'),
                   ('screenshot_sha256','bad'),('screenshot_size_bytes',True),('screenshot_size_bytes',5_000_001),('status','failed')]
        for key,value in mutations:
            with self.subTest(key=key,value=value):
                result=dict(original);result[key]=value;self.replace_result(token,result)
                self.assertEqual(list_downloadable_files(self.actions,'u','p','chat'),[])
                with self.assertRaises(ActionBlocked):self.read(token)

    def test_capture_link_is_blocked_without_filesystem_link_privilege(self):
        token,_=self.capture()
        for method in ('is_symlink','is_junction'):
            with self.subTest(method=method),patch.object(Path,method,return_value=True,create=True):
                with self.assertRaises(ActionBlocked):self.read(token)

    def test_text_creation_still_uses_exact_approved_content(self):
        value={'project_root':str(self.root),'action':'create_file','arguments':{'relative_path':'report.md','content':'Approved report'}}
        token=self.actions.propose('u','p','chat','create_file',value);self.actions.execute('u','p','chat',token)
        self.assertEqual(self.read(token)['data'],b'Approved report')
        (self.root/'report.md').write_text('changed',encoding='utf-8')
        with self.assertRaises(ActionBlocked):self.read(token)

    def test_zip_is_one_exact_nonexecutable_entry_and_does_not_touch_files(self):
        token,_=self.capture();snapshot=self.read(token)
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        packed=zip_snapshot(snapshot)
        with zipfile.ZipFile(io.BytesIO(packed['data'])) as archive:
            self.assertEqual(archive.namelist(),['inspection.png'])
            self.assertEqual(archive.read('inspection.png'),PNG)
            self.assertEqual(archive.getinfo('inspection.png').external_attr>>16 & 0o111,0)
        self.assertEqual(packed['mime'],'application/zip')
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_zip_rejects_paths_and_oversized_untyped_data(self):
        for name,data in [('../file.txt',b'x'),('/file.txt',b'x'),('a\\b.txt',b'x'),('file.txt:stream',b'x'),('file.txt','text'),('file.txt',b'x'*5_000_001)]:
            with self.subTest(name=name),self.assertRaises(ActionBlocked):zip_snapshot({'name':name,'data':data})

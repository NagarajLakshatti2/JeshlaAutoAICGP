"""Whole-read deadline includes worker DNS/headers and cleanup after cancellation."""
import json
import subprocess
from unittest.mock import Mock,patch
import unittest
from agent.web_pages import fetch_web_page

class PageDeadlineTests(unittest.TestCase):
 def worker(self,output=None):
  p=Mock();p.stdin=Mock();p.stdout=Mock();p.returncode=0;p.poll.return_value=0
  p.communicate.return_value=(json.dumps(output or {'url':'https://docs.test','text':'Visible evidence.','title':'Docs','truncated':False}),None)
  return p

 def test_worker_returns_evidence_with_bounded_wait(self):
  p=self.worker()
  with patch('agent.web_pages.subprocess.Popen',return_value=p) as launch:
   result=fetch_web_page('https://docs.test')
  self.assertEqual(result['text'],'Visible evidence.')
  self.assertGreater(p.communicate.call_args.kwargs['timeout'],0)
  self.assertLessEqual(p.communicate.call_args.kwargs['timeout'],30)
  self.assertEqual(json.loads(p.communicate.call_args.args[0]),{'url':'https://docs.test'})
  self.assertNotIn('https://docs.test',str(launch.call_args.args[0]))
  p.stdin.close.assert_called_once();p.stdout.close.assert_called_once()

 def test_stuck_dns_or_headers_terminates_worker(self):
  p=self.worker();p.poll.return_value=None;p.communicate.side_effect=subprocess.TimeoutExpired('reader',30)
  with patch('agent.web_pages.subprocess.Popen',return_value=p):result=fetch_web_page('https://docs.test')
  self.assertIn('deadline',result['error']);self.assertNotIn('text',result)
  p.kill.assert_called_once();p.wait.assert_called_once_with(timeout=5)

 def test_cancelled_read_still_cleans_up_worker(self):
  p=self.worker();p.poll.return_value=None;p.communicate.side_effect=KeyboardInterrupt()
  with patch('agent.web_pages.subprocess.Popen',return_value=p),self.assertRaises(KeyboardInterrupt):fetch_web_page('https://docs.test')
  p.kill.assert_called_once();p.stdin.close.assert_called_once()

 def test_worker_crash_or_invalid_json_cannot_become_evidence(self):
  for invalid in ['not JSON','[]','{"text": 1}']:
   p=self.worker();p.communicate.return_value=(invalid,None)
   with self.subTest(invalid=invalid),patch('agent.web_pages.subprocess.Popen',return_value=p):
    self.assertIn('error',fetch_web_page('https://docs.test'))

 def test_credential_url_is_rejected_before_worker_start(self):
  with patch('agent.web_pages.subprocess.Popen') as launch:
   self.assertIn('error',fetch_web_page('https://user:password@docs.test'))
  launch.assert_not_called()

 def test_unicode_excerpt_does_not_exceed_transport_guard(self):
  text='文'*4500
  p=self.worker({'url':'https://docs.test','text':text,'title':'Docs','truncated':True})
  with patch('agent.web_pages.subprocess.Popen',return_value=p):result=fetch_web_page('https://docs.test')
  self.assertEqual(result['text'],text)

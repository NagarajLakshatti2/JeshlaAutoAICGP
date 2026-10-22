import io,unittest
from email.message import Message
from agent.web_pages import fetch_web_page,public_target

class Response:
    def __init__(self,body=b"",status=200,headers=None):
        self.status=status;self.headers=Message()
        for k,v in (headers or {"Content-Type":"text/html; charset=utf-8"}).items():self.headers[k]=v
        self.body=io.BytesIO(body)
    def getheader(self,name):return self.headers.get(name)
    def read(self,size):return self.body.read(size)
class Connection:
    sock=None
    def __init__(self,response):self.response=response;self.closed=False
    def request(self,*args,**kwargs):pass
    def getresponse(self):return self.response
    def close(self):self.closed=True
class WebPageTests(unittest.TestCase):
    def test_pinned_public_text_and_script_removal(self):
        conn=Connection(Response(b"<title>Docs</title><p>Useful evidence.</p><script>secret script</script>"));targets=[]
        def factory(host,port,ip,timeout):targets.append(ip);return conn
        result=fetch_web_page("https://docs.test/path",resolver=lambda *a:["8.8.8.8"],connection_factory=factory)
        self.assertEqual(targets,["8.8.8.8"]);self.assertTrue(conn.closed)
        self.assertIn("Useful evidence",result["text"]);self.assertNotIn("secret script",result["text"])
        self.assertEqual(result["title"],"Docs")
    def test_private_mixed_dns_credentials_and_ports_blocked(self):
        for url,addresses in [("https://host.test",["8.8.8.8","127.0.0.1"]),("http://localhost",["127.0.0.1"]),("http://host.test",["169.254.169.254"]),("https://u:p@host.test",["8.8.8.8"]),("https://host.test:8443",["8.8.8.8"])]:
            with self.subTest(url=url),self.assertRaises(ValueError):public_target(url,lambda *a:addresses)
    def test_private_redirect_is_blocked_before_second_connection(self):
        calls=[]
        def factory(*args):calls.append(args);return Connection(Response(status=302,headers={"Location":"https://internal.test"}))
        result=fetch_web_page("https://public.test",resolver=lambda host,port:["127.0.0.1"] if host=="internal.test" else ["8.8.8.8"],connection_factory=factory)
        self.assertIn("error",result);self.assertEqual(len(calls),1)
    def test_byte_text_bounds_and_compression(self):
        r=fetch_web_page("https://host.test",resolver=lambda *a:["8.8.8.8"],connection_factory=lambda *a:Connection(Response(b"x"*600000,headers={"Content-Type":"text/plain"})))
        self.assertEqual(len(r["text"]),4500);self.assertTrue(r["truncated"])
        r=fetch_web_page("https://host.test",resolver=lambda *a:["8.8.8.8"],connection_factory=lambda *a:Connection(Response(headers={"Content-Type":"text/html","Content-Encoding":"gzip"})))
        self.assertIn("error",r)
    def test_downgrade_and_nontext_declined(self):
        for response in [Response(status=302,headers={"Location":"http://host.test"}),Response(headers={"Content-Type":"application/pdf"})]:
            r=fetch_web_page("https://host.test",resolver=lambda *a:["8.8.8.8"],connection_factory=lambda *a:Connection(response))
            self.assertIn("error",r)
    def test_connection_failure_does_not_expose_exception(self):
        def factory(*args):raise OSError("private error details")
        r=fetch_web_page("https://host.test",resolver=lambda *a:["8.8.8.8"],connection_factory=factory)
        self.assertIn("error",r);self.assertNotIn("private error",str(r))

    def test_page_tool_requires_search_and_registers_final_url(self):
        import json
        from types import SimpleNamespace
        from agent.conversation import answer_question
        decisions=iter([
            {"tool_calls":[{"id":"blocked","function":{"name":"fetch_web_page","arguments":json.dumps({"url":"https://unseen.test"})}}]},
            {"tool_calls":[{"id":"search","function":{"name":"web_search","arguments":json.dumps({"query":"public docs"})}}]},
            {"tool_calls":[{"id":"fetch","function":{"name":"fetch_web_page","arguments":json.dumps({"url":"https://docs.test"})}}]},
            {"content":"[Page](https://docs.test/final) confirms the evidence."}])
        calls=[];messages=[]
        def model(history,spec):messages.append(history.copy());return next(decisions)
        def page(url):calls.append(url);return {"url":"https://docs.test/final","text":"Page evidence"}
        tools=SimpleNamespace(root="test",list_files=lambda **k:{},read_file=lambda **k:{},search_text=lambda **k:{})
        result=answer_question({"question":"Read documentation"},model=model,project_root=".",document_search=lambda **k:{},web=lambda **k:{"results":[{"url":"https://docs.test","snippet":"snippet"}]},tools=tools,page_fetch=page)
        self.assertEqual(calls,["https://docs.test"])
        self.assertIn("Search first",str(messages[1]))
        self.assertIn("Page evidence",str(messages[-1]))
        self.assertIn("https://docs.test/final",result["answer"])


class DocumentationFragmentTests(unittest.TestCase):
    def test_requested_section_is_visible_after_a_long_page_preamble(self):
        body=("<title>Language rules</title><p>"+"Old preamble "*600+"</p><h3 id='rules'>Target rule</h3><p>Explicit implementation is required.</p>").encode()
        result=fetch_web_page("https://host.test/spec#rules",resolver=lambda *a:["8.8.8.8"],connection_factory=lambda *a:Connection(Response(body)))
        self.assertTrue(result["fragment_found"])
        self.assertTrue(result["text"].startswith("Target rule"))
        self.assertIn("Explicit implementation",result["text"])
        self.assertNotIn("Old preamble",result["text"])

    def test_missing_fragment_is_explicit_and_limits_remain_bounded(self):
        result=fetch_web_page("https://host.test/spec#missing",resolver=lambda *a:["8.8.8.8"],connection_factory=lambda *a:Connection(Response(b"<p>Visible page</p>")))
        self.assertFalse(result["fragment_found"])
        self.assertEqual(result["text"],"Visible page")


    def test_same_discovered_page_can_be_read_at_a_different_fragment(self):
        import json
        from types import SimpleNamespace
        from agent.runtime.conversation import answer_question
        base="https://docs.example.test/spec"
        decisions=iter([
            {"tool_calls":[{"id":"search","function":{"name":"web_search","arguments":json.dumps({"query":"official specs"})}}]},
            {"tool_calls":[{"id":"read","function":{"name":"fetch_web_page","arguments":json.dumps({"url":base+"#target"})}}]},
            {"content":"[Source]("+base+"#target) provides the rule."}])
        fetched=[]
        def page(url):fetched.append(url);return {"url":url,"text":"Specific rule"}
        tools=SimpleNamespace(root="fixture",list_files=lambda **k:{},read_file=lambda **k:{},search_text=lambda **k:{})
        result=answer_question({"question":"Read official specs","route":"web"},model=lambda *a:next(decisions),tools=tools,
            project_root=".",document_search=lambda **k:{},web=lambda **k:{"results":[{"url":base}]},page_fetch=page)
        self.assertEqual(fetched,[base+"#target"])
        self.assertEqual(result["execution_outcome"],"completed")

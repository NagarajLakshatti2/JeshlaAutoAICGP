import json,unittest
from agent.clarification_guard import conflict_clarification_issue
class ClarificationTests(unittest.TestCase):
 def test_generic_conflict_requires_explicit_source_options(self):
  text=json.dumps({"status":"conflict","answer":"Please clarify.","sources":["[DOC-a]","[DOC-b]"]})
  self.assertIsNotNone(conflict_clarification_issue(text,{"DOC-a","DOC-b"}))
 def test_explicit_question_with_registered_options_passes(self):
  text=json.dumps({"status":"conflict","answer":"PDF [DOC-a] or HTML [DOC-b]?","sources":["[DOC-a]","[DOC-b]"]})
  self.assertIsNone(conflict_clarification_issue(text,{"DOC-a","DOC-b"}))
 def test_normal_answers_and_web_only_json_are_unchanged(self):
  for text,refs in [("What workflow?",set()),('{"status":"unknown"}',{"DOC-a"}),('{"status":"conflict","answer":"Which website?"}',set())]:
   self.assertIsNone(conflict_clarification_issue(text,refs))
 def test_unknown_refs_cannot_satisfy_conflict_check(self):
  text=json.dumps({"status":"conflict","answer":"PDF [DOC-a] or HTML [DOC-forged]?","sources":["[DOC-a]","[DOC-forged]"]})
  self.assertIsNotNone(conflict_clarification_issue(text,{"DOC-a","DOC-b"}))

class ConflictLoopTests(unittest.TestCase):
 def run_loop(self,repeat_bad):
  from types import SimpleNamespace
  from agent.conversation import answer_question
  refs=["DOC-aaaaaaaaaaaaaaaa","DOC-bbbbbbbbbbbbbbbb"]
  sources={"sources":[{"ref":refs[0],"text":"Format is PDF."},{"ref":refs[1],"text":"Format is HTML."}]}
  bad=json.dumps({"status":"conflict","answer":"Which format?","sources":["["+ref+"]" for ref in refs]})
  good=json.dumps({"status":"conflict","answer":"PDF ["+refs[0]+"] or HTML ["+refs[1]+"]?","sources":["["+ref+"]" for ref in refs]})
  seen=[]
  def model(messages,specs):
   seen.append(messages.copy())
   if len(seen)==1:return {"role":"assistant","content":"","tool_calls":[{"id":"read","function":{"name":"search_documents","arguments":"{\"query\":\"format\"}"}}]}
   return {"role":"assistant","content":bad if len(seen)==2 or repeat_bad else good}
  tools=SimpleNamespace(root="fixture",list_files=lambda **k:{},read_file=lambda **k:{},search_text=lambda **k:{})
  result=answer_question({"question":"Which format?","route":"rag"},model=model,project_root=".",tools=tools,document_search=lambda **kw:sources)
  return result,seen
 def test_one_correction_preserves_requested_json(self):
  result,seen=self.run_loop(False)
  self.assertEqual(len(seen),3)
  self.assertEqual(json.loads(result["answer"])["status"],"conflict")
  self.assertEqual(result["execution_outcome"],"completed")
 def test_repeated_generic_conflict_stops_after_one_correction(self):
  result,seen=self.run_loop(True)
  self.assertEqual(len(seen),3)
  self.assertEqual(result["task_status"],"incomplete")
  self.assertIn("no resolved answer",result["answer"])

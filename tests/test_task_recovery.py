"""Actual local read-only tools with scripted decisions for failure/recovery coverage."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.conversation import answer_question
from agent.tools.project_tools import ProjectTools

class TaskRecoveryTests(unittest.TestCase):
 def run_case(self,root,steps,tools=None):
  sequence=iter(steps);seen=[]
  def model(messages,specs):
   seen.append(messages.copy());step=next(sequence)
   if isinstance(step,str):return {'role':'assistant','content':step}
   name,args=step
   return {'role':'assistant','content':'','tool_calls':[{'id':'step-'+str(len(seen)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
  return answer_question({'question':'Inspect the project files and explain the configured format.'},model=model,project_root=root,tools=tools or ProjectTools(root),document_search=lambda **kwargs:{'sources':[]}),seen

 def test_only_failed_read_cannot_be_reported_as_completed(self):
  with tempfile.TemporaryDirectory() as folder:
   result,seen=self.run_case(Path(folder),[('read_file',{'relative_path':'missing.txt'}),'Completed: invented format is HTML.'])
   self.assertEqual(result['task_status'],'incomplete')
   self.assertEqual(result['execution_outcome'],'blocked')
   self.assertNotIn('invented',result['answer'])
   self.assertIn('error',json.loads(seen[-1][-1]['content']))

 def test_changed_path_recovers_using_actual_file(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'format.txt').write_text('format=Markdown',encoding='utf-8')
   result,seen=self.run_case(root,[('read_file',{'relative_path':'missing.txt'}),('read_file',{'relative_path':'format.txt'}),'The file specifies Markdown.'])
   self.assertEqual(result['task_status'],'incomplete')
   self.assertIn('The file specifies Markdown.',result['answer'])
   self.assertIn('format=Markdown',seen[-1][-1]['content'])
   self.assertEqual((root/'format.txt').read_text(encoding='utf-8'),'format=Markdown')

 def test_discover_then_read_is_a_multi_step_success(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'format.txt').write_text('format=PDF',encoding='utf-8')
   result,seen=self.run_case(root,[('list_files',{}),('read_file',{'relative_path':'format.txt'}),'The file specifies PDF.'])
   self.assertEqual(result['execution_outcome'],'completed')
   self.assertEqual(json.loads(seen[1][-1]['content'])['files'],['format.txt'])
   self.assertIn('format=PDF',seen[2][-1]['content'])
   self.assertNotIn('task_status',result)

 def test_unchanged_failed_read_is_not_reexecuted(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);tools=ProjectTools(root)
   with patch.object(tools,'read_file',wraps=tools.read_file) as read:
    result,seen=self.run_case(root,[('read_file',{'relative_path':'missing.txt'}),('read_file',{'relative_path':'missing.txt'}),'Done.'],tools=tools)
   self.assertEqual(read.call_count,1)
   self.assertIn('unchanged call',seen[-1][-1]['content'])
   self.assertEqual(result['task_status'],'incomplete')

 def test_successful_listing_cannot_hide_failed_required_read(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'present.txt').write_text('available',encoding='utf-8')
   result,seen=self.run_case(root,[('list_files',{}),('read_file',{'relative_path':'missing.txt'}),'Completed all requested reads.'])
   self.assertEqual(result['task_status'],'incomplete')
   self.assertIn('Task status: incomplete.',result['answer'])
   self.assertEqual(result['execution_outcome'],'partial')

 def test_later_unrelated_success_does_not_clear_failed_read(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'present.txt').write_text('format=PDF',encoding='utf-8')
   result,seen=self.run_case(root,[('read_file',{'relative_path':'missing.txt'}),('list_files',{}),'The folder contains present.txt.'])
   self.assertEqual(result['task_status'],'incomplete')
   self.assertIn('present.txt',result['answer'])

 def test_handler_exception_is_not_hidden_by_other_success(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);tools=ProjectTools(root)
   with patch.object(tools,'read_file',side_effect=RuntimeError('private internal detail')):
    result,seen=self.run_case(root,[('list_files',{}),('read_file',{'relative_path':'file.txt'}),'No complete file evidence.'],tools=tools)
   self.assertEqual(result['task_status'],'incomplete')
   self.assertNotIn('private internal detail',str(seen))

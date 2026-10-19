"""Gemini transport/config checks; fake keys and mocked HTTP only."""
import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from agent import llm_client,tool_llm
from agent.gemini_config import credentials
from agent.provider_errors import ProviderError,response_error

class GeminiTests(unittest.TestCase):
 def environment(self,**extra):return {'GOOGLE_AI_STUDEO_KEY':'offline-fake','GEMINI_MODEL':'gemini-test',**extra}
 def response(self,message=None,reason='stop',status=200):return SimpleNamespace(status_code=status,headers={},json=lambda:{'choices':[{'finish_reason':reason,'message':message or {'content':'Answer'}}],'model':'gemini-test'})

 def test_existing_key_alias_and_primary_precedence(self):
  with patch.dict(llm_client.os.environ,self.environment(),clear=True):self.assertEqual(credentials(),('offline-fake','gemini-test'))
  with patch.dict(llm_client.os.environ,self.environment(GEMINI_API_KEY='preferred-fake'),clear=True):self.assertEqual(credentials()[0],'preferred-fake')

 def test_missing_key_or_model_fails_before_network(self):
  for env in [{},{'GEMINI_API_KEY':'offline-fake'}]:
   with self.subTest(env=bool(env)),patch.dict(llm_client.os.environ,env,clear=True),patch('agent.llm_client.requests.post') as post:
    with self.assertRaises(ProviderError):llm_client.call_gemini('Hello')
    post.assert_not_called()

 def test_text_and_json_use_google_endpoint_and_output_budget(self):
  with patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.llm_client.requests.post',return_value=self.response()) as post:
   self.assertEqual(llm_client.call_gemini('Hello',json_mode=True,max_tokens=512),'Answer')
   self.assertEqual(post.call_args.args[0],'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
   data=post.call_args.kwargs['json'];self.assertEqual(data['max_tokens'],512);self.assertEqual(data['response_format'],{'type':'json_object'})
   self.assertFalse(post.call_args.kwargs['allow_redirects'])

 def test_shared_provider_dispatch(self):
  with patch.object(llm_client,'LLM_PROVIDER','gemini'),patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.llm_client.requests.post',return_value=self.response()):
   self.assertEqual(llm_client.call_llm('Hello'),'Answer')

 def test_tools_and_thought_signature_round_trip(self):
  call={'id':'id-1','type':'function','function':{'name':'search_memory','arguments':'{"query":"project"}'},'extra_content':{'google':{'thought_signature':'opaque-test-signature'}}}
  specs=[{'type':'function','function':{'name':'search_memory','parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query']}}}]
  with patch.object(tool_llm,'LLM_PROVIDER','gemini'),patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.tool_llm.requests.post',side_effect=[self.response({'content':None,'tool_calls':[call]},'tool_calls'),self.response()]) as post:
   result=tool_llm.call_tool_messages([{'role':'user','content':'Read the project name.'}],specs)
   self.assertEqual(result['tool_calls'][0]['extra_content'],call['extra_content'])
   tool_llm.call_tool_messages([result,{'role':'tool','tool_call_id':'id-1','name':'search_memory','content':'sample'}],specs)
   self.assertEqual(post.call_args.kwargs['json']['messages'][0]['tool_calls'][0]['extra_content'],call['extra_content'])

 def test_empty_tools_are_omitted(self):
  with patch.object(tool_llm,'LLM_PROVIDER','gemini'),patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.tool_llm.requests.post',return_value=self.response()) as post:
   tool_llm.call_tool_messages([{'role':'user','content':'Hello'}],[])
   self.assertNotIn('tools',post.call_args.kwargs['json']);self.assertNotIn('tool_choice',post.call_args.kwargs['json'])

 def test_limit_and_invalid_reasoning_stop_without_fallback(self):
  with patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.llm_client.requests.post',return_value=self.response(reason='length')) as post:
   with self.assertRaisesRegex(ProviderError,'OUTPUT_LIMIT'):llm_client.call_gemini('Hello')
   self.assertEqual(post.call_count,1)
  with patch.dict(llm_client.os.environ,self.environment(GEMINI_REASONING_EFFORT='invalid'),clear=True),patch('agent.llm_client.requests.post') as post:
   with self.assertRaises(ProviderError):llm_client.call_gemini('Hello')
   post.assert_not_called()

 def test_google_key_error_is_secret_safe(self):
  response=SimpleNamespace(status_code=400,json=lambda:{'error':{'status':'INVALID_ARGUMENT','message':'API key not valid: secret-value'}})
  error=response_error('gemini',response)
  self.assertEqual(error.category,'AUTHENTICATION');self.assertNotIn('secret-value',str(error))

 def test_quota_error_has_no_automatic_retry(self):
  response=SimpleNamespace(status_code=429,headers={},json=lambda:{'error':{'status':'RESOURCE_EXHAUSTED','message':'Daily limit exceeded secret details'}})
  with patch.dict(llm_client.os.environ,self.environment(),clear=True),patch('agent.llm_client.requests.post',return_value=response) as post:
   with self.assertRaisesRegex(ProviderError,'QUOTA_EXHAUSTED'):llm_client.call_gemini('Hello')
   self.assertEqual(post.call_count,1)

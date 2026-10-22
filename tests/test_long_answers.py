"""Section composition uses scripted data replies, never provider/network access."""
from contextlib import redirect_stdout
import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from agent.providers.errors import ProviderError
from agent.providers.fallback import fallback_scope
from agent.providers.selection import current_provider,output_limit_passthrough,defer_output_limit
from agent.runtime.long_answers import compose_long_answer,_clean_repetition
from agent.runtime.conversation import answer_question


class LongAnswerTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{"LLM_FALLBACK_ENABLED":"true","LLM_FALLBACK_ORDER":"openrouter,groq,gemini",
            "AI_LONG_ANSWERS_ENABLED":"true","AI_LONG_ANSWER_MAX_SECTIONS":"3","AI_LONG_ANSWER_MAX_CALLS":"8",
            "AI_LONG_ANSWER_MAX_CHARS":"60000","AI_CHAT_MAX_CONVERSATION_CHARS":"36000"})
        self.environment.start();self.addCleanup(self.environment.stop)
        self.scope=fallback_scope();self.scope.__enter__();self.addCleanup(self.scope.__exit__,None,None,None)
        self.quiet=redirect_stdout(io.StringIO());self.quiet.__enter__();self.addCleanup(self.quiet.__exit__,None,None,None)
        self.plan={"mode":"answer","title":"Topic guide","scope":"A bounded explanation of the requested topic.","sections":[
            {"title":"Foundations","purpose":"Define the basic concepts"},
            {"title":"Rules","purpose":"Explain applicable rules"},
            {"title":"Pitfalls","purpose":"Explain common mistakes"}]}
        self.calls=[]

    def reply(self,name,value):
        return {"role":"assistant","content":"","tool_calls":[{"id":"data-"+str(len(self.calls)),"type":"function",
            "function":{"name":name,"arguments":json.dumps(value)}}]}

    def model(self,messages,specs):
        name=specs[0]["function"]["name"]
        self.calls.append((current_provider("openrouter"),name,messages))
        if name=="submit_answer_outline":return self.reply(name,self.plan)
        assignment=next(item["content"] for item in reversed(messages) if "Section assignment: " in item.get("content",""))
        task=json.loads(assignment.split("Section assignment: ",1)[1]);identity=task["assigned_section_id"]
        value={"section_id":identity,"content":"Unique completed material for "+identity+".","covered_points":[identity]}
        if "complete" in specs[0]["function"]["parameters"]["properties"]:value["complete"]=True
        return self.reply(name,value)

    def compose(self,model=None):
        return compose_long_answer([{"role":"user","content":"Explain the requested topic."}],model or self.model,failed_provider="openrouter")

    def test_ordered_sections_are_assembled_once(self):
        result=self.compose()
        self.assertEqual([p for p,n,_ in self.calls if n=="submit_answer_section"],["openrouter","groq","gemini"])
        self.assertEqual(result["composition"]["sections"],3)
        self.assertEqual(result["composition"]["model_calls"],4)
        for index,title in enumerate(("Foundations","Rules","Pitfalls"),1):
            self.assertEqual(result["content"].count("## "+title),1)
            self.assertEqual(result["content"].count("Unique completed material for section-"+str(index)),1)
        self.assertLess(result["content"].index("## Foundations"),result["content"].index("## Rules"))
        self.assertIn("already_completed",self.calls[-1][2][-1]["content"])

    def test_integration_replaces_truncated_draft_with_one_answer_without_tools(self):
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        initial=[]
        def model(messages,specs):
            if not specs:
                initial.append("original")
                raise ProviderError("openrouter","OUTPUT_LIMIT","fixture")
            return self.model(messages,specs)
        result=answer_question({"question":"Explain a long topic","route":"direct"},model=model,tools=tools,
            project_root=".",document_search=lambda **k:None)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(initial,["original"])
        self.assertEqual(result["answer"].count("## Foundations"),1)
        tools.list_files.assert_not_called();tools.read_file.assert_not_called();tools.search_text.assert_not_called()

    def test_native_action_drafts_do_not_enter_text_composition(self):
        error=ProviderError("openrouter","OUTPUT_LIMIT","fixture");error.tool_call_output=True
        with output_limit_passthrough():self.assertFalse(defer_output_limit(error))
        with output_limit_passthrough(data_only=True):self.assertTrue(defer_output_limit(error))
        self.assertFalse(defer_output_limit(error))

    def test_wrong_section_id_is_corrected_once_and_never_appended_twice(self):
        failures=[]
        def model(messages,specs):
            reply=self.model(messages,specs)
            if specs[0]["function"]["name"]=="submit_answer_section" and not failures:
                failures.append(1)
                return self.reply("submit_answer_section",{"section_id":"wrong","content":"REJECTED","covered_points":[]})
            return reply
        result=self.compose(model)
        self.assertNotIn("REJECTED",result["content"])
        self.assertEqual(result["composition"]["sections"],3)
        self.assertEqual(result["composition"]["model_calls"],5)

    def test_duplicate_plan_sections_are_rejected_with_bounded_calls(self):
        self.plan["sections"][1]["title"]="Foundations"
        with self.assertRaises(ProviderError) as caught:self.compose()
        self.assertEqual(caught.exception.category,"LONG_ANSWER_FORMAT")
        self.assertEqual(len(self.calls),2)

    def test_later_failure_does_not_return_earlier_completed_sections(self):
        def model(messages,specs):
            if len(self.calls)>=2:raise ProviderError("groq","AUTHENTICATION","fixture")
            return self.model(messages,specs)
        with self.assertRaises(ProviderError) as caught:self.compose(model)
        self.assertEqual(caught.exception.category,"AUTHENTICATION")
        self.assertEqual(len([n for _,n,_ in self.calls if n=="submit_answer_section"]),1)

    def test_request_budget_is_bounded(self):
        with patch.dict(os.environ,{"AI_LONG_ANSWER_MAX_CALLS":"3"}):
            with self.assertRaises(ProviderError) as caught:self.compose()
        self.assertEqual(caught.exception.category,"LONG_ANSWER_LIMIT")
        self.assertEqual(len(self.calls),3)

    def test_required_source_must_be_retrieved_before_long_answer(self):
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        def model(*args):raise ProviderError("openrouter","OUTPUT_LIMIT","fixture")
        with self.assertRaises(ProviderError):answer_question({"question":"Search online","route":"web"},model=model,
            tools=tools,project_root=".",document_search=lambda **k:None)
        self.assertEqual(self.calls,[])

    def test_unsplittable_output_and_unresolved_source_tasks_are_declined(self):
        for mode in ("single_response","needs_tools"):
            with self.subTest(mode=mode):
                self.plan.update(mode=mode,sections=[])
                self.assertIsNone(self.compose())

    def test_exact_repeated_prose_is_removed_but_code_is_preserved(self):
        paragraph="This exact explanatory paragraph is long enough to count as repeated information across sections."
        bullet="- This is the same explanatory point repeated across the answer."
        paragraphs=set();bullets=set()
        first=_clean_repetition(paragraph+"\n\n"+bullet,paragraphs,bullets)
        second=_clean_repetition(paragraph+"\n\n"+bullet+"\n\nNew material",paragraphs,bullets)
        self.assertIn(paragraph,first);self.assertEqual(second,"New material")
        code="```java\nreturn value;\n\nreturn value;\n```"
        self.assertEqual(_clean_repetition(code,paragraphs,bullets),code)
        self.assertEqual(_clean_repetition(code,paragraphs,bullets),code)

    def test_one_composed_answer_is_archived_once_without_workflow_replay(self):
        from tempfile import TemporaryDirectory
        from agent.runtime.turns import run_turn
        graph,catalog=Mock(),Mock();graph.get_state.return_value.values={}
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        def model(messages,specs):
            if not specs:raise ProviderError("openrouter","OUTPUT_LIMIT","fixture")
            return self.model(messages,specs)
        graph.invoke.side_effect=lambda state,**kwargs:answer_question({**state,"route":"direct"},model=model,tools=tools,
            project_root=".",document_search=lambda **k:None)
        with TemporaryDirectory() as directory,patch.dict(os.environ,{"AI_SUMMARY_THRESHOLD_CHARS":"100000"}):
            result=run_turn(graph,{"configurable":{"thread_id":"fixture"}},catalog,"fixture","Explain a long topic",directory)
        graph.invoke.assert_called_once()
        catalog.append.assert_called_once_with("fixture","Explain a long topic",result["answer"])
        self.assertEqual(result["history"].count("Assistant:"),1)
        self.assertEqual(result["answer"].count("## Foundations"),1)
        self.assertEqual(result["execution_outcome"],"completed")

    def test_model_repeated_section_heading_is_not_rendered_twice(self):
        def model(messages,specs):
            reply=self.model(messages,specs)
            if specs[0]["function"]["name"]=="submit_answer_section":
                fn=reply["tool_calls"][0]["function"];value=json.loads(fn["arguments"])
                assignment=next(item["content"] for item in reversed(messages) if "Section assignment: " in item.get("content",""))
                task=json.loads(assignment.split("Section assignment: ",1)[1])
                value["content"]="## "+task["assigned_section"]["title"]+"\n\n"+value["content"]
                fn["arguments"]=json.dumps(value)
            return reply
        result=self.compose(model)
        for title in ("Foundations","Rules","Pitfalls"):self.assertEqual(result["content"].count("## "+title),1)

    def test_citation_correction_does_not_restart_section_planning(self):
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        model=Mock(side_effect=ProviderError("openrouter","OUTPUT_LIMIT","fixture"))
        with patch("agent.runtime.long_answers.compose_long_answer",return_value={"content":"Invalid reference 【commentary:functions.web_search#1】"}) as compose:
            with self.assertRaises(ProviderError):answer_question({"question":"Explain a long topic","route":"direct"},
                model=model,tools=tools,project_root=".",document_search=lambda **k:None)
        compose.assert_called_once()
        self.assertEqual(model.call_count,2)

    def test_aggregated_truncated_tool_proposals_are_not_composed_as_text(self):
        from agent.providers.fallback import call_with_fallback
        def invoke(provider):
            error=ProviderError(provider,"OUTPUT_LIMIT","fixture");error.tool_call_output=True
            raise error
        with output_limit_passthrough():
            with self.assertRaises(ProviderError) as caught:call_with_fallback("openrouter",invoke)
        self.assertTrue(caught.exception.tool_call_output)

    def test_composition_mode_resets_after_failure_and_does_not_leak_threads(self):
        from concurrent.futures import ThreadPoolExecutor
        error=ProviderError("openrouter","OUTPUT_LIMIT","fixture");error.tool_call_output=True
        with self.assertRaises(RuntimeError):
            with output_limit_passthrough(data_only=True):
                self.assertTrue(defer_output_limit(error))
                with ThreadPoolExecutor() as pool:self.assertFalse(pool.submit(defer_output_limit,error).result())
                raise RuntimeError("fixture")
        self.assertFalse(defer_output_limit(error))


    def test_brief_followup_finishes_once_without_artificial_sections(self):
        self.plan.update(mode="single_response",sections=[],answer="Foundations\nRules\nPitfalls")
        result=self.compose()
        self.assertEqual(result["content"],"Foundations\nRules\nPitfalls")
        self.assertEqual(result["composition"]["sections"],0)
        self.assertEqual(len(self.calls),1)
        self.assertNotIn("#",result["content"])
        self.assertIn("hidden reasoning",self.calls[0][2][-1]["content"])

    def test_brief_recovery_keeps_requested_machine_readable_format(self):
        self.plan.update(mode="single_response",sections=[],answer='{"topics":["one","two"]}')
        result=self.compose()
        self.assertEqual(json.loads(result["content"]),{"topics":["one","two"]})
        self.assertEqual(result["content"],self.plan["answer"])

    def test_single_response_rejects_empty_or_unexpected_answer_data(self):
        for content in ("", 1, []):
            with self.subTest(content=content):
                self.plan.update(mode="single_response",sections=[],answer=content)
                with self.assertRaises(ProviderError) as caught:self.compose()
                self.assertEqual(caught.exception.category,"LONG_ANSWER_FORMAT")
        self.plan.update(mode="answer",sections=[{"title":"A","purpose":"A"},{"title":"B","purpose":"B"}],answer="unrelated")
        with self.assertRaises(ProviderError):self.compose()

    def test_provider_rejected_data_gets_one_changed_correction(self):
        attempts=[]
        def model(messages,specs):
            attempts.append([dict(message) for message in messages])
            if len(attempts)==1:raise ProviderError("groq","TOOL_OUTPUT","fixture",status=400)
            return self.model(messages,specs)
        result=self.compose(model)
        self.assertEqual(result["composition"]["sections"],3)
        self.assertEqual(len(attempts),5)
        self.assertIn("provider rejected the generated data format",attempts[1][-1]["content"].lower())
        self.assertNotEqual(attempts[0],attempts[1])

    def test_twice_rejected_section_moves_forward_without_replaying_completed_section(self):
        attempts=[]
        def model(messages,specs):
            name=specs[0]["function"]["name"]
            provider=current_provider("openrouter")
            attempts.append((provider,name,messages))
            if provider=="groq" and name=="submit_answer_section":
                raise ProviderError("groq","TOOL_OUTPUT","fixture",status=400)
            return self.model(messages,specs)
        result=self.compose(model)
        self.assertEqual(result["composition"]["sections"],3)
        self.assertEqual(result["composition"]["model_calls"],6)
        providers=[p for p,name,messages in attempts if name=="submit_answer_section"]
        self.assertEqual(providers,["openrouter","groq","groq","gemini","gemini"])
        self.assertEqual(result["content"].count("Unique completed material for section-1"),1)
        self.assertEqual(result["content"].count("Unique completed material for section-2"),1)

    def test_schema_rejections_cannot_exceed_total_recovery_call_budget(self):
        attempts=[]
        def model(messages,specs):
            attempts.append(current_provider("openrouter"))
            raise ProviderError(attempts[-1],"TOOL_OUTPUT","fixture",status=400)
        with patch.dict(os.environ,{"AI_LONG_ANSWER_MAX_CALLS":"3"}):
            with self.assertRaises(ProviderError) as caught:self.compose(model)
        self.assertEqual(caught.exception.category,"LONG_ANSWER_LIMIT")
        self.assertEqual(attempts,["groq","groq","gemini"])

    def test_conversation_short_recovery_returns_requested_list_without_expansion(self):
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        self.plan.update(mode="single_response",sections=[],answer="First topic\nLast topic")
        def model(messages,specs):
            if specs and specs[0]["function"]["name"]=="submit_answer_outline":return self.model(messages,specs)
            raise ProviderError("openrouter","OUTPUT_LIMIT","fixture")
        result=answer_question({"question":"List every topic covered in your previous answer. Topic names only.",
            "route":"direct","previous_exchange":{"question":"Explain the topic","answer":"First topic\nExplanation\nLast topic"}},
            model=model,tools=tools,project_root=".",document_search=lambda **k:None)
        self.assertEqual(result["answer"],"First topic\nLast topic")
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(len(self.calls),1)
        tools.list_files.assert_not_called();tools.read_file.assert_not_called();tools.search_text.assert_not_called()

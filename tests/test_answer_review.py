"""Data-review contract and no-execution boundaries; no live provider calls."""
import json
import unittest
from unittest.mock import Mock
from agent.runtime.answer_review import review_technical_answer
from agent.providers.errors import ProviderError


class AnswerReviewTests(unittest.TestCase):
    url="https://official.example.test/rules"
    def messages(self):
        return [{"role":"tool","name":"fetch_web_page","content":json.dumps({"url":self.url,"text":"An actual rule excerpt","truncated":True})}]
    def reply(self,value,name="submit_answer_review"):
        if name=="submit_answer_review" and set(value)=={"status","issues","source_urls"}:
            value={**value,"evidence":[]}
        return {"tool_calls":[{"id":"review","function":{"name":name,"arguments":json.dumps(value)}}]}
    def review(self,model):
        return review_technical_answer("Explain the rule","An actual rule excerpt",self.messages(),{self.url},model)

    def test_supported_requires_actual_source_and_no_issues(self):
        data={"status":"supported","issues":[],"source_urls":[self.url]}
        model=Mock(return_value=self.reply({**data,"evidence":[{"claim":"An actual rule excerpt","source_url":self.url,"quote":"An actual rule excerpt"}]}))
        self.assertEqual(self.review(model),data)
        payload=json.loads(model.call_args.args[0][1]["content"])
        self.assertEqual(payload["source_excerpts"][0]["text"],"An actual rule excerpt")
        self.assertEqual(model.call_args.args[1][0]["function"]["name"],"submit_answer_review")

    def test_missing_complete_excerpts_declines_without_a_model_call(self):
        model=Mock()
        result=review_technical_answer("Question","Draft",[],{self.url},model)
        self.assertEqual(result["status"],"insufficient_evidence");model.assert_not_called()

    def test_foreign_actions_and_unsupported_source_claims_are_rejected(self):
        for reply in (self.reply({"status":"supported","issues":[],"source_urls":["https://unread.test"]}),
                      self.reply({"status":"supported","issues":["There is a contradiction"],"source_urls":[self.url]}),
                      self.reply({"status":"revise","issues":[],"source_urls":[]}),
                      self.reply({"action":"delete_file"},name="delete_file")):
            with self.subTest(reply=reply):
                model=Mock(return_value=reply)
                with self.assertRaises(ProviderError) as caught:self.review(model)
                self.assertEqual(caught.exception.category,"ANSWER_REVIEW_FORMAT")
                self.assertEqual(model.call_count,2)

    def test_provider_schema_rejection_gets_one_changed_correction(self):
        data={"status":"revise","issues":["Claim not established by excerpt"],"source_urls":[]}
        model=Mock(side_effect=[ProviderError("groq","TOOL_OUTPUT","fixture"),self.reply(data)])
        self.assertEqual(self.review(model),data)
        self.assertEqual(model.call_count,2)
        self.assertIn("provider rejected",model.call_args.args[0][-1]["content"].lower())

    def test_authentication_failure_is_not_retried_as_a_format_error(self):
        model=Mock(side_effect=ProviderError("groq","AUTHENTICATION","fixture"))
        with self.assertRaises(ProviderError):self.review(model)
        self.assertEqual(model.call_count,1)


    def test_successful_redirect_alias_is_supplied_to_reviewer(self):
        alias="https://official.example.test/original"
        messages=[{"role":"tool","name":"fetch_web_page","content":json.dumps({"url":self.url,"requested_url":alias,"text":"An actual rule excerpt"})}]
        value={"status":"supported","issues":[],"source_urls":[alias]}
        result=review_technical_answer("Question","An actual rule excerpt",messages,{self.url,alias},Mock(return_value=self.reply({**value,"evidence":[{"claim":"An actual rule excerpt","source_url":alias,"quote":"An actual rule excerpt"}]})))
        self.assertEqual(result,value)


    def anchored(self, **changes):
        value={"status":"supported","issues":[],"source_urls":[self.url],"evidence":[{"claim":"An actual rule excerpt","source_url":self.url,"quote":"An actual rule excerpt"}]}
        value.update(changes)
        return value

    def test_supported_without_evidence_is_rejected_after_one_correction(self):
        for value in (self.anchored(evidence=[]), {"status":"supported","issues":[],"source_urls":[self.url]}):
            model=Mock(return_value={"content":json.dumps(value)})
            with self.assertRaises(ProviderError) as caught:self.review(model)
            self.assertEqual(caught.exception.category,"ANSWER_REVIEW_FORMAT")
            self.assertEqual(model.call_count,2)

    def test_fabricated_quotes_and_claims_outside_draft_are_rejected(self):
        for field,bad in (("claim","A claim the draft never made"),("quote","A source quotation that was never retrieved"),("quote","rule"),("source_url","https://unread.test")):
            value=self.anchored();value["evidence"][0][field]=bad
            model=Mock(return_value={"content":json.dumps(value)})
            with self.subTest(field=field,bad=bad),self.assertRaises(ProviderError):self.review(model)
            self.assertEqual(model.call_count,2)

    def test_quote_cannot_be_borrowed_from_another_supplied_page(self):
        other="https://official.example.test/other"
        messages=self.messages()+[{"role":"tool","name":"fetch_web_page","content":json.dumps({"url":other,"text":"A rule available only on the other source."})}]
        value=self.anchored();value["evidence"][0]["quote"]="A rule available only on the other source."
        model=Mock(return_value={"content":json.dumps(value)})
        with self.assertRaises(ProviderError):review_technical_answer("Question","An actual rule excerpt",messages,{self.url,other},model)

    def test_each_claimed_source_requires_an_anchor_and_duplicates_are_invalid(self):
        other="https://official.example.test/other"
        messages=self.messages()+[{"role":"tool","name":"fetch_web_page","content":json.dumps({"url":other,"text":"Another actual rule excerpt"})}]
        for value in (self.anchored(source_urls=[self.url,other]),self.anchored(evidence=self.anchored()["evidence"]*2)):
            model=Mock(return_value={"content":json.dumps(value)})
            with self.assertRaises(ProviderError):review_technical_answer("Question","An actual rule excerpt",messages,{self.url,other},model)

    def test_whitespace_normalization_preserves_case_and_exact_quote_membership(self):
        value=self.anchored();value["evidence"][0]["quote"]="An actual\n rule excerpt"
        model=Mock(return_value={"content":json.dumps(value)})
        self.assertEqual(self.review(model)["status"],"supported")
        value["evidence"][0]["quote"]="AN ACTUAL RULE EXCERPT"
        model.return_value={"content":json.dumps(value)}
        with self.assertRaises(ProviderError):self.review(model)

    def test_one_changed_evidence_correction_preserves_caller_contract(self):
        bad=self.anchored();bad["evidence"][0]["quote"]="An invented source quote to reject"
        good=self.anchored()
        model=Mock(side_effect=[{"content":json.dumps(bad)},{"content":json.dumps(good)}])
        result=self.review(model)
        self.assertEqual(result,{"status":"supported","issues":[],"source_urls":[self.url]})
        self.assertEqual(model.call_count,2)
        self.assertIn("do not fabricate",model.call_args.args[0][-1]["content"])

    def test_real_insufficient_evidence_verdict_may_have_empty_anchors(self):
        value=self.anchored(status="insufficient_evidence",issues=["The excerpt lacks the requested advanced rule"],source_urls=[],evidence=[])
        model=Mock(return_value={"content":json.dumps(value)})
        self.assertEqual(self.review(model)["status"],"insufficient_evidence")
        model.assert_called_once()

    def test_anchor_extras_non_strings_and_bounds_remain_rejected(self):
        bads=[]
        for field,item in (("claim",True),("quote",12),("quote","x"*401),("source_url",False),("action","write_file")):
            value=self.anchored();value["evidence"][0][field]=item;bads.append(value)
        bads.append(self.anchored(evidence=self.anchored()["evidence"]*9))
        for value in bads:
            model=Mock(return_value={"content":json.dumps(value)})
            with self.assertRaises(ProviderError):self.review(model)

    def test_new_native_review_schema_survives_json_compatibility_validation(self):
        from agent.providers.read_only_json import normalize
        value=self.anchored()
        model=Mock(return_value={"content":json.dumps(value)})
        self.review(model)
        specs=model.call_args.args[1]
        envelope={"kind":"tool","name":"submit_answer_review","arguments":value}
        reply=normalize({"content":json.dumps(envelope)},specs,required=True)
        self.assertEqual(json.loads(reply["tool_calls"][0]["function"]["arguments"]),value)
        envelope["arguments"]["evidence"][0]["quote"]=True
        with self.assertRaises(ProviderError):normalize({"content":json.dumps(envelope)},specs,required=True)


class ExecutionReviewBoundaryTests(unittest.TestCase):
    def test_model_supported_verdict_cannot_override_missing_run_evidence(self):
        model=Mock(return_value={"content":json.dumps({"status":"supported","issues":[],"source_urls":["https://official.example.test/rule"]})})
        result=review_technical_answer("Explain expected versus actual output", "## Actual Execution\nThe program will print 42 when you run it.", [], set(), model)
        self.assertEqual(result["status"],"revise")
        self.assertIn("execution evidence",result["issues"][0])
        model.assert_not_called()


class EvidenceReviewConversationTests(unittest.TestCase):
    url="https://official.example.test/version/rules"
    quote="A widget requires an explicit parent."

    def run_answer(self, *, missing_evidence=False):
        from types import SimpleNamespace
        from unittest.mock import patch
        from agent.runtime.conversation import answer_question
        phase=iter(["search","read","draft","revision"])
        calls=[];source_calls=[]
        def model(messages,specs):
            if specs and specs[0]["function"]["name"]=="submit_answer_review":
                calls.append("review")
                value={"status":"supported","issues":[],"source_urls":[self.url]}
                if not missing_evidence:
                    value["evidence"]=[{"claim":self.quote,"source_url":self.url,"quote":self.quote}]
                return {"content":json.dumps(value)}
            item=next(phase);calls.append(item)
            if item=="search":
                return {"tool_calls":[{"id":"search","function":{"name":"web_search","arguments":'{"query":"official widget documentation"}'}}]}
            if item=="read":
                return {"tool_calls":[{"id":"read","function":{"name":"fetch_web_page","arguments":json.dumps({"url":self.url})}}]}
            return {"content":self.quote+" [Official documentation]("+self.url+")"}
        def web(**kwargs):source_calls.append("search");return {"results":[{"url":self.url}]}
        def page(url):source_calls.append("read");return {"url":url,"text":self.quote,"truncated":False}
        tools=SimpleNamespace(root="public-fixture",list_files=Mock(side_effect=AssertionError("No files")),read_file=Mock(side_effect=AssertionError("No files")),search_text=Mock(side_effect=AssertionError("No files")))
        with patch.dict("os.environ",{"AI_TECHNICAL_VERIFICATION":"auto","AI_SOURCE_FIRST_DOCUMENTATION":"false"}):
            result=answer_question({"question":"Explain advanced widget concepts with examples. Verify against official documentation.","route":"direct"},model=model,tools=tools,project_root=".",document_search=lambda **k:{},web=web,page_fetch=page)
        return result,calls,source_calls

    def test_valid_anchors_complete_existing_shared_source_flow(self):
        result,calls,sources=self.run_answer()
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(calls,["search","read","draft","review"])
        self.assertEqual(sources,["search","read"])

    def test_evidence_free_supported_review_cannot_complete_shared_source_flow(self):
        with self.assertRaises(ProviderError) as caught:self.run_answer(missing_evidence=True)
        self.assertEqual(caught.exception.category,"ANSWER_REVIEW_FORMAT")

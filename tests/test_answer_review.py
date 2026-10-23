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


    def feedback_fixture(self, *, verdict="supported", invalid_field="claim"):
        draft="A widget must name its parent."
        source="The declaration of every widget includes an explicit parent."
        messages=[{"role":"tool","name":"fetch_web_page","content":json.dumps({"url":self.url,"text":source})}]
        good={"status":verdict,"issues":[] if verdict=="supported" else ["The advanced claim is outside the supplied excerpt."],"source_urls":[self.url],"evidence":[{"claim":draft,"source_url":self.url,"quote":source}]}
        bad=json.loads(json.dumps(good))
        bad["evidence"][0][invalid_field]=source if invalid_field=="claim" else "UNTRUSTED_REVIEW_VALUE_987 is not in the source."
        if verdict!="supported":good["evidence"]=[]
        calls=[]
        def model(request,specs):
            calls.append(request)
            corrected=len(calls)==2 and "evidence[0]."+invalid_field in request[-1]["content"]
            return self.reply(good if corrected else bad)
        result=review_technical_answer("Explain the rule",draft,messages,{self.url},model)
        return result,calls

    def test_source_text_in_claim_gets_field_specific_feedback_and_one_repair(self):
        result,calls=self.feedback_fixture()
        self.assertEqual(result["status"],"supported")
        self.assertEqual(len(calls),2)
        self.assertIn("draft",calls[-1][-1]["content"])
        self.assertNotIn("The declaration of every widget",calls[-1][-1]["content"])

    def test_negative_verdict_can_repair_anchors_without_becoming_supported(self):
        result,calls=self.feedback_fixture(verdict="revise")
        self.assertEqual(result["status"],"revise")
        self.assertEqual(result["issues"],["The advanced claim is outside the supplied excerpt."])
        self.assertEqual(len(calls),2)

    def test_fabricated_quote_feedback_names_field_without_echoing_value(self):
        result,calls=self.feedback_fixture(invalid_field="quote")
        self.assertEqual(result["status"],"supported")
        self.assertEqual(len(calls),2)
        self.assertNotIn("UNTRUSTED_REVIEW_VALUE_987",calls[-1][-1]["content"])

    def test_malformed_payload_feedback_does_not_echo_untrusted_data(self):
        data={"status":"revise","issues":["No supporting rule in the excerpt"],"source_urls":[],"evidence":[]}
        model=Mock(side_effect=[{"content":"UNTRUSTED_REVIEW_VALUE_987"},self.reply(data)])
        self.assertEqual(self.review(model)["status"],"revise")
        self.assertEqual(model.call_count,2)
        self.assertNotIn("UNTRUSTED_REVIEW_VALUE_987",model.call_args.args[0][-1]["content"])


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

    def run_answer(self, *, missing_evidence=False, inconsistent_review=False, repeated_concerns=False):
        from types import SimpleNamespace
        from unittest.mock import patch
        from agent.runtime.conversation import answer_question
        phase=iter(["search","read","draft","revision"])
        calls=[];source_calls=[]
        def model(messages,specs):
            if specs and specs[0]["function"]["name"]=="submit_answer_review":
                calls.append("review")
                value={"status":"supported","issues":[],"source_urls":[self.url]}
                if inconsistent_review and (calls.count("review")==1 or repeated_concerns):
                    value["issues"]=["Remove the unsupported requirement for exactly four parents."]
                if not missing_evidence:
                    value["evidence"]=[{"claim":self.quote,"source_url":self.url,"quote":self.quote}]
                return {"content":json.dumps(value)}
            item=next(phase);calls.append(item)
            if item=="search":
                return {"tool_calls":[{"id":"search","function":{"name":"web_search","arguments":'{"query":"official widget documentation"}'}}]}
            if item=="read":
                return {"tool_calls":[{"id":"read","function":{"name":"fetch_web_page","arguments":json.dumps({"url":self.url})}}]}
            if inconsistent_review and item=="revision":
                self.assertIn("Remove the unsupported requirement",messages[-1]["content"])
            draft=self.quote+" [Official documentation]("+self.url+")"
            if inconsistent_review and item=="draft":draft+=" Every widget requires exactly four parents."
            return {"content":draft}
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

    def test_inconsistent_review_reaches_shared_answer_revision_and_new_review(self):
        result,calls,sources=self.run_answer(inconsistent_review=True)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertNotIn("exactly four parents",result["answer"])
        self.assertEqual(calls,["search","read","draft","review","revision","review"])
        self.assertEqual(sources,["search","read"])

    def test_repeated_concerns_stop_after_one_shared_answer_revision(self):
        result,calls,sources=self.run_answer(inconsistent_review=True,repeated_concerns=True)
        self.assertEqual(result["execution_outcome"],"blocked")
        self.assertFalse(result["answer_available"])
        self.assertNotIn("exactly four parents",result["answer"])
        self.assertEqual(calls,["search","read","draft","review","revision","review"])
        self.assertEqual(sources,["search","read"])



class PassageSelectionReviewTests(unittest.TestCase):
    url="https://official.example.test/parent-rules"
    draft="**Single inheritance:** A widget has one parent."
    text="Every ordinary widget has one direct parent, and only one."

    def run_review(self,model,*,draft=None,text=None,url=None,extra_pages=()):
        chosen_url=url or self.url
        pages=[{"url":chosen_url,"text":self.text if text is None else text}]+list(extra_pages)
        messages=[{"role":"tool","name":"fetch_web_page","content":json.dumps(page)} for page in pages]
        return review_technical_answer("Explain the parent rule",self.draft if draft is None else draft,messages,{page["url"] for page in pages},model)

    def value(self,request,*,status="supported"):
        payload=json.loads(request[1]["content"])
        passage=next(row for row in payload["source_excerpts"] if row.get("source_id"))
        return {"status":status,"issues":[] if status=="supported" else ["The excerpt does not establish the requested advanced rule."],"source_urls":[passage["url"]],"evidence":[{"draft_id":payload["draft_spans"][0]["draft_id"],"source_id":passage["source_id"]}]}

    def reply(self,value):
        return {"tool_calls":[{"id":"review","function":{"name":"submit_answer_review","arguments":json.dumps(value)}}]}

    def test_formatted_draft_selection_resolves_exact_original_text(self):
        from unittest.mock import patch
        from agent.runtime.answer_review import _validate_review_evidence
        model=Mock(side_effect=lambda request,specs:self.reply(self.value(request)))
        with patch("agent.runtime.answer_review._validate_review_evidence",wraps=_validate_review_evidence) as validate:
            result=self.run_review(model)
        self.assertEqual(result,{"status":"supported","issues":[],"source_urls":[self.url]})
        anchor=validate.call_args.args[0]["evidence"][0]
        self.assertEqual(anchor,{"claim":self.draft,"source_url":self.url,"quote":self.text})
        model.assert_called_once()

    def test_unknown_ids_mixed_shapes_and_non_string_ids_remain_rejected(self):
        mutations=(lambda v:v["evidence"][0].update(draft_id="unknown"),lambda v:v["evidence"][0].update(source_id="unknown"),lambda v:v["evidence"][0].update(claim="Mixed reply"),lambda v:v["evidence"][0].update(draft_id=True))
        for mutate in mutations:
            def model(request,specs):
                value=self.value(request);mutate(value);return self.reply(value)
            mock=Mock(side_effect=model)
            with self.subTest(mutate=mutate),self.assertRaises(ProviderError) as caught:self.run_review(mock)
            self.assertEqual(caught.exception.category,"ANSWER_REVIEW_FORMAT")
            self.assertEqual(mock.call_count,2)

    def test_source_passage_cannot_be_assigned_to_a_different_cited_page(self):
        other="https://official.example.test/unrelated"
        def model(request,specs):
            value=self.value(request);payload=json.loads(request[1]["content"])
            value["evidence"][0]["source_id"]=next(p["source_id"] for p in payload["source_excerpts"] if p["url"]==other)
            return self.reply(value)
        with self.assertRaises(ProviderError):self.run_review(model,extra_pages=[{"url":other,"text":"An unrelated publisher passage with another rule."}])

    def test_duplicate_selections_remain_rejected(self):
        def model(request,specs):
            value=self.value(request);value["evidence"]*=2;return self.reply(value)
        with self.assertRaises(ProviderError):self.run_review(model)

    def test_changed_draft_or_source_invalidates_previous_selection_ids(self):
        saved=[]
        def first(request,specs):
            value=self.value(request);saved.append(value);return self.reply(value)
        self.run_review(first)
        for options in ({"draft":"A widget has a parent; the draft changed."},{"text":"A changed publisher excerpt states an explicit parent requirement."},{"url":"https://official.example.test/other-parent-rules"}):
            with self.subTest(options=options),self.assertRaises(ProviderError):self.run_review(lambda *args:self.reply(saved[0]),**options)

    def test_native_json_compatibility_validates_selection_ids(self):
        from agent.providers.read_only_json import normalize
        observed=[]
        def model(request,specs):
            value=self.value(request);observed.append((value,specs));return self.reply(value)
        self.run_review(model)
        value,specs=observed[0]
        envelope={"kind":"tool","name":"submit_answer_review","arguments":value}
        reply=normalize({"content":json.dumps(envelope)},specs,required=True)
        self.assertEqual(json.loads(reply["tool_calls"][0]["function"]["arguments"]),value)
        value["evidence"][0]["source_id"]="unknown"
        with self.assertRaises(ProviderError):normalize({"content":json.dumps(envelope)},specs,required=True)

    def test_negative_review_does_not_require_or_invent_selection_evidence(self):
        def model(request,specs):
            value=self.value(request,status="insufficient_evidence");value["source_urls"]=[];value["evidence"]=[];return self.reply(value)
        result=self.run_review(model)
        self.assertEqual(result["status"],"insufficient_evidence")
        self.assertTrue(result["issues"])


    def test_inconsistent_supported_verdict_routes_concerns_to_revision_without_format_retry(self):
        calls=[]
        def model(request,specs):
            value=self.value(request)
            if not calls:value["issues"]=["A material claim is outside the supplied evidence."]
            calls.append(value)
            return self.reply(value)
        result=self.run_review(model)
        self.assertEqual(result,{"status":"revise","issues":["A material claim is outside the supplied evidence."],"source_urls":[]})
        self.assertEqual(len(calls),1)

    def test_invalid_negative_review_cannot_erase_concerns_on_format_retry(self):
        calls=[]
        def model(request,specs):
            value=self.value(request)
            if not calls:
                value["status"]="revise"
                value["issues"]=["A material claim is outside the supplied evidence."]
                value["evidence"][0]["source_id"]="unknown"
            calls.append(value)
            return self.reply(value)
        with self.assertRaises(ProviderError) as caught:self.run_review(model)
        self.assertEqual(caught.exception.category,"ANSWER_REVIEW_FORMAT")
        self.assertEqual(len(calls),2)

    def test_catalogue_uses_bounded_exact_passages_from_long_inputs(self):
        draft=("A widget has one explicit parent. "*35)+"Draft tail."
        source=("The publisher describes an explicit parent requirement. "*30)+"Source tail."
        def model(request,specs):
            payload=json.loads(request[1]["content"])
            self.assertEqual(payload["draft"],draft)
            self.assertGreater(len(payload["draft_spans"]),1)
            self.assertGreater(len(payload["source_excerpts"]),1)
            for span in payload["draft_spans"]:
                self.assertIn(span["text"],draft);self.assertLessEqual(len(span["text"]),500)
            for passage in payload["source_excerpts"]:
                self.assertIn(passage["text"],source);self.assertTrue(20<=len(passage["text"])<=400)
            self.assertTrue(any("Source tail." in p["text"] for p in payload["source_excerpts"]))
            return self.reply(self.value(request))
        self.assertEqual(self.run_review(model,draft=draft,text=source)["status"],"supported")

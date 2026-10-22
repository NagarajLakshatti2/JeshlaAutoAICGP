"""Technical evidence and syntax checks; no generated code is ever executed."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from agent.policies.answer_quality import needs_reference_review,syntax_issue
from agent.runtime.conversation import answer_question


class AnswerQualityTests(unittest.TestCase):
    def setUp(self):
        # Preserve coverage of the compatible legacy path; the source-first
        # opt-in path has separate integration and evidence-boundary tests.
        env=patch.dict("os.environ",{"AI_TECHNICAL_VERIFICATION":"auto","AI_SOURCE_FIRST_DOCUMENTATION":"false"})
        env.start();self.addCleanup(env.stop)
        self.tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        self.url="https://official.example.test/language#rules"
        reviewer=patch("agent.runtime.answer_review.review_technical_answer",return_value={"status":"supported","issues":[],"source_urls":[self.url]})
        self.review=reviewer.start();self.addCleanup(reviewer.stop)
        self.good="An explicit implementation resolves the conflict.\n```java\nclass Sample { int value() { return 1; } }\n```\n[Language documentation]("+self.url+")"

    @staticmethod
    def call(name,args,identity):
        return {"tool_calls":[{"id":identity,"function":{"name":name,"arguments":json.dumps(args)}}]}

    def answer(self,model,question="Explain advanced programming rules with examples and pitfalls. Verify against official documentation.",page=None):
        return answer_question({"question":question,"route":"direct"},model=model,tools=self.tools,project_root=".",
            document_search=lambda **k:{},web=lambda **k:{"results":[{"url":self.url,"snippet":"An official documentation result."}]},
            page_fetch=page or (lambda url:{"url":url,"text":"The rule requires an explicit implementation.","truncated":False}))

    def test_detail_requests_verify_but_topic_only_followups_do_not(self):
        self.assertTrue(needs_reference_review("Explain advanced programming concepts with examples."))
        self.assertFalse(needs_reference_review("List the topic names from your previous answer."))
        self.assertFalse(needs_reference_review("What is a superclass?"))
        with patch.dict("os.environ",{"AI_TECHNICAL_VERIFICATION":"off"}):
            self.assertFalse(needs_reference_review("Explain advanced concepts with examples."))

    def test_narrow_java_check_ignores_strings_text_blocks_and_comments(self):
        self.assertIsNotNone(syntax_issue("```java\nint f() => 1;\n```"))
        self.assertIsNone(syntax_issue('```java\nString s = "=>"; // =>\n/* => */\nString t = """\n=>\n""";\n```'))

    def test_python_parse_never_runs_generated_calls(self):
        self.assertIsNotNone(syntax_issue("```python\ndef f(:\n    pass\n```"))
        with patch("os.system",side_effect=AssertionError("Must never execute")):
            self.assertIsNone(syntax_issue("```python\nimport os\nos.system('untrusted command')\n```"))
        self.assertIsNone(syntax_issue("```python\n>>> print(1)\n1\n```"))

    def test_technical_answer_requires_search_then_read_and_uses_only_web_tools(self):
        decisions=iter([{"content":"Unverified premature answer"},self.call("web_search",{"query":"official language documentation"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        requests=[]
        def model(messages,specs):
            requests.append((list(messages),specs))
            return next(decisions)
        result=self.answer(model)
        self.assertEqual(result["answer"],self.good)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(len(requests),4)
        self.assertEqual({spec["function"]["name"] for spec in requests[0][1]},{"web_search"})
        self.assertIn("fetch_web_page",{spec["function"]["name"] for spec in requests[2][1]})
        self.assertEqual({spec["function"]["name"] for spec in requests[-1][1]},{"fetch_web_page"})
        self.tools.list_files.assert_not_called();self.tools.read_file.assert_not_called();self.tools.search_text.assert_not_called()

    def test_snippet_alone_is_not_a_verified_final_answer(self):
        requests=[]
        def model(messages,specs):
            requests.append(messages)
            return self.call("web_search",{"query":"official language docs"},"search") if len(requests)==1 else {"content":self.good}
        result=self.answer(model)
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotEqual(result["answer"],self.good)
        self.assertIn("reading primary documentation",result["answer"])

    def test_restricted_quality_registry_cannot_execute_project_tools(self):
        decisions=iter([self.call("list_files",{},"blocked"),self.call("web_search",{"query":"official language docs"},"search"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        seen=[]
        def model(messages,specs):
            seen.append(list(messages));return next(decisions)
        result=self.answer(model)
        self.tools.list_files.assert_not_called()
        self.assertIn("Invalid tool name or arguments",str(seen[1]))
        self.assertEqual(result["execution_outcome"],"completed")

    def test_invalid_code_gets_one_changed_correction_without_running_it(self):
        decisions=iter([{"content":"```python\ndef f(:\n pass\n```"},{"content":"```python\ndef f():\n    return 1\n```"}])
        requests=[]
        def model(messages,specs):requests.append(list(messages));return next(decisions)
        with patch.dict("os.environ",{"AI_TECHNICAL_VERIFICATION":"off"}):
            result=self.answer(model,question="Write a short example")
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(len(requests),2)
        self.assertIn("failed local syntax parsing",requests[1][-1]["content"])
        self.assertNotIn("def f(:",result["answer"])

    def test_repeated_syntax_failure_is_not_published_as_working_code(self):
        with patch.dict("os.environ",{"AI_TECHNICAL_VERIFICATION":"off"}):
            result=self.answer(Mock(return_value={"content":"```java\nint f() => 1;\n```"}),question="Write a short example")
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotIn("int f() =>",result["answer"])

    def test_late_explanatory_code_enables_reference_review_once(self):
        decisions=iter([{"content":"An explanatory code example.\n```java\nint f() => 1;\n```"},
            self.call("web_search",{"query":"official language docs"},"search"),self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        result=self.answer(lambda *args:next(decisions),question="Explain one example")
        self.assertEqual(result["answer"],self.good)
        self.assertNotIn("=>",result["answer"])

    def test_code_only_and_topic_only_formats_are_preserved(self):
        for content in ("```java\nclass Sample {}\n```","- First topic\n- Last topic"):
            with self.subTest(content=content):
                model=Mock(return_value={"content":content})
                result=self.answer(model,question="Give only the requested output")
                self.assertEqual(result["answer"],content);model.assert_called_once()


    def test_standalone_tutorial_verifies_even_after_a_scoped_previous_chat_request(self):
        seen=[]
        decisions=iter([self.call("web_search",{"query":"official language docs"},"search"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        def model(messages,specs):
            seen.append(json.loads(messages[1]["content"]))
            return next(decisions)
        state={"question":"Explain advanced programming concepts with examples.","route":"direct",
               "history":"User: List topics from the previous answer.\nAssistant: PRIVATE_CANARY",
               "summary":"User project PRIVATE_CANARY", "memory_context":"PRIVATE_CANARY",
               "previous_exchange":{"question":"Inspect my project","answer":"PRIVATE_CANARY"}}
        result=answer_question(state,model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"results":[{"url":self.url}]},page_fetch=lambda url:{"url":url,"text":"Official rule"})
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertNotIn("PRIVATE_CANARY",json.dumps(seen))
        self.assertIn("PRIVATE_CANARY",state["memory_context"])


    def test_table_embedded_code_is_corrected_without_rejecting_markdown_source_examples(self):
        self.assertIsNotNone(syntax_issue("| Example | ```java\\nclass C {}\\n``` |"))
        self.assertIsNone(syntax_issue("```markdown\n| Example | ```java\\nclass C {}\\n``` |\n```"))

    def test_quality_response_must_cite_a_page_actually_read_not_another_search_result(self):
        unread="https://other.example.test/unread"
        bad=self.good.replace(self.url,unread)
        decisions=iter([self.call("web_search",{"query":"official language docs"},"search"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":bad},{"content":self.good}])
        seen=[]
        def model(messages,specs):seen.append(list(messages));return next(decisions)
        result=answer_question({"question":"Explain advanced programming concepts with examples.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"results":[{"url":self.url},{"url":unread}]},
            page_fetch=lambda url:{"url":url,"text":"Official rule"})
        self.assertEqual(result["answer"],self.good)
        self.assertIn("URL not returned",seen[-1][-1]["content"])


    def test_verification_searches_are_capped_with_a_specific_phase_correction(self):
        searches=[];seen=[]
        decisions=iter([self.call("web_search",{"query":"official first query"},"q1"),
                       self.call("web_search",{"query":"official refined query"},"q2"),
                       self.call("web_search",{"query":"unneeded third query"},"q3"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        def model(messages,specs):seen.append(list(messages));return next(decisions)
        def web(query):searches.append(query);return {"results":[{"url":self.url}]}
        result=answer_question({"question":"Explain advanced programming concepts with examples. Verify official documentation.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=web,
            page_fetch=lambda url:{"url":url,"text":"Primary rule"})
        self.assertEqual(searches,["official first query","official refined query"])
        self.assertIn("Available tools in this phase: fetch_web_page",str(seen[3]))
        self.assertEqual(result["execution_outcome"],"completed")


    def test_failed_source_review_gets_one_revision_before_publishing(self):
        self.review.side_effect=[{"status":"revise","issues":["Detailed rule is not established by the excerpt"],"source_urls":[]},
                                 {"status":"supported","issues":[],"source_urls":[self.url]}]
        decisions=iter([self.call("web_search",{"query":"official docs"},"search"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good},{"content":self.good+"\nScope is limited to the excerpt."}])
        result=self.answer(lambda *a:next(decisions))
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertIn("Scope is limited",result["answer"])
        self.assertEqual(self.review.call_count,2)

    def test_repeated_review_failure_does_not_publish_an_unverified_explanation(self):
        self.review.return_value={"status":"insufficient_evidence","issues":["The needed rule is outside the excerpt"],"source_urls":[]}
        decisions=iter([self.call("web_search",{"query":"official docs"},"search"),
                       self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good},{"content":self.good}])
        result=self.answer(lambda *a:next(decisions))
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotEqual(result["answer"],self.good)
        self.assertEqual(self.review.call_count,2)


    def test_automatic_empty_or_failed_search_still_answers_without_verified_claim(self):
        for search_result in ({"results":[]},{"error":"Search timeout"}):
            with self.subTest(search_result=search_result):
                decisions=iter([self.call("web_search",{"query":"official rules"},"search"),{"content":"A general explanation.\n```java\nclass Example {}\n```"}])
                seen=[]
                def model(messages,specs):seen.append((list(messages),specs));return next(decisions)
                result=answer_question({"question":"Explain advanced concepts with examples.","route":"direct"},
                    model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=lambda **k:search_result)
                self.assertEqual(result["execution_outcome"],"completed")
                self.assertIn("uses general knowledge",result["answer"])
                self.assertIn("A general explanation",result["answer"])
                self.assertEqual(len(seen),2);self.assertEqual(seen[-1][1],[])
                self.review.assert_not_called()

    def test_automatic_failed_page_does_not_repeat_search_or_review(self):
        decisions=iter([self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":"A general explanation."}])
        result=self.answer(lambda *a:next(decisions),question="Explain advanced concepts with examples.",page=lambda url:{"error":"Page unavailable"})
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertIn("uses general knowledge",result["answer"])
        self.review.assert_not_called()

    def test_automatic_rejected_draft_gets_one_general_regeneration_not_another_review(self):
        self.review.return_value={"status":"revise","issues":["Unsupported version claim"],"source_urls":[]}
        decisions=iter([self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good+" Unpublished version claim."},
            {"content":"A corrected general explanation."}])
        result=self.answer(lambda *a:next(decisions),question="Explain advanced concepts with examples.")
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertIn("A corrected general explanation",result["answer"])
        self.assertNotIn("Unpublished version claim",result["answer"])
        self.review.assert_called_once()

    def test_automatic_review_format_failure_recovers_but_authentication_does_not(self):
        from agent.providers.errors import ProviderError
        for category in ("ANSWER_REVIEW_FORMAT","AUTHENTICATION"):
            with self.subTest(category=category):
                self.review.reset_mock()
                self.review.side_effect=ProviderError("groq",category,"fixture")
                decisions=iter([self.call("web_search",{"query":"official rules"},"search"),
                    self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good},
                    {"content":"A general explanation."}])
                if category=="AUTHENTICATION":
                    with self.assertRaises(ProviderError):self.answer(lambda *a:next(decisions),question="Explain advanced concepts with examples.")
                else:
                    result=self.answer(lambda *a:next(decisions),question="Explain advanced concepts with examples.")
                    self.assertIn("uses general knowledge",result["answer"])
                self.review.assert_called_once()

    def test_explicit_web_verification_uses_review_gate_and_redacts_private_context(self):
        decisions=iter([self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        seen=[]
        def model(messages,specs):seen.append(json.loads(messages[1]["content"]));return next(decisions)
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"web","memory_context":"PRIVATE_CANARY"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"results":[{"url":self.url}]},page_fetch=lambda url:{"url":url,"text":"Official rule"})
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertNotIn("PRIVATE_CANARY",json.dumps(seen));self.review.assert_called_once()

    def test_explicit_failed_verification_never_silently_changes_to_general_knowledge(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),{"content":"Unsupported answer"},
            self.call("web_search",{"query":"shorter official rules"},"search2"),{"content":"Unsupported answer"}])
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"web"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=lambda **k:{"results":[]})
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotIn("Unsupported answer",result["answer"])
        self.assertNotIn("uses general knowledge",result["answer"])

    def test_failed_previous_response_has_no_topics_to_invent(self):
        model=Mock(side_effect=AssertionError("No model needed for absent published explanation"))
        result=answer_question({"question":"List topics covered in your previous answer.","route":"direct",
            "previous_exchange":{"question":"Explain advanced topics","answer":"Source verification failed."},
            "previous_response_status":{"task_status":"incomplete","execution_outcome":"blocked"},
            "summary":"OLDER_PRIVATE_TOPICS"},model=model,tools=self.tools,project_root=".",document_search=lambda **k:{})
        self.assertIn("did not publish a completed explanation",result["answer"])
        model.assert_not_called()

    def test_successful_followup_does_not_borrow_older_summary_topics_or_tools(self):
        seen=[]
        def model(messages,specs):seen.append((json.loads(messages[1]["content"]),specs));return {"content":"Only the published topic"}
        result=answer_question({"question":"List topics covered in your previous answer.","route":"direct",
            "previous_exchange":{"question":"Explain topics","answer":"Only the published topic"},
            "previous_response_status":{"task_status":"completed","execution_outcome":"completed"},
            "summary":"OLDER_CANARY","history":"User: Older topic\nAssistant: OLDER_CANARY","memory_context":"OLDER_CANARY"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{})
        self.assertNotIn("OLDER_CANARY",json.dumps(seen));self.assertEqual(seen[0][1],[])
        self.assertEqual(result["answer"],"Only the published topic")


    def test_empty_failed_reply_marked_partial_still_cannot_invent_topics(self):
        model=Mock(side_effect=AssertionError("No explanation to extract"))
        result=answer_question({"question":"List topics in your previous answer.","route":"direct",
            "previous_exchange":{"question":"Explain concepts","answer":"No usable source links."},
            "previous_response_status":{"task_status":"incomplete","execution_outcome":"partial","answer_available":False}},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{})
        self.assertIn("did not publish",result["answer"]);model.assert_not_called()

    def test_explicit_new_source_task_is_not_mistaken_for_tool_free_reformatting(self):
        model=Mock(return_value={"content":"Need live evidence"})
        result=answer_question({"question":"Compare your previous answer with official documentation.","route":"web",
            "previous_exchange":{"question":"Explain concepts","answer":"Some topics"},
            "previous_response_status":{"task_status":"incomplete","execution_outcome":"blocked"}},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{})
        self.assertEqual(result["task_status"],"incomplete")
        self.assertIn("web_search",{spec["function"]["name"] for spec in model.call_args.args[1] or model.call_args_list[0].args[1]})

    def test_partial_published_text_remains_available_for_followups(self):
        model=Mock(return_value={"content":"Published topic"})
        result=answer_question({"question":"List topics in your previous answer.","route":"direct",
            "previous_exchange":{"question":"Explain concepts","answer":"Published topic. Task incomplete."},
            "previous_response_status":{"task_status":"incomplete","execution_outcome":"partial","answer_available":True}},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{})
        self.assertEqual(result["answer"],"Published topic");model.assert_called_once()


    def test_blanket_complete_code_claim_is_rejected_for_a_method_fragment(self):
        self.assertIsNotNone(syntax_issue("All code snippets are self-contained.\n```java\n@Override\npublic void act() {}\n```"))
        self.assertIsNotNone(syntax_issue("All code snippets are self\u2011contained.\n```java\n@Override\npublic void act() {}\n```"))
        self.assertIsNone(syntax_issue("Fragment inside the subclass:\n```java\n@Override\npublic void act() {}\n```"))


    def test_general_explanation_recovery_keeps_existing_long_answer_composition(self):
        from agent.providers.errors import ProviderError
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            ProviderError("openrouter","OUTPUT_LIMIT","fixture")])
        with patch.dict("os.environ",{"AI_LONG_ANSWERS_ENABLED":"true","LLM_FALLBACK_ENABLED":"true"}),patch("agent.runtime.long_answers.compose_long_answer",return_value={"content":"A complete general explanation."}) as compose:
            result=answer_question({"question":"Explain advanced concepts with examples.","route":"direct"},
                model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=lambda **k:{"results":[]})
        self.assertIn("A complete general explanation",result["answer"])
        self.assertIn("uses general knowledge",result["answer"])
        compose.assert_called_once()


    def test_missing_source_labels_are_attached_without_regenerating_the_whole_answer(self):
        uncited="A supported explanation.\n```java\nclass Example {}\n```"
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":uncited}])
        result=self.answer(model)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertTrue(result["answer"].startswith(uncited))
        self.assertIn("Sources read (bounded excerpts)",result["answer"])
        self.assertIn(self.url,result["answer"])
        self.assertEqual(model.call_count,3);self.review.assert_called_once()

    def test_requested_redirect_url_is_a_valid_alias_of_actual_page_read(self):
        canonical="https://official.example.test/canonical"
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        result=self.answer(model,page=lambda url:{"url":canonical,"requested_url":url,"text":"Official rule"})
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(model.call_count,3)
        self.assertIn(self.url,self.review.call_args.args[3])
        self.assertIn(canonical,self.review.call_args.args[3])

    def test_explicit_empty_first_search_uses_remaining_changed_query_budget(self):
        searches=[]
        def web(query):
            searches.append(query)
            return {"results":[]} if len(searches)==1 else {"results":[{"url":self.url}]}
        model=Mock(side_effect=[self.call("web_search",{"query":"long failed query"},"search1"),
            self.call("web_search",{"query":"short official rules"},"search2"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=web,
            page_fetch=lambda url:{"url":url,"text":"Official rule"})
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(searches,["long failed query","short official rules"])
        self.review.assert_called_once()

    def test_automatic_failure_does_not_grow_to_two_model_search_calls(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),{"content":"A general explanation."}])
        web=Mock(return_value={"error":"Both search backends unavailable"})
        result=answer_question({"question":"Explain advanced concepts with examples.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=web)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertIn("uses general knowledge",result["answer"])
        web.assert_called_once()


    def test_explicit_request_can_read_one_complementary_page_before_final_review(self):
        other="https://official.example.test/additional-section"
        decisions=iter([self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"first-page"),
            self.call("fetch_web_page",{"url":other},"second-page"),{"content":self.good}])
        fetched=[]
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"direct"},
            model=lambda *a:next(decisions),tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"results":[{"url":self.url},{"url":other}]},
            page_fetch=lambda url:fetched.append(url) or {"url":url,"text":"Official rule"})
        self.assertEqual(fetched,[self.url,other]);self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(self.review.call_args.args[3],{self.url,other})


    def test_explicit_learning_can_read_candidate_official_url_after_search_outage(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good}])
        page=Mock(return_value={"url":self.url,"text":"An actual rule excerpt"})
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"error":"Search backend unavailable"},page_fetch=page)
        self.assertEqual(result["execution_outcome"],"completed")
        page.assert_called_once_with(self.url);self.review.assert_called_once()
        self.assertIn(self.url,self.review.call_args.args[3])

    def test_failed_candidate_url_never_becomes_citable_evidence(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":self.good},
            self.call("web_search",{"query":"short official query"},"search2"),{"content":self.good}])
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"error":"Search unavailable"},page_fetch=lambda url:{"error":"HTTP 404"})
        self.assertEqual(result["task_status"],"incomplete");self.review.assert_not_called()
        self.assertNotEqual(result["answer"],self.good)

    def test_candidate_url_fallback_is_not_available_for_private_source_tasks(self):
        page=Mock(side_effect=AssertionError("Private task cannot use candidate URL escape"))
        model=Mock(side_effect=[self.call("web_search",{"query":"public rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),{"content":"No private source evidence"}])
        result=answer_question({"question":"Read my indexed documents","route":"web"},model=model,
            tools=self.tools,project_root=".",document_search=lambda **k:{},web=lambda **k:{"error":"Search unavailable"},page_fetch=page)
        page.assert_not_called();self.assertEqual(result["task_status"],"incomplete")


    def test_read_only_provider_format_failure_gets_one_changed_correction_without_replaying_reads(self):
        from agent.providers.errors import ProviderError
        requests=[]
        choices=iter([self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),ProviderError("groq","TOOL_OUTPUT","fixture"),{"content":self.good}])
        def model(messages,specs):
            requests.append(list(messages));reply=next(choices)
            if isinstance(reply,Exception):raise reply
            return reply
        page=Mock(return_value={"url":self.url,"text":"Official rule"})
        result=self.answer(model,page=page)
        self.assertEqual(result["execution_outcome"],"completed")
        page.assert_called_once_with(self.url)
        self.assertIn("provider rejected the response format",requests[-1][-1]["content"].lower())
        self.assertIn("fetch_web_page",requests[-1][-1]["content"])
        self.review.assert_called_once()

    def test_repeated_read_only_format_failure_stops_after_one_correction(self):
        from agent.providers.errors import ProviderError
        model=Mock(side_effect=[self.call("web_search",{"query":"official rules"},"search"),
            self.call("fetch_web_page",{"url":self.url},"read"),ProviderError("groq","TOOL_OUTPUT","fixture"),ProviderError("groq","TOOL_OUTPUT","fixture")])
        with self.assertRaises(ProviderError):self.answer(model)
        self.assertEqual(model.call_count,4)
        self.review.assert_not_called()


    def test_browser_two_failed_searches_then_refusal_enters_direct_read_phase(self):
        choices=iter([self.call("web_search",{"query":"first official query"},"search1"),
            self.call("web_search",{"query":"refined official query"},"search2"),
            {"content":"No usable source links. Cannot verify."},
            self.call("fetch_web_page",{"url":self.url},"direct-read"),{"content":self.good}])
        requests=[]
        def model(messages,specs):
            requests.append((list(messages),specs));return next(choices)
        page=Mock(return_value={"url":self.url,"text":"An actual official rule excerpt"})
        result=answer_question({"question":"Explain advanced programming concepts with examples. Verify official documentation.","route":"web"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"error":"Search unavailable"},page_fetch=page)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual({spec["function"]["name"] for spec in requests[3][1]},{"fetch_web_page"})
        page.assert_called_once_with(self.url);self.review.assert_called_once()
        self.tools.list_files.assert_not_called();self.tools.read_file.assert_not_called()

    def test_premature_refusal_after_one_failed_search_does_not_trigger_more_search_loops(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official query"},"search"),
            {"content":"No links found"},self.call("fetch_web_page",{"url":self.url},"direct-read"),{"content":self.good}])
        web=Mock(return_value={"results":[]})
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"direct"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=web,
            page_fetch=lambda url:{"url":url,"text":"Official rule"})
        self.assertEqual(result["execution_outcome"],"completed");web.assert_called_once()

    def test_known_version_document_can_be_read_even_if_search_only_found_other_links(self):
        old="https://official.example.test/older-version"
        model=Mock(side_effect=[self.call("web_search",{"query":"official version documentation"},"search"),
            self.call("fetch_web_page",{"url":self.url},"version-read"),{"content":self.good}])
        page=Mock(return_value={"url":self.url,"text":"Actual version-specific rule"})
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"web"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},
            web=lambda **k:{"results":[{"url":old}]},page_fetch=page)
        self.assertEqual(result["execution_outcome"],"completed");page.assert_called_once_with(self.url)
        self.assertNotIn(old,self.review.call_args.args[3])

    def test_missing_candidate_stops_without_claiming_a_verified_answer(self):
        model=Mock(side_effect=[self.call("web_search",{"query":"official query"},"search"),
            {"content":"No links found"},{"content":"I do not know a suitable URL"}])
        page=Mock()
        result=answer_question({"question":"Explain advanced concepts with examples. Verify official documentation.","route":"web"},
            model=model,tools=self.tools,project_root=".",document_search=lambda **k:{},web=lambda **k:{"error":"Unavailable"},page_fetch=page)
        self.assertEqual(result["task_status"],"incomplete")
        self.assertIn("no suitable documentation page was opened",result["answer"])
        page.assert_not_called();self.review.assert_not_called()


class ExecutionEvidenceTests(unittest.TestCase):
    def test_prediction_under_actual_heading_requires_disclosure(self):
        from agent.policies.answer_quality import execution_claim_issue
        for heading in ("Actual Execution", "### Actual Output", "**Observed output**", "Execution results:"):
            self.assertIsNotNone(execution_claim_issue(heading+"\nWhen you run the example, the output will match the prediction."))

    def test_actual_heading_accepts_explicit_not_run_disclosure(self):
        from agent.policies.answer_quality import execution_claim_issue
        for disclosure in ("The example was not executed here.", "I haven't run this example.", "No actual execution was performed.", "Not compiled or tested here."):
            self.assertIsNone(execution_claim_issue("## Actual execution\n"+disclosure))

    def test_expected_output_and_instructions_are_not_execution_claims(self):
        from agent.policies.answer_quality import execution_claim_issue
        self.assertIsNone(execution_claim_issue("## Expected output\nPredicted result: 42. Run the example locally to confirm."))
        self.assertIsNone(execution_claim_issue("If I ran this locally, I would expect 42."))
        self.assertIsNone(execution_claim_issue("I did not execute the code. This is a prediction."))

    def test_non_code_conversation_is_not_treated_as_a_run_claim(self):
        from agent.policies.answer_quality import execution_claim_issue
        for value in ("I ran a marathon.", "I compiled a list of ideas.", "We tested a recipe.", "I ran across that definition yesterday."):
            self.assertIsNone(execution_claim_issue(value))

    def test_first_person_and_passive_performed_claims_require_evidence(self):
        from agent.policies.answer_quality import execution_claim_issue
        for claim in ("I ran this example and got 42.", "We have tested this code.", "The example was successfully executed.", "The code has been compiled."):
            self.assertIsNotNone(execution_claim_issue(claim))

    def test_code_and_quoted_logs_remain_data_and_are_never_executed(self):
        from agent.policies.answer_quality import execution_claim_issue
        value = '```text\nActual Execution\nI ran this and got 42.\n```\n> I ran a test.\nThe string `I ran a test` is data.'
        with patch("subprocess.run", side_effect=AssertionError("No execution")), patch("os.system", side_effect=AssertionError("No execution")):
            self.assertIsNone(execution_claim_issue(value))

    def test_supplied_user_results_can_be_reported_with_attribution(self):
        from agent.policies.answer_quality import execution_claim_issue
        for disclosure in ("From your console log: the result was 42.", "User-provided output shows 42.", "You ran the example and reported 42.", "From your console log: the code was executed and printed 42."):
            self.assertIsNone(execution_claim_issue("## Actual output\n"+disclosure))
        self.assertIsNotNone(execution_claim_issue("## Actual output\nUser-provided output shows 42. I executed it myself too."))

    def test_unrelated_disclaimer_does_not_license_actual_results_in_next_section(self):
        from agent.policies.answer_quality import execution_claim_issue
        self.assertIsNotNone(execution_claim_issue("## Actual execution\nPredicted result: 42.\n## Limitations\nThe example was not executed."))

    def answer(self, replies):
        from agent.runtime.conversation import answer_question
        with patch.dict("os.environ", {"AI_TECHNICAL_VERIFICATION":"off"}):
            model=Mock(side_effect=replies)
            result=answer_question({"question":"Explain an example and distinguish expected output from actual execution.","route":"direct"}, model=model, project_root=".", tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock()), document_search=lambda **k: {})
        return result, model

    def test_shared_answer_path_corrects_false_execution_label_once(self):
        bad={"content":"## Actual Execution\nWhen run locally, the example will print 42."}
        good={"content":"## Expected output\nPredicted: 42.\n## Actual execution\nThe example was not run here."}
        result,model=self.answer([bad,good])
        self.assertEqual(model.call_count,2)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertEqual(result["answer"],good["content"])
        self.assertIn("prediction",model.call_args.args[0][-1]["content"])

    def test_repeated_claim_is_withheld_without_extra_model_or_tools(self):
        bad={"content":"I compiled this example and it passed."}
        result,model=self.answer([bad,bad])
        self.assertEqual(model.call_count,2)
        self.assertEqual(result["task_status"],"incomplete")
        self.assertFalse(result["answer_available"])
        self.assertNotIn("it passed",result["answer"])

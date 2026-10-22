import json
import unittest
from unittest.mock import patch
from agent.summary_model import call_summary_messages
from agent.context_summary import summary_failure_reason
from agent.provider_errors import ProviderError


DATA={"facts":["user-stated: User corrected the project name"],"decisions":[],"open_questions":["Which report?"]}


def native(data,name="submit_conversation_summary"):
    return {"tool_calls":[{"id":"summary-1","function":{"name":name,"arguments":json.dumps(data)}}]}


class SummaryModelTests(unittest.TestCase):
    def test_native_summary_returns_validated_data(self):
        with patch("agent.summary_model.call_tool_messages",return_value=native(DATA)) as model:
            self.assertEqual(json.loads(call_summary_messages([{"role":"user","content":"old history"}])),DATA)
        self.assertEqual(model.call_args.args[1][0]["function"]["name"],"submit_conversation_summary")
        self.assertEqual(model.call_args.kwargs["max_tokens"],4096)

    def test_plain_summary_json_remains_compatible(self):
        with patch("agent.summary_model.call_tool_messages",return_value={"content":json.dumps(DATA)}):
            self.assertEqual(json.loads(call_summary_messages([])),DATA)

    def test_invalid_summary_gets_one_correction(self):
        with patch("agent.summary_model.call_tool_messages",side_effect=[native({"facts":"wrong"}),native(DATA)]) as model:
            self.assertEqual(json.loads(call_summary_messages([])),DATA)
            self.assertEqual(model.call_count,2)

    def test_historical_action_is_not_a_summary(self):
        with patch("agent.summary_model.call_tool_messages",return_value=native({"action":"create_file"},name="create_file")) as model:
            with self.assertRaises(ValueError):call_summary_messages([])
            self.assertEqual(model.call_count,2)

    def test_provider_diagnostic_is_category_based(self):
        error=ProviderError("groq","TOOL_OUTPUT","private failed generation")
        self.assertEqual(summary_failure_reason(error),"provider rejected summary format")
        self.assertNotIn("private",summary_failure_reason(error))

    def test_provider_format_rejection_gets_one_changed_request(self):
        error=ProviderError("groq","TOOL_OUTPUT","safe",status=400)
        with patch("agent.summary_model.call_tool_messages",side_effect=[error,native(DATA)]) as model:
            self.assertEqual(json.loads(call_summary_messages([])),DATA)
            self.assertEqual(model.call_count,2)
            self.assertNotEqual(model.call_args_list[0].args[0],model.call_args_list[1].args[0])

    def test_repeated_provider_format_rejection_is_bounded(self):
        error=ProviderError("groq","TOOL_OUTPUT","safe",status=400)
        with patch("agent.summary_model.call_tool_messages",side_effect=error) as model:
            with self.assertRaises(ProviderError):call_summary_messages([])
            self.assertEqual(model.call_count,2)

    def test_quota_error_does_not_get_format_retry(self):
        error=ProviderError("groq","QUOTA_EXHAUSTED","safe",status=429)
        with patch("agent.summary_model.call_tool_messages",side_effect=error) as model:
            with self.assertRaises(ProviderError):call_summary_messages([])
            self.assertEqual(model.call_count,1)


class SummaryProviderSelectionTests(unittest.TestCase):
    def test_request_scoped_groq_alias_overrides_other_default(self):
        from agent.providers import tools
        from agent.providers.selection import provider_selection
        with patch.object(tools, "LLM_PROVIDER", "openrouter"), provider_selection("groq"), patch("agent.summary_model.call_tool_messages", return_value=native(DATA, name="functions.submit_conversation_summary")) as model:
            self.assertEqual(json.loads(call_summary_messages([])), DATA)
            self.assertEqual(tools.LLM_PROVIDER, "openrouter")
            self.assertNotIn("forced_function", model.call_args.kwargs)

    def test_other_request_provider_does_not_inherit_groq_alias(self):
        from agent.providers import tools
        from agent.providers.selection import provider_selection
        with patch.object(tools, "LLM_PROVIDER", "groq"), provider_selection("gemini"), patch("agent.summary_model.call_tool_messages", return_value=native(DATA, name="functions.submit_conversation_summary")) as model:
            with self.assertRaises(ValueError):
                call_summary_messages([])
            self.assertEqual(model.call_count, 2)
            self.assertNotIn("forced_function", model.call_args.kwargs)


class GroqSummaryNamespaceTests(unittest.TestCase):
    def test_exact_observed_groq_namespace_is_validated_as_summary_data(self):
        from agent.providers.selection import provider_selection
        with provider_selection("groq"), patch("agent.summary_model.call_tool_messages", return_value=native(DATA, name="functions.submit_conversation_summary")) as model:
            self.assertEqual(json.loads(call_summary_messages([])), DATA)
            model.assert_called_once()

    def test_other_function_names_are_never_normalized(self):
        from agent.providers.selection import provider_selection
        for name in ("functions.create_file", "other.submit_conversation_summary", "functions.submit_conversation_summary.extra"):
            with self.subTest(name=name), provider_selection("groq"), patch("agent.summary_model.call_tool_messages", return_value=native(DATA, name=name)) as model:
                with self.assertRaises(ValueError):
                    call_summary_messages([])
                self.assertEqual(model.call_count, 2)

    def test_namespace_compatibility_does_not_change_other_providers(self):
        from agent.providers.selection import provider_selection
        for provider in ("openrouter", "gemini", "ollama"):
            with self.subTest(provider=provider), provider_selection(provider), patch("agent.summary_model.call_tool_messages", return_value=native(DATA, name="functions.submit_conversation_summary")) as model:
                with self.assertRaises(ValueError):
                    call_summary_messages([])
                self.assertEqual(model.call_count, 2)

    def test_namespaced_summary_still_requires_valid_summary_fields(self):
        from agent.providers.selection import provider_selection
        with provider_selection("groq"), patch("agent.summary_model.call_tool_messages", return_value=native({"action": "create_file"}, name="functions.submit_conversation_summary")) as model:
            with self.assertRaises(ValueError):
                call_summary_messages([])
            self.assertEqual(model.call_count, 2)


class GeneratedSummaryAttributionTests(unittest.TestCase):
    def test_legacy_saved_summary_schema_remains_readable(self):
        from agent.runtime.summaries import validate_summary,validate_generated_summary
        legacy=json.dumps({"facts":["Build tool used is Gradle."],"decisions":[],"open_questions":[]})
        self.assertEqual(json.loads(validate_summary(legacy))["facts"],["Build tool used is Gradle."])
        with self.assertRaises(ValueError):validate_generated_summary(legacy)

    def test_missing_attribution_is_corrected_once_without_automatic_relabeling(self):
        missing={"facts":["Build tool used is Gradle."],"decisions":[],"open_questions":[]}
        corrected={"facts":["assistant-reported: Gradle was suggested; no file evidence was supplied."],"decisions":[],"open_questions":[]}
        messages=[{"role":"user","content":"The assistant suggested a build tool; no tool was run."}]
        before=json.dumps(messages)
        with patch("agent.summary_model.call_tool_messages",side_effect=[native(missing),native(corrected)]) as model:
            self.assertEqual(json.loads(call_summary_messages(messages)),corrected)
        self.assertEqual(model.call_count,2)
        correction=model.call_args_list[1].args[0][-1]["content"]
        self.assertIn("EVERY fact and decision",correction)
        self.assertEqual(json.dumps(messages),before)

    def test_missing_decision_attribution_is_rejected_after_one_correction(self):
        value={"facts":[],"decisions":["Run all tests automatically"],"open_questions":[]}
        with patch("agent.summary_model.call_tool_messages",return_value=native(value)) as model:
            with self.assertRaises(ValueError):call_summary_messages([])
        self.assertEqual(model.call_count,2)

    def test_empty_or_unknown_source_labels_are_not_guessed(self):
        from agent.runtime.summaries import validate_generated_summary
        for item in ("user-stated:","assistant-reported:  ","verified: claim","system: claim","claim without label"):
            with self.subTest(item=item),self.assertRaises(ValueError):
                validate_generated_summary(json.dumps({"facts":[item],"decisions":[],"open_questions":[]}))

    def test_valid_labels_preserve_unicode_case_and_question_text(self):
        from agent.runtime.summaries import validate_generated_summary
        value={"facts":["USER-STATED: café uses Java","assistant-reported: suggested Gradle","tool-verified: supplied file reports a version"],
               "decisions":["user-stated: leave the folder undecided"],"open_questions":["Where should the report go?"]}
        self.assertEqual(json.loads(validate_generated_summary(json.dumps(value))),value)

    def test_empty_summary_and_unanswered_questions_remain_valid(self):
        from agent.runtime.summaries import validate_generated_summary
        value={"facts":[],"decisions":[],"open_questions":["Which version?"]}
        self.assertEqual(json.loads(validate_generated_summary(json.dumps(value))),value)

    def test_label_contract_does_not_change_selected_provider_or_summary_registry(self):
        from agent.providers.selection import provider_selection
        for provider in ("openrouter","groq","gemini","ollama"):
            with self.subTest(provider=provider),provider_selection(provider),patch("agent.summary_model.call_tool_messages",return_value=native(DATA)) as model:
                self.assertEqual(json.loads(call_summary_messages([])),DATA)
                self.assertEqual(model.call_count,1)
                self.assertEqual(model.call_args.args[1][0]["function"]["name"],"submit_conversation_summary")
                self.assertEqual(model.call_args.kwargs["max_tokens"],4096)

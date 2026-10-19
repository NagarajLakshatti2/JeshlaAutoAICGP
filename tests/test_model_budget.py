import os
import unittest
from unittest.mock import patch
import requests
from agent.model_budget import apply_model_budget
from agent.provider_errors import ProviderError,request_model


def hosted(text="hello"):
    return {"model":"test-model","messages":[{"role":"user","content":text}],"max_completion_tokens":4096}


class ModelBudgetTests(unittest.TestCase):
    def test_hosted_unknown_context_keeps_requested_output(self):
        with patch.dict(os.environ,{},clear=True):
            result=apply_model_budget("groq",hosted())
        self.assertEqual(result["max_completion_tokens"],4096)

    def test_known_hosted_context_reserves_input_and_output(self):
        with patch.dict(os.environ,{"GROQ_CONTEXT_TOKENS":"2048"},clear=True):
            original=hosted();result=apply_model_budget("groq",original)
        self.assertLess(result["max_completion_tokens"],2048)
        self.assertEqual(original["max_completion_tokens"],4096)

    def test_ollama_uses_actual_request_context(self):
        payload={"model":"local","messages":[{"role":"user","content":"hello"}],"options":{"num_ctx":1024,"num_predict":4096}}
        with patch.dict(os.environ,{},clear=True):result=apply_model_budget("ollama",payload)
        self.assertLess(result["options"]["num_predict"],1024)
        self.assertEqual(payload["options"]["num_predict"],4096)

    def test_oversized_input_fails_before_network(self):
        with patch.dict(os.environ,{"GROQ_CONTEXT_TOKENS":"1024"},clear=True),patch.object(requests,"post") as post:
            with self.assertRaises(ProviderError) as caught:
                request_model("groq","https://example.invalid",headers={},json=hosted("x"*10000),timeout=(10,90))
        self.assertEqual(caught.exception.category,"CONTEXT_PREFLIGHT")
        post.assert_not_called()

    def test_schema_is_part_of_input_estimate(self):
        payload=hosted();payload["tools"]=[{"description":"x"*10000}]
        with patch.dict(os.environ,{"GROQ_CONTEXT_TOKENS":"1024"},clear=True):
            with self.assertRaises(ProviderError):apply_model_budget("groq",payload)

    def test_selected_model_must_match_bound_limits(self):
        with patch.dict(os.environ,{"GROQ_CONTEXT_TOKENS":"2048","GROQ_BUDGET_MODEL":"different"},clear=True):
            with self.assertRaises(ProviderError):apply_model_budget("groq",hosted())

    def test_output_cap_is_provider_specific(self):
        with patch.dict(os.environ,{"GROQ_OUTPUT_TOKEN_LIMIT":"512"},clear=True):
            self.assertEqual(apply_model_budget("groq",hosted())["max_completion_tokens"],512)
            self.assertEqual(apply_model_budget("openrouter",{"model":"test","messages":[{"role":"user","content":"hi"}],"max_tokens":4096})["max_tokens"],4096)

    def test_bad_ratio_is_configuration_error(self):
        with patch.dict(os.environ,{"LLM_TOKEN_ESTIMATE_BYTES_PER_TOKEN":"NaN"},clear=True):
            with self.assertRaises(ProviderError) as caught:apply_model_budget("groq",hosted())
        self.assertEqual(caught.exception.category,"CONFIGURATION")

    def test_unspecified_hosted_output_is_preserved_when_limits_unknown(self):
        payload={"model":"test-model","messages":[{"role":"user","content":"hello"}]}
        with patch.dict(os.environ,{},clear=True):result=apply_model_budget("openrouter",payload)
        self.assertNotIn("max_tokens",result)

    def test_all_providers_reject_large_unicode_and_schema_before_network(self):
        import copy
        for provider in ("groq","openrouter","gemini","ollama"):
            for large_schema in (False,True):
                with self.subTest(provider=provider,schema=large_schema):
                    payload={"model":"fixture","messages":[{"role":"user","content":"hello" if large_schema else "漢字"*5000}]}
                    if large_schema:payload["tools"]=[{"description":"schema "*3000}]
                    if provider=="ollama":payload["options"]={"num_ctx":1024,"num_predict":512}
                    else:payload["max_completion_tokens" if provider=="groq" else "max_tokens"]=512
                    before=copy.deepcopy(payload)
                    with patch.dict(os.environ,{provider.upper()+"_CONTEXT_TOKENS":"1024"},clear=True),patch.object(requests,"post") as post:
                        with self.assertRaises(ProviderError) as caught:
                            request_model(provider,"https://example.invalid",headers={},json=payload,timeout=(10,90))
                    self.assertEqual(caught.exception.category,"CONTEXT_PREFLIGHT")
                    post.assert_not_called()
                    self.assertEqual(payload,before)

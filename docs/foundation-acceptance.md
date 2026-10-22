# Workstream 1 foundation acceptance - 17 October 2026

## Current result: Y for the agreed foundation scope

Both previously pending items are verified: the three selected provider/model combinations pass live direct-answer and real tool/result checks; configuration errors have actionable, secret-safe presentation in console and browser. This completes Workstream 1, not the whole core-agent release.

| Provider / model | Direct answer | Tool/result answer | Status |
|---|---|---|---|
| OpenRouter / nvidia/nemotron-3-super-120b-a12b:free | Y: 2.15s | Y: 4.46s | Y |
| Groq / openai/gpt-oss-20b | Y: 1.71s | Y: 2.87s | Y |
| Ollama / qwen2.5-coder:7b | Y: 57.56s including 43.60s loading | Y: 22.04s after compatibility fix | Y |

Timings are observations, not guarantees. Stored reports are outputs/acceptance/provider-openrouter.json, provider-groq.json and provider-ollama.json. OpenRouter report identifies the observed manual check; the reusable runner generated the others. The local direct result and post-fix tool result were performed separately for the same model, not represented as a new full rerun.

## Ollama diagnosis and fix

Initial tool checks failed even though the installed model advertised tools capability. A diagnostic on temporary data showed it returned a whole JSON text object with name and arguments, rather than the server's tool_calls field. agent/tool_llm.py now normalizes that exact form only for Ollama, only for registered tool names and object arguments. Prose, extra fields and claimed results are not converted into calls. Unknown tool names/malformed arguments are rejected. Caller schema/path validation and write/execute approval controls still apply.

This is a compatibility tool-call path, not a claim that the server emitted native tool_calls. The live application executed a real temporary-file read after normalization, and the model answered using the returned random verification code. No project files were sent to hosted providers. No model was downloaded or substituted, and the active .env provider remains OpenRouter.

## Configuration/error acceptance

Hosted missing keys/model settings fail before network calls. Numeric errors and unknown providers do not echo supplied configuration values. Console/browser share actionable ProviderError presentation and hide unknown exception bodies. Headless browser tests check useful error display and secret suppression. 183 guarded offline tests passed in 7.313 seconds, including compatibility, existing native adapters and frontend acceptance.

Changes: agent/user_errors.py, agent/llm_client.py, agent/tool_llm.py, agent/langgraph/langgraph_agent.py, streamlit_app.py; tests/test_foundation_errors.py, tests/test_streamlit_ui.py, tests/test_tool_llm.py.

## Repeat deliberately

```powershell
python evaluations/provider_live_acceptance.py --provider openrouter
python evaluations/provider_live_acceptance.py --provider groq
python evaluations/provider_live_acceptance.py --provider ollama
```

These use existing credentials/compute and consume hosted quota. --check native_tool_result_answer reruns only that case, preserving a prior direct result for the same model. Offline test discovery excludes live acceptance.

## Scope limits

Verification covers these configured models and acceptance cases, not every possible model/prompt or complete production readiness. Full live browser workflows, summary correctness, advanced memory, grounding, side-effect recovery and core release acceptance remain in their respective workstreams. A different model requires fresh live acceptance.


## OpenRouter endpoint recovery - 20 October 2026

User console/browser failed with MODEL_OR_ENDPOINT HTTP 404 for nvidia/nemotron-3-super-120b-a12b:free. A synthetic direct API check independently reproduced 404, so this is not caused by the package relocation. OpenRouter public endpoint metadata reported 0% uptime over the previous 30 minutes at inspection; that supports availability trouble but does not establish the exact upstream cause. No rate/quota error was observed for this request.

The free router passed a synthetic tool/result cycle but its greeting chose unnecessary reads and was slow, so it was not selected as the default. Groq passed a synthetic greeting through the shared conversation loop using openai/gpt-oss-20b, completed with no tool calls. Default LLM_PROVIDER changed to groq only; API keys, all provider models/budgets, chats and facts retained. Restart the console; select Groq in the browser or restart Streamlit for the new default. This does not implement automatic provider failover or restore the unavailable OpenRouter endpoint.

Evidence: outputs/acceptance/openrouter-404-diagnostic.json, openrouter-free-tool-check.json, groq-recovery-greeting.json and provider-recovery-settings.json. Only synthetic requests were sent; no saved user history/files. An initial greeting-check script incorrectly expected task_status on successful answers; the final check uses the actual execution_outcome contract. No production Python code changed in this recovery. Prior 428-test package acceptance remains historical; no broad-suite rerun was needed for this one-key configuration change.

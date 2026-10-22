# Provider exceptions and retries

Implemented 17 October 2026 for Ollama, Groq and OpenRouter text and native-tool HTTP requests. Existing project actions/approval controls remain unchanged. 148 guarded offline tests passed in 3.451 seconds; no live provider request was required for this change.

Errors contain provider, category, HTTP status when available, an explanation/action and attempt count. Raw provider bodies, generated failed output, proxy credentials and API keys are not logged. An error states only that no action ran from the failed response; earlier successful actions may still exist.

| Category | Meaning / response | Automatic retry |
|---|---|---|
| CONNECT_TIMEOUT / CONNECTION | Could not connect or connection dropped; check internet, DNS, proxy or local Ollama availability | Bounded |
| RESPONSE_TIMEOUT | Connected but response timed out; retry manually | No |
| TLS_CERTIFICATE / PROXY | Certificate or proxy configuration failure | No |
| AUTHENTICATION / ACCESS_DENIED | HTTP 401/403; check local key or account/model permissions | No |
| BILLING / QUOTA_EXHAUSTED | HTTP 402 or recognized exhausted quota; inspect account dashboard/reset | No |
| RATE_LIMIT | HTTP 429; may be request/token limit or unspecified quota | Only explicit numeric Retry-After from 0 to 5 seconds |
| PROVIDER_TEMPORARY | HTTP 408/500/502/503/504; temporary server/gateway failure | Bounded |
| INVALID_REQUEST / TOOL_OUTPUT | HTTP 400/422 or recognized tool/JSON failure; fix request/schema | No |
| CONTEXT_LIMIT / REQUEST_TOO_LARGE | Input/model budget or HTTP 413 | No |
| MODEL_OR_ENDPOINT | HTTP 404 or recognized missing/retired model | No |
| OUTPUT_LIMIT / CONTENT_FILTER | Native tool response truncated or filtered | No |
| INVALID_RESPONSE / INCOMPLETE_RESPONSE / MODEL_ERROR | Malformed/incomplete response or error inside HTTP success | No |
| CONFIGURATION / TRANSPORT / REDIRECT_BLOCKED / HTTP_ERROR | Invalid connection settings, other transport/status or unexpected redirect | No |

No HTTP response means no verified HTTP quota status. DNS/firewall/server causes cannot always be distinguished; messages state what was observed rather than inventing an exact cause. Category inference from known error codes/messages is not a replacement for account limits.

Defaults: two attempts total, 30-second connection timeout, one-second backoff for connection/server failures. Optional PREFIX_CONNECT_ATTEMPTS (1 to 3) and PREFIX_CONNECT_TIMEOUT (5 to 120 seconds), where PREFIX is GROQ, OPENROUTER or OLLAMA. Existing response-timeout settings remain. Requests timeouts are phase/inactivity limits, not a total wall-clock deadline. Rate-limit sleeps are at most five seconds each; retries can consume provider quota. No action execution occurs in the request helper.

Files: agent/provider_errors.py (shared exceptions/transport), agent/llm_client.py and agent/tool_llm.py (integration), tests/test_provider_errors.py and tests/test_tool_llm.py (offline regressions). Restart the running agent to load the changes.


## Project-action budget and OpenRouter compatibility

Project proposals use AI_PROJECT_MAX_TOKENS (default 4096, range 64 to 16384), independently of normal chat budgets. Valid native or text-JSON action proposals go through the same validation and existing approval handlers; ordinary final text uses the evidence-checked finish path. OpenRouter was selected in the existing .env and its live file listing/build.gradle read succeeded. Full project review remains to be tried after restart; this is not a claim of full source coverage.


## Project input-budget fix - 17 October 2026

The source-review cutoff was an application character budget, not an API quota failure. Project input now defaults to 32000 characters, with older summary/fact/history context capped to reserve evidence space. AI_PROJECT_MAX_CONVERSATION_CHARS overrides the project budget; an explicitly configured legacy AI_MAX_CONVERSATION_CHARS remains a fallback. Bounds: 4000 to 200000. Input characters are separate from AI_PROJECT_MAX_TOKENS output tokens and from the provider context/token/rate limits. A larger input can consume more API quota; this is not unlimited context.

155 offline tests pass, including a real project-loop test reading all 305 lines of a temporary source in two calls with restored context, and an explicit small-budget stop. Files: agent/project_budget.py, agent/langgraph/langgraph_agent.py, tests/test_project_budget.py. Budget exhaustion still reports incomplete and identifies the setting; no unread source is silently claimed as inspected.

The existing .env explicitly set the legacy budget to 12000. Added AI_PROJECT_MAX_CONVERSATION_CHARS=32000 for project reviews; the legacy setting and provider/key settings were retained.

Live OpenRouter verification completed successfully after the override: inspected build.gradle lines 1-100 and 101-305, returned a framework/tool summary, and did not modify files or execute project commands. This establishes this read-only review path, not complete project or production acceptance.

## Tested OpenRouter settings on 21 October 2026

The saved older Nemotron endpoint reported no recent uptime. The following model handled native review tools in live synthetic checks; this does not guarantee availability, unlimited free requests or every quality case. Its final larger-budget run hit an account quota response. The local .env was left unchanged. After quota/access is available, these are matching configuration values for the tested model (retain the existing API key privately):

```dotenv
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free
OPENROUTER_BUDGET_MODEL=nvidia/nemotron-3.5-lightning:free
OPENROUTER_CONTEXT_TOKENS=1000000
OPENROUTER_MAX_TOKENS=4096
OPENROUTER_OUTPUT_TOKEN_LIMIT=4096
```

Both model fields must match. Context and output settings above describe this inspected endpoint and finite test, not every OpenRouter model. The output cap remains below its published 65536 maximum. Restart console/Streamlit processes after changing local configuration. A provider change does not replace local embedding libraries. That earlier evaluation did not add fallback; the requested implementation is described below.


## Ordered quota fallback — 21 October 2026

The shared text/native-tool request path now supports OpenRouter -> Groq -> Gemini -> Ollama. It switches only after RATE_LIMIT or QUOTA_EXHAUSTED errors, following the existing bounded transport retry policy. Authentication, billing, TLS, invalid requests/tools, truncation and context errors still stop with their diagnostic. This is request fallback, not a replay of the agent workflow or an approved action.

Local configuration is enabled with:

```dotenv
LLM_PROVIDER=openrouter
LLM_FALLBACK_ENABLED=true
AI_DEPLOYMENT_MODE=local
LLM_ALLOW_LOCAL_OLLAMA=true
```

The primary model is now nvidia/nemotron-3.5-lightning:free, with the matching budget settings above. Existing Groq/Gemini model settings and all credentials were retained. Each fallback builds the next provider's own authentication, model and budget. Missing secondary key/model settings are skipped visibly. The selected primary's configuration errors remain explicit. Manual provider selection starts at that provider's position in the order. An exhausted provider is skipped for the rest of that conversation turn; a new turn tries the preferred provider again. This is not a persistent account-wide quota cache.

For GitHub/hosted deployment set AI_DEPLOYMENT_MODE=hosted and LLM_ALLOW_LOCAL_OLLAMA=false. GitHub Actions, CI and Codespaces indicators independently exclude Ollama, even if local permission was accidentally enabled. The checked-in CI workflow explicitly disables live fallback during offline fixture tests. A GitHub clone running on your own workstation can use local Ollama. Local automatic fallback requires a loopback endpoint and an installed/running model; CPU generation can still take minutes. Hosted environments without these known platform indicators must set the explicit hosted mode.

Console output and returned browser notices identify quota switches and the effective provider. Only the failed model request changes provider; tool results/history remain in the conversation. Google signatures are retained for Google and removed from other providers. Imported unsigned tool traces use Google's documented marker, without changing the original history or executing a tool: [Google thought signatures](https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures#faqs).

Implementation: agent/providers/fallback.py, the existing text/tools adapters and runtime turn/summary/project-decision integration. Evidence: outputs/acceptance/provider-fallback-20261021. 195 focused offline checks passed, including simulated HTTP quota switches across all four adapters, hosted exclusion, selection, summaries, notices, and existing approval/receipt regressions. One live primary OpenRouter synthetic request passed in 2.91 seconds. Real quota exhaustion was simulated; a fresh live run through all four providers and CPU Ollama generation is not claimed. Provider-specific acceptance runners disable fallback to keep attribution accurate. Restart console and Streamlit to load configuration.


## General learning step-limit correction — 21 October 2026

A browser direct-chat request exhausted six model steps. A synthetic reproduction of the inheritance follow-up selected search_text unnecessarily, despite a general-learning prompt. General explanations, definitions, examples and topic checklists now use a conservative knowledge-only policy when the current request and recent user context contain no requested source scope. No inheritance answer or programming-language response is hardcoded. Explicit project/files, saved facts, history, uploads, current facts and official-reference requests retain tools. Assistant error text such as "specify the source" does not itself turn a retry into a user source request.

The existing six-step tool loop reserves its final step for a text answer. Unexpected tools at that step are never executed; required-source and citation validation still apply. Empty tool registries/auto choice are omitted from all four native-provider payloads for text-only requests. Source work is not silently converted into a successful knowledge answer, and the existing step/tool limits and action approvals were retained.

Implementation is in agent/policies/knowledge.py, agent/runtime/conversation.py and agent/providers/tools.py. Evidence: outputs/acceptance/conversation-finalization-20261021. 226 related offline tests passed, then 40 final targeted checks passed after retry/source-scope refinements (overlapping scopes, not 266 unique tests). The exact question with synthetic prior Java context passed live OpenRouter acceptance in one call, no tools, 12.09 seconds. This verifies the observed learning case, not exhaustive educational accuracy or all possible intents. Restart console and Streamlit before retrying the question. Existing broad WS8 quality/install gates and Word synchronization status are unchanged.


## Section-based long answers and ordered failover — 21 October 2026

The selected automatic hosted order is OpenRouter -> Groq -> Gemini. Quota/rate exhaustion and OUTPUT_LIMIT can trigger provider switching. Truncated text and tool proposals are discarded before parsing/execution. Provider token budgets remain separate; the 4096/1024/4096 application caps do not become one pooled context or guaranteed visible-token allowance. Local Ollama remains manually selectable; it is excluded from the configured automatic hosted chain.

The user selected section-based generation for answers exceeding one response budget. Normal short replies keep their existing path. Conversation text overflow can invoke one bounded, data-only outline/section workflow in agent/runtime/long_answers.py. The outline defines ordered, distinct sections. Completed sections carry covered-point summaries so later requests avoid repeating them. Each section must be fully returned and validated before assembly; incomplete drafts are never concatenated. Exact repeated prose/bullets and duplicate leading section headings are consolidated; fenced code is preserved. Semantically reworded overlap and factual exhaustiveness are not mechanically guaranteed.

Only one final assembled answer is returned and archived once after all planned sections finish. If a required section fails, no assembled answer is published. Essential unresolved source tasks and unsplittable exact/JSON/code-only outputs retain the ordinary tool/single-response path. Source/citation checks and action approvals remain in force. Partial native action proposals never become text sections. Composition state is request-scoped and resets after exceptions. Planning cannot restart repeatedly during later citation corrections in the same conversation turn.

Enabled local settings: AI_LONG_ANSWERS_ENABLED=true, AI_LONG_ANSWER_MAX_SECTIONS=3, AI_LONG_ANSWER_MAX_CALLS=8, AI_LONG_ANSWER_MAX_CHARS=60000. These are bounded budgets, not an assertion that every request needs three sections. The call cap counts data-model adapter invocations; existing transport retries and quota failover can add HTTP requests. No hard total wall-clock deadline is claimed. Existing credentials and provider token caps were verified unchanged. Restart console and Streamlit to load the settings.

Evidence: outputs/acceptance/output-limit-fallback-20261021 contains 238 offline checks plus a simulated primary output-limit / real Groq completion in 4.11 seconds, with only one final reply. outputs/acceptance/sectioned-answers-20261021 contains 248 related offline checks, then 97 final focused checks after archive, heading and scope-safety refinements (overlapping sets, not additive). Its synthetic live composition passed in 23.68 seconds: real Groq outline, real OpenRouter/Groq/Gemini section requests, three sections and one final assembled reply; only the initial overflow trigger was simulated. No private histories/project files were used in that acceptance. Broader WS8 quality/install gates and Word synchronization remain unchanged.


### 2026-10-22 — Preserve brief requested formats during output-limit recovery

An output-token limit does not establish that the requested visible answer needs several sections. The existing registered internal outline response can now return mode=single_response with a complete answer string and empty sections, preserving a brief list, extraction, JSON or code request. Multi-section generation remains available for genuinely larger responses. No topic-specific response templates were added.

Inside registered data-only outline/section generation, provider TOOL_OUTPUT gets one changed schema correction, then recovery advances to the next configured provider within the existing overall call budget. Rejected generations are never read back as accepted content or executed. Other error categories and generic action/fallback policies retain their existing handling. Evidence: outputs/acceptance/brief-answer-recovery-20261022 (129 targeted checks; real Groq and Gemini recovery checks with explicitly simulated triggering failures).

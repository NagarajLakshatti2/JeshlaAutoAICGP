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

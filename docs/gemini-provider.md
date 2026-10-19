# Gemini provider configuration

Gemini is added alongside Ollama, Groq and OpenRouter. The selected local provider is gemini. No new SDK or package is required; the shared requests transport uses Google's OpenAI-compatible endpoint directly, not OpenRouter or OpenAI services.

## Current nonsecret configuration

```dotenv
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MAX_TOKENS=4096
GEMINI_OUTPUT_TOKEN_LIMIT=4096
GEMINI_REASONING_EFFORT=low
GEMINI_TIMEOUT=90
```

Existing key alias GOOGLE_AI_STUDEO_KEY is supported without copying or printing the key. Lookup precedence is GEMINI_API_KEY, GOOGLE_AI_STUDIO_KEY, GOOGLE_AI_STUDEO_KEY, GOOGLE_API_KEY. A missing key/model produces a safe configuration error before HTTP. Optional GEMINI_CONTEXT_TOKENS and GEMINI_BUDGET_MODEL use the existing preflight; no unsupported model context size was assumed. Output budgets are not usage quotas or spending controls.

## What is connected

Text answers, JSON output, native function calls, shared summaries, console and browser use the selected shared provider. Tool responses preserve opaque Gemini extra_content thought-signature metadata when present. Existing registered-tool validation, action permissions and citation guards remain. No automatic paid-model/provider fallback is enabled.

Restart the console with python -m agent.langgraph.langgraph_agent, or restart the existing Streamlit server. The initial banner should show Model provider: gemini. For a first live test, start a new chat and ask a public/general question rather than restoring private history.

## Free tier and privacy

Google currently lists free-tier input/output for gemini-3.1-flash-lite. Your project's billing tier, eligibility and quotas determine actual access and charges. This configuration cannot inspect or disable Google Cloud billing or guarantee zero charges on a paid project. Verify in Google AI Studio that the key belongs to a project using the free tier without paid billing before running it. Free quota is limited and may change. Unpaid-service content may be used to improve Google's products; shared saved facts and selected chat evidence can enter hosted requests during normal agent use.

Official references: https://ai.google.dev/gemini-api/docs/openai and https://ai.google.dev/gemini-api/docs/pricing and https://ai.google.dev/gemini-api/terms

## Validation

271 guarded offline tests passed in 30.326 seconds. Nine new Gemini tests cover existing-key aliases, missing configuration, text/JSON transport, shared dispatch, function-call signature round trips, empty tools, truncation/invalid reasoning, secret-safe key errors and no automatic quota retry. Every provider request was mocked with fake keys. No live Google request, private-data export, billing change, model download or API-key creation was performed. Live authentication, account model availability, billing/free-tier eligibility and end-to-end tool execution remain unverified.


## Live verification update 17 October 2026

After the user corrected the key, a normal console answer succeeded in 3.09 seconds. The temporary real-tool mixed-source test subsequently passed all eight checks in 19.49 seconds. Live authentication, selected-model access and the sampled tool/result loop are now verified. Account billing/free-tier eligibility remains unverified. Earlier offline-only statements above describe initial setup and are superseded for these observed live checks. See outputs/acceptance/mixed-real-tools-gemini.json.

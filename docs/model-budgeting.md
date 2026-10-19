# Provider-aware request budgeting

Implemented 17 October 2026. 174 guarded offline tests passed in 3.774 seconds.

## Implemented

- All three providers use the shared HTTP preflight for text and native tools.
- Input estimate includes serialized messages, tool schemas and JSON response-format hints, with UTF-8 byte estimation and framing allowance. Logs explicitly say estimate; no tokenizer/model is downloaded.
- Ollama uses the actual request options.num_ctx as its configured context boundary and reserves space for output.
- Hosted providers accept PREFIX_CONTEXT_TOKENS, PREFIX_OUTPUT_TOKEN_LIMIT and optional PREFIX_BUDGET_MODEL (PREFIX is OPENROUTER or GROQ). A bound-model mismatch stops before sending.
- Output is reduced to fit configured context/caps with a visible message. Input and tool evidence are never silently truncated by this helper. If estimated input plus safety reserve leaves fewer than 64 output tokens, CONTEXT_PREFLIGHT stops before network use or action execution.
- Unknown hosted context is labeled unknown. Existing unspecified provider-default output remains unspecified when no limits are supplied.
- The 32000-character project guard remains separate and unchanged. Context limits are not account rate limits or free-tier allowances.

## Current OpenRouter snapshot

Public catalog https://openrouter.ai/api/v1/models checked on 17 October 2026, without sending a key or project contents:

- Model: nvidia/nemotron-3-super-120b-a12b:free
- Model/top-provider context: 262144 tokens
- Top-provider maximum completion: 235929 tokens

Saved OPENROUTER_CONTEXT_TOKENS=262144, OPENROUTER_OUTPUT_TOKEN_LIMIT=235929 and OPENROUTER_BUDGET_MODEL matching that model in .env. Existing provider/key and project settings were retained. This is a snapshot, not automatic live discovery or a promise that every routed endpoint/account supports identical limits. Refresh when changing models/providers. No generation API call was made for this work.

## Configuration and limits

PREFIX_CONTEXT_RESERVE_TOKENS defaults to 256. LLM_TOKEN_ESTIMATE_BYTES_PER_TOKEN defaults to 3, configurable from 1 to 6. Estimates can undercount or overcount real tokenizer usage, especially code/multilingual text. Preflight cannot guarantee exact token fit. Provider errors remain authoritative.

Groq context remains unknown unless configured; no model-specific value was guessed. Ollama num_ctx is a requested context, not proof the installed model/hardware supports every chosen value. No automatic increase of local context, provider switching, paid-service enablement, or new dependency was introduced.

Pending: exact/model-aware tokenizer counting, quota-aware scheduling, metadata refresh, actual usage calibration and context compaction/chunk planning when a request cannot fit.

Files: agent/model_budget.py, agent/provider_errors.py, tests/test_model_budget.py and the three model-budget entries in .env.

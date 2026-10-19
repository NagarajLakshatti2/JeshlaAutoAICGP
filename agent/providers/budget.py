"""Provider context preflight with explicitly labeled local token estimates.

No tokenizer/model downloads, remote model discovery or cross-provider calls.
Configured hosted limits are operator supplied, not claims about live quotas.
"""
import json
import math
import os


def apply_model_budget(provider, payload):
    from agent.providers.errors import ProviderError
    if not isinstance(payload,dict) or not isinstance(payload.get("messages"),list):
        return payload
    prefix=provider.upper()
    def integer(name,default=None):
        raw=os.getenv(name)
        if raw is None:return default
        try:
            value=int(raw)
            if value<1:raise ValueError()
            return value
        except (TypeError,ValueError):
            raise ProviderError(provider,"CONFIGURATION",f"{name} must be a positive integer.",attempts=0) from None
    try:
        ratio=float(os.getenv("LLM_TOKEN_ESTIMATE_BYTES_PER_TOKEN","3"))
        if not math.isfinite(ratio) or not 1<=ratio<=6:raise ValueError()
    except (TypeError,ValueError):
        raise ProviderError(provider,"CONFIGURATION","LLM_TOKEN_ESTIMATE_BYTES_PER_TOKEN must be from 1 to 6.",attempts=0) from None
    # Include schemas and framing; UTF-8 bytes reflect non-ASCII text better than chars.
    content={key:payload[key] for key in ("messages","tools","response_format") if key in payload}
    estimate=math.ceil(len(json.dumps(content,ensure_ascii=False,separators=(",", ":")).encode("utf-8"))/ratio)
    estimate+=16*len(payload["messages"])+64
    result=dict(payload)
    if provider=="ollama":
        options=dict(payload.get("options",{}))
        context=options.get("num_ctx")
        output=options.get("num_predict")
        output_key="num_predict"
        source="configured Ollama num_ctx"
    else:
        context=integer(prefix+"_CONTEXT_TOKENS")
        output_key="max_completion_tokens" if provider=="groq" else "max_tokens"
        output=payload.get(output_key)
        source="configured provider context"
        bound=os.getenv(prefix+"_BUDGET_MODEL","").strip()
        if bound and bound!=payload.get("model"):
            raise ProviderError(provider,"CONFIGURATION",f"{prefix}_BUDGET_MODEL does not match the selected model. Update its budget configuration before sending.",attempts=0)
    cap=integer(prefix+"_OUTPUT_TOKEN_LIMIT")
    if output is None and cap is None and context is None:
        print(f"{prefix} BUDGET | input ~{estimate} tokens (estimate) | output: provider default | context: unknown; no model-context fit guarantee")
        return result
    if output is None:
        output=cap if cap is not None else integer(prefix+"_MAX_TOKENS",1024)
    if type(output) is not int or output<1:
        raise ProviderError(provider,"CONFIGURATION","Requested output-token budget must be a positive integer.",attempts=0)
    requested=output
    if cap is not None:output=min(output,cap)
    if context is not None:
        if type(context) is not int or context<1:
            raise ProviderError(provider,"CONFIGURATION","Configured context must be a positive integer.",attempts=0)
        safety=integer(prefix+"_CONTEXT_RESERVE_TOKENS",256)
        available=context-estimate-safety
        if available<64:
            raise ProviderError(provider,"CONTEXT_PREFLIGHT",
                f"Estimated input {estimate} tokens plus {safety} reserve leaves insufficient output space in the configured {context}-token context. Narrow evidence/history or configure the model context correctly. Estimate is approximate; no request sent.",attempts=0)
        output=min(output,available)
    if provider=="ollama":
        options[output_key]=output;result["options"]=options
    else:result[output_key]=output
    context_label=f"{context} ({source})" if context is not None else "unknown; no model-context fit guarantee"
    print(f"{prefix} BUDGET | input ~{estimate} tokens (estimate) | output <= {output} tokens | context: {context_label}")
    if output!=requested:
        print(f"{prefix} BUDGET | output reduced from {requested} to {output} to respect configured limits; input was not silently truncated.")
    return result

"""Provider adapter for native function calls; no tool execution occurs here."""
import json
import os
import time
import uuid
import requests
from agent.providers.text import LLM_PROVIDER, OLLAMA_URL, OLLAMA_MODEL, OPENROUTER_URL, OPENROUTER_MODEL, env_int
from agent.timing import timed
from agent.providers.errors import request_model, ProviderError, read_model_json


def ollama_text_tool_call(content, tools):
    """Recognize only a whole JSON tool proposal, never prose or claimed results."""
    try:
        proposal=json.loads(content)
    except (ValueError,TypeError):
        return None
    if not isinstance(proposal,dict) or set(proposal)!={"name","arguments"}:
        return None
    registered={item.get("function",{}).get("name") for item in tools if isinstance(item,dict)}
    name=proposal.get("name")
    if not isinstance(name,str) or name not in registered:
        raise ProviderError("ollama","INVALID_TOOL","Model proposed an unregistered tool. No action was executed; correct the request/tool schema.")
    if not isinstance(proposal.get("arguments"),dict):
        raise ProviderError("ollama","INVALID_TOOL","Tool arguments must be a JSON object. No action was executed.")
    return {"function":{"name":name,"arguments":proposal["arguments"]}}


@timed("LLM tool request")
def call_tool_messages(messages, tools, *, max_tokens=None, forced_function=None, require_tool=False):
    if max_tokens is not None and (type(max_tokens) is not int or not 64 <= max_tokens <= 16384):
        raise ValueError("Output budget must be an integer from 64 to 16384.")
    if type(require_tool) is not bool or (require_tool and (not tools or forced_function is not None)):
        raise ValueError("Required tool selection needs registered tools and no conflicting forced function.")
    if forced_function is not None:
        registered={item.get("function",{}).get("name") for item in tools if isinstance(item,dict)}
        if not isinstance(forced_function,str) or forced_function not in registered:
            raise ValueError("Forced function must be registered in this request.")
    provider = LLM_PROVIDER
    payload = {"messages": messages, "tools": tools, "stream": False}
    headers = {"Content-Type": "application/json"}
    if provider == "ollama":
        url = OLLAMA_URL
        payload.update(model=OLLAMA_MODEL, keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
                       options={"temperature": 0, "num_ctx": env_int("OLLAMA_NUM_CTX", 4096, 1024, 131072),
                                "num_predict": max_tokens if max_tokens is not None else env_int("OLLAMA_NUM_PREDICT", 1024, 64, 16384)})
        converted = []
        for message in messages:
            item = dict(message)
            if item.get("tool_calls"):
                item["tool_calls"] = [{"function": {"name": call["function"]["name"],
                    "arguments": json.loads(call["function"]["arguments"])}} for call in item["tool_calls"]]
            if item["role"] == "tool":
                item["tool_name"] = item.pop("name", "")
                item.pop("tool_call_id", None)
            converted.append(item)
        payload["messages"] = converted
        timeout = env_int("OLLAMA_TIMEOUT", 600, 30, 3600)
    elif provider in {"groq", "openrouter"}:
        prefix = "GROQ" if provider == "groq" else "OPENROUTER"
        key = os.getenv(prefix + "_API_KEY", "").strip()
        model = os.getenv("GROQ_MODEL", "").strip() if provider == "groq" else OPENROUTER_MODEL
        if not key or not model:
            raise ProviderError(provider,"CONFIGURATION",f"Configure {prefix}_API_KEY and {prefix}_MODEL locally in .env and restart.",attempts=0)
        url = "https://api.groq.com/openai/v1/chat/completions" if provider == "groq" else OPENROUTER_URL
        headers["Authorization"] = f"Bearer {key}"
        payload.update(model=model, temperature=0, tool_choice="auto")
        payload["max_completion_tokens" if provider == "groq" else "max_tokens"] = max_tokens if max_tokens is not None else env_int(prefix + "_MAX_TOKENS", 1024, 64, 32768)
        timeout = env_int(prefix + "_TIMEOUT", 90, 10, 600)
    elif provider == "gemini":
        from agent.providers.gemini import GEMINI_URL, credentials, reasoning_effort
        key,model=credentials();url=GEMINI_URL
        headers["Authorization"]=f"Bearer {key}"
        payload.update(model=model,temperature=0,reasoning_effort=reasoning_effort(),
                       max_tokens=max_tokens if max_tokens is not None else env_int("GEMINI_MAX_TOKENS",4096,64,32768))
        if tools:payload["tool_choice"]="auto"
        else:payload.pop("tools",None)
        timeout=env_int("GEMINI_TIMEOUT",90,10,600)
    else:
        raise ProviderError("model","CONFIGURATION","Set LLM_PROVIDER to groq, openrouter, ollama or gemini in .env and restart.",attempts=0)
    if provider=="groq" and forced_function is not None:
        payload["tool_choice"]={"type":"function","function":{"name":forced_function}}
        payload["parallel_tool_calls"]=False
    if provider=="groq" and require_tool:
        payload["tool_choice"]="required"
        payload["parallel_tool_calls"]=False
    started = time.perf_counter()
    response = request_model(provider,url,headers=headers,json=payload,
                             timeout=(10,timeout),allow_redirects=False)
    try:
        data = read_model_json(response,provider)
        if provider == "ollama":
            if data.get("done_reason") == "length" or data.get("error"):
                raise ValueError()
            message = data["message"]
        else:
            choice = data["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ProviderError(provider,"OUTPUT_LIMIT","Model output reached its token limit. Increase the output budget within model limits or narrow the task; no automatic retry.")
            if choice.get("finish_reason") == "content_filter":
                raise ProviderError(provider,"CONTENT_FILTER","Provider filtered this response; no automatic retry.")
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise ValueError()
            message = choice["message"]
        content = message.get("content") or ""
        calls = message.get("tool_calls") or []
        if provider=="ollama" and not calls and isinstance(content,str):
            proposal=ollama_text_tool_call(content,tools)
            if proposal is not None:
                calls=[proposal]
                content=""
                print("Ollama compatibility: normalized a registered tool proposal from JSON text; execution remains subject to caller validation.")
        if not isinstance(content, str) or not isinstance(calls, list) or len(calls) > 8:
            raise ValueError()
        normalized = []
        for call in calls:
            fn = call["function"]
            args = fn.get("arguments", {})
            if not isinstance(args, (str, dict)) or not isinstance(fn["name"], str):
                raise ValueError()
            normalized.append({"id": call.get("id") or "call_" + uuid.uuid4().hex,
                               "type": "function", "function": {"name": fn["name"],
                               "arguments": args if isinstance(args, str) else json.dumps(args)}})
        if provider=="gemini":
            # Gemini may require opaque thought signatures on subsequent tool turns.
            for original,converted in zip(calls,normalized):
                if isinstance(original.get("extra_content"),dict):
                    converted["extra_content"]=original["extra_content"]
        if not content.strip() and not normalized:
            raise ValueError()
        ids = [call["id"] for call in normalized]
        if any(not isinstance(value, str) for value in ids) or len(set(ids)) != len(ids):
            raise ValueError()
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ProviderError(provider,"INVALID_RESPONSE","Model returned incomplete, truncated or invalid tool output. Narrow the request or check output-token settings; no retry performed.") from None
    print(f"Provider: {provider} | Model: {payload['model']} | Request: {time.perf_counter()-started:.2f}s")
    return {"role": "assistant", "content": content, **({"tool_calls": normalized} if normalized else {})}

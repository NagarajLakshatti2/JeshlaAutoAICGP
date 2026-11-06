"""One-shot isolated AutoGen AgentChat process; emits one JSON result on stdout."""
import asyncio
import inspect
import json
import os
import sys
from typing import Any, Optional


def _stage(name):
    # Stage names only; never log prompts, tool arguments, credentials or responses.
    print("AUTOGEN_STAGE " + name, file=sys.stderr, flush=True)


def _supports_native_json_output(provider, requested):
    """Use native JSON mode only where this app already requests it."""
    return requested is True and provider in {"groq", "gemini"}

def _annotation(rule):
    kind = rule.get("type")
    if kind == "string": return str
    if kind == "integer": return int
    if kind == "number": return float
    if kind == "boolean": return bool
    if kind == "array": return list[Any]
    if kind == "object": return dict[str, Any]
    return Any


def _capture_tool(spec, captured):
    from autogen_core.tools import FunctionTool
    function = spec["function"]
    schema = function["parameters"]
    required = set(schema.get("required", []))

    async def capture(**arguments) -> str:
        captured.append({"name": function["name"], "arguments": arguments})
        return "Proposal returned to JeshlaAutoAI for its normal validation. No project action executed here."

    capture.__name__ = function["name"]
    annotations = {"return": str}
    parameters = []
    for name, rule in schema.get("properties", {}).items():
        annotation = _annotation(rule)
        default = inspect.Parameter.empty if name in required else None
        if default is None:
            annotation = Optional[annotation]
        annotations[name] = annotation
        parameters.append(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation))
    capture.__annotations__ = annotations
    capture.__signature__ = inspect.Signature(parameters, return_annotation=str)

    class ExactSchemaTool(FunctionTool):
        @property
        def schema(self):
            return {"name": function["name"], "description": function.get("description", ""),
                    "parameters": schema, "strict": False}
    return ExactSchemaTool(capture, description=function.get("description", ""), name=function["name"])


def _provider_error(error):
    from agent.providers.errors import ProviderError
    if isinstance(error, ProviderError):
        messages = {
            "CONFIGURATION": "Configure the selected provider model and local key.",
            "OUTPUT_LIMIT": "Model output reached its token limit; partial output was discarded.",
            "RATE_LIMIT": "Provider rate or quota limit reached.",
            "QUOTA_EXHAUSTED": "Provider quota appears exhausted.",
        }
        return {"category": error.category, "status": error.status,
                "error": messages.get(error.category, "Provider request could not be completed.")}
    response = getattr(error, "response", None)
    status = getattr(error, "status_code", None) or getattr(response, "status_code", None)
    name = type(error).__name__.lower()
    if status == 429:
        return {"category": "RATE_LIMIT", "status": status, "error": "Provider rate or quota limit reached."}
    if status in {401, 403}:
        return {"category": "AUTHENTICATION", "status": status, "error": "Provider rejected the configured credentials or access."}
    if status == 404:
        return {"category": "MODEL_OR_ENDPOINT", "status": status, "error": "Selected model or provider endpoint was not found."}
    if status == 400:
        return {"category": "TOOL_OUTPUT", "status": status, "error": "Provider rejected the generated tool request."}
    if "timeout" in name:
        return {"category": "RESPONSE_TIMEOUT", "status": status, "error": "Provider request timed out."}
    if status and status >= 500:
        return {"category": "PROVIDER_TEMPORARY", "status": status, "error": "Provider is temporarily unavailable."}
    return {"category": "CONNECTION", "status": status, "error": "Provider request could not be completed."}


async def _run(request):
    _stage("async_request_started")
    from integrations.autogen.provider_config import provider_config

    provider = request["provider"]
    config = provider_config(provider)
    _stage("provider_configured provider=" + provider)
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    native_json_output = _supports_native_json_output(provider, request.get("json_mode"))
    model_info = {"vision": False, "function_calling": True, "json_output": native_json_output,
                  "structured_output": False, "family": "unknown"}
    class BoundedOpenAIChatCompletionClient(OpenAIChatCompletionClient):
        async def create(self, *args, **kwargs):
            if native_json_output:
                kwargs["json_output"] = True
            if provider == "gemini":
                from agent.providers.gemini import reasoning_effort
                extra = kwargs.get("extra_create_args")
                extra = dict(extra) if isinstance(extra, dict) else {}
                extra.setdefault("reasoning_effort", reasoning_effort())
                kwargs["extra_create_args"] = extra
            result = await super().create(*args, **kwargs)
            if result.finish_reason == "length":
                from agent.providers.errors import ProviderError
                raise ProviderError(provider, "OUTPUT_LIMIT", "Model output reached its token limit; partial output discarded.", attempts=1)
            return result

    client = BoundedOpenAIChatCompletionClient(model=config["model"], api_key=config["api_key"], base_url=config["base_url"],
        model_info=model_info, max_tokens=request["max_tokens"], parallel_tool_calls=False, temperature=0)
    _stage("model_client_created provider=" + provider)
    captured = []
    tools = [_capture_tool(item, captured) for item in request.get("tools", [])]
    systems = [item.get("content", "") for item in request.get("messages", []) if item.get("role") == "system"]
    history = [item for item in request.get("messages", []) if item.get("role") != "system"]
    system = "\n\n".join(systems)
    if request.get("json_mode") is True:
        system += "\nReturn exactly one valid JSON object and no surrounding Markdown."
    system += ("\n\nYou are operating through AutoGen AgentChat. Use supplied tools for evidence and registered actions. "
               "Tool functions return proposals to the existing application; never claim a proposed action executed. "
               "For code work, inspect relevant project files, explain concrete changes, and use a proposal tool only when the request requires a file change or test run. "
               "Do not claim tests ran unless actual test evidence is returned. Return one concise, coherent answer without repeated explanations.")
    agent = AssistantAgent(name="jeshla_code_assistant", model_client=client, tools=tools,
        system_message=system, reflect_on_tool_use=False, max_tool_iterations=1)
    try:
        _stage("agent_run_started provider=" + provider)
        result = await agent.run(task=json.dumps(history, ensure_ascii=False))
        _stage("agent_run_completed provider=" + provider)
        content = ""
        for message in reversed(result.messages):
            value = getattr(message, "content", None)
            if isinstance(value, str) and value.strip():
                content = value
                break
        return {"content": content, "tool_calls": captured}
    finally:
        await client.close()


def main():
    # The host communicates with this isolated process as UTF-8. Windows' console
    # default (often cp1252) cannot encode many valid model response characters.
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    for line in sys.stdin:
        try:
            request = json.loads(line)
            _stage("request_received provider=" + str(request.get("provider", "unknown")))
            result = asyncio.run(_run(request))
        except Exception as error:
            result = {"error": _provider_error(error)["error"], **_provider_error(error)}
            _stage("request_failed category=" + str(result.get("category", "unknown")))
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

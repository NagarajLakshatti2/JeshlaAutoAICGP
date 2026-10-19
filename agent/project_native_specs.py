"""Native project proposal schemas derived from the registered handler signatures."""
import inspect
from typing import get_origin,get_args

def argument_schema(annotation):
    origin=get_origin(annotation)
    if annotation is str:return {"type":"string"}
    if annotation is int:return {"type":"integer"}
    if annotation is bool:return {"type":"boolean"}
    if annotation is float:return {"type":"number"}
    if origin is list or annotation is list:
        values=get_args(annotation)
        return {"type":"array","items":argument_schema(values[0]) if values else {}}
    if origin is dict or annotation is dict:return {"type":"object","additionalProperties":True}
    return {}

def native_project_specs(actions):
    specs=[]
    for name,handler in sorted(actions.items()):
        properties={};required=[]
        try:parameters=inspect.signature(handler).parameters
        except (ValueError,TypeError):parameters={}
        for key,param in parameters.items():
            properties[key]=argument_schema(param.annotation)
            if param.default is inspect.Parameter.empty:required.append(key)
        specs.append({"type":"function","function":{"name":name,
            "description":"Propose this project action only. Application validation and explicit approval control execution.",
            "parameters":{"type":"object","properties":properties,"required":required,"additionalProperties":False}}})
    for name,field in [("ask","question"),("finish","answer")]:
        specs.append({"type":"function","function":{"name":name,"description":"Ask for essential missing details." if name=="ask" else "Answer only from recorded evidence; never claim unexecuted actions.",
            "parameters":{"type":"object","properties":{field:{"type":"string","minLength":1}},"required":[field],"additionalProperties":False}}})
    return specs

def decode_native_project_reply(reply,actions):
    import json
    calls=reply.get("tool_calls") or []
    if len(calls)!=1:raise ValueError("Return exactly one registered native project proposal.")
    fn=calls[0].get("function",{});name=fn.get("name")
    if name not in set(actions)|{"ask","finish"}:raise ValueError("Unknown native project proposal function.")
    try:args=json.loads(fn["arguments"])
    except (ValueError,TypeError,KeyError):raise ValueError("Native project arguments must be valid JSON.") from None
    if not isinstance(args,dict):raise ValueError("Native project arguments must be an object.")
    if name in {"ask","finish"}:
        field="question" if name=="ask" else "answer"
        if set(args)!={field} or not isinstance(args[field],str) or not args[field].strip():raise ValueError("Clarification/final text is required.")
        return json.dumps({"action":name,field:args[field]},ensure_ascii=False)
    spec=next(item["function"]["parameters"] for item in native_project_specs(actions) if item["function"]["name"]==name)
    if set(args)-set(spec["properties"]) or set(spec["required"])-set(args):
        raise ValueError("Native project proposal has missing or unexpected arguments.")
    return json.dumps({"action":name,"arguments":args},ensure_ascii=False)

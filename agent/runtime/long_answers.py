"""Bounded data-only planning and section generation; drafts never execute tools."""
import json
import os
import re

from agent.providers.errors import ProviderError
from agent.providers.fallback import configured_order, last_provider
from agent.providers.selection import current_provider, provider_selection, output_limit_passthrough
from agent.providers.text import LLM_PROVIDER, env_int
from agent.runtime.timing import timed


def enabled():
    from agent.providers.fallback import enabled as fallback_enabled
    return fallback_enabled() and os.getenv("AI_LONG_ANSWERS_ENABLED","false").lower()=="true"


def _decode(reply,name):
    calls=reply.get("tool_calls") or []
    if calls:
        if len(calls)!=1:raise ValueError("Return one registered data function.")
        fn=calls[0].get("function",{})
        if fn.get("name") not in {name,"functions."+name}:raise ValueError("Unexpected data function.")
        raw=fn.get("arguments")
    else:raw=reply.get("content","")
    if isinstance(raw,str) and raw.strip().startswith("```json") and raw.strip().endswith("```"):
        raw=raw.strip()[7:-3].strip()
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError("Return a JSON object.")
    return value


def _spec(name,properties,required):
    return {"type":"function","function":{"name":name,
        "description":"Return answer-planning data only. No actions, permissions or tool execution.",
        "parameters":{"type":"object","properties":properties,"required":required,"additionalProperties":False}}}


def _clean_repetition(content,paragraphs,bullets):
    # Preserve code verbatim, including significant blank lines and indentation.
    if "```" in content or "~~~" in content:return content.strip()
    kept=[];in_code=False
    for block in re.split(r"\n\s*\n",content.strip()):
        code=in_code or "```" in block or "~~~" in block
        if (block.count("```")+block.count("~~~"))%2:in_code=not in_code
        if code or "|" in block:
            kept.append(block);continue
        key=" ".join(block.split()).casefold()
        is_list=bool(re.match(r"\s*(?:[-*+] |\d+[.)] )",block))
        if not is_list and len(key)>=80:
            if key in paragraphs:continue
            paragraphs.add(key)
        lines=[]
        for line in block.splitlines():
            match=re.match(r"\s*(?:[-*+] |\d+[.)] )(.+)",line)
            key=" ".join(match.group(1).split()).casefold() if match else ""
            if len(key)>=20:
                if key in bullets:continue
                bullets.add(key)
            lines.append(line)
        if any(line.strip() for line in lines):kept.append("\n".join(lines))
    return "\n\n".join(kept)


@timed("Long answer composition")
def compose_long_answer(messages,model,*,failed_provider,allow_partial=False,resume=None):
    """Return one assembled answer, or None when more source tools are needed."""
    order=configured_order();selected=current_provider(LLM_PROVIDER)
    order=order[order.index(selected):] if selected in order else (selected,)
    maximum=env_int("AI_LONG_ANSWER_MAX_SECTIONS",3,2,6)
    call_limit=env_int("AI_LONG_ANSWER_MAX_CALLS",8,3,20)
    char_limit=env_int("AI_LONG_ANSWER_MAX_CHARS",60000,4000,200000)
    input_limit=env_int("AI_CHAT_MAX_CONVERSATION_CHARS",36000,4000,200000)
    trace=[];call_count=0
    short={"type":"string","minLength":1,"maxLength":240}
    plan_spec=_spec("submit_answer_outline",{
        "mode":{"type":"string","enum":["answer","needs_tools","single_response"]},"title":short,
        "scope":short,"answer":{"type":"string","minLength":1,"maxLength":char_limit},
        "sections":{"type":"array","maxItems":maximum,"items":{
            "type":"object","properties":{"title":short,"purpose":short},"required":["title","purpose"],"additionalProperties":False}}},
        ["mode","title","scope","sections"])
    section_spec=_spec("submit_answer_section",{
        "section_id":{"type":"string"},"content":{"type":"string","minLength":1},
        "covered_points":{"type":"array","maxItems":8,"items":short}},["section_id","content","covered_points"])

    def data_request(provider,prompt,spec,validate):
        nonlocal call_count
        begin=order.index(provider)
        last=None;failed_output=set()
        for candidate in order[begin:]:
            if candidate in failed_output:continue
            request=[*messages,{"role":"system","content":prompt}]
            for correction in range(2):
                if call_count>=call_limit:
                    raise ProviderError("model","LONG_ANSWER_LIMIT","Long-answer request budget reached; no assembled answer was published.")
                if sum(len(json.dumps(item,ensure_ascii=False)) for item in request)>input_limit:
                    raise ProviderError("model","CONTEXT_LIMIT","Section planning exceeds the input budget; no assembled answer was published.")
                call_count+=1
                try:
                    with provider_selection(candidate),output_limit_passthrough(data_only=True):
                        reply=model(request,[spec])
                        actual=last_provider(candidate)
                except ProviderError as error:
                    if error.category=="TOOL_OUTPUT":
                        # These are registered data-only functions, never actions.
                        # A changed format correction is safe; rejected generations
                        # are neither decoded nor reused as content/permissions.
                        last=error
                        if not correction:
                            request.append({"role":"user","content":
                                "The provider rejected the generated data format. Return exactly one registered "+
                                spec["function"]["name"]+" function with arguments matching its schema. "+
                                "No historical or unrelated tool names, extra fields, commentary or partial data. "+
                                "Keep the response brief and fully finished; this function only returns data."})
                            print(f"Long answer: correcting {error.provider} data format once.")
                            continue
                        failed_output.add(error.provider)
                        print(f"Long answer: {error.provider} rejected data format after correction; trying the next configured provider.")
                        break
                    if error.category!="OUTPUT_LIMIT":raise
                    last=error;failed_output.add(error.provider);break
                try:
                    value=_decode(reply,spec["function"]["name"])
                    validate(value)
                    trace.append({"provider":actual,"data_function":spec["function"]["name"]})
                    return value,actual
                except (ValueError,TypeError,KeyError):
                    if correction:
                        raise ProviderError(actual,"LONG_ANSWER_FORMAT","Could not validate section data after one correction; no assembled answer was published.") from None
                    request.append({"role":"user","content":"Return exactly one valid object through the registered data function. Follow its required fields and the assigned section. Do not return other tool calls or repeat earlier sections."})
        if last is not None:raise last
        raise ProviderError("model","PROVIDERS_UNAVAILABLE","No provider could complete the requested answer section.")

    def validate_plan(value):
        fields={"mode","title","scope","sections"}
        if not fields<=set(value) or set(value)-fields-{"answer"} or value["mode"] not in {"answer","needs_tools","single_response"}:raise ValueError()
        if "answer" in value and (value["mode"]!="single_response" or not isinstance(value["answer"],str) or not value["answer"].strip() or len(value["answer"])>char_limit):raise ValueError()
        if not all(isinstance(value[key],str) and 0<len(value[key].strip())<=240 for key in ("title","scope")):raise ValueError()
        sections=value["sections"]
        if not isinstance(sections,list) or not 0<=len(sections)<=maximum:raise ValueError()
        if value["mode"]=="answer" and len(sections)<2:raise ValueError()
        if value["mode"]!="answer" and sections:raise ValueError()
        for part in sections:
            if set(part)!={"title","purpose"} or not all(isinstance(v,str) and 0<len(v.strip())<=240 for v in part.values()):raise ValueError()
        if any("\n" in part["title"] or "\r" in part["title"] for part in sections):raise ValueError()
        if len({" ".join(part["title"].split()).casefold() for part in sections})!=len(sections):raise ValueError()

    if resume is not None:
        from agent.runtime.continuations import validate_ledger
        validate_ledger(resume)
        if not allow_partial or messages!=resume["messages"]:raise ValueError("Use the saved text continuation context.")
        plan=resume["outline"]
    else:
        start=order[min(order.index(failed_provider)+1,len(order)-1)] if failed_provider in order else order[0]
        plan,_=data_request(start,
        "A provider hit an output limit, which may include hidden reasoning. This does not establish that the user wants a long answer. "
        "Use only submit_answer_outline. First decide the response length and format from the LATEST user request, not from the length of quoted history. "
        "For a response that can fit one request, including concise extraction, reformatting, a short list, exact output, JSON or code, "
        "return mode=single_response, sections=[], and answer containing the complete requested final response in its exact requested format. "
        "Do not add section headings, scope notes, examples, explanations or recaps when they were not requested. "
        "Preserve exact source URLs and citation labels from the actually supplied evidence in single_response as well as section mode. Do not replace them with guessed publisher homepages, newer version paths or unread specification links. "
        "For follow-ups use the complete previous_exchange as source material; do not regenerate or expand that earlier answer. "
        "Only if the requested response itself needs multiple budgets, return mode=answer and plan 2 to "+str(maximum)+
        " distinct, non-overlapping sections in a natural order. Omit answer for this mode. Do not answer these sections yet. "
        "No tool here can inspect sources or execute actions. If more source tools are essential, return mode=needs_tools with sections=[] and omit answer. "
        "Use mode=answer only when the supplied context/knowledge is sufficient. Scope must be honest; never claim verified 100 percent coverage. Keep the outline short.",plan_spec,validate_plan)
    if plan["mode"]=="single_response" and plan.get("answer"):
        return {"role":"assistant","content":plan["answer"].strip(),
                "composition":{"sections":0,"model_calls":call_count,"trace":trace,"mode":"single_response"}}
    if plan["mode"]!="answer":return None
    from agent.runtime.continuations import make_ledger,save_progress,validate_ledger,section_issue,content_identity
    completed=list(resume["completed"]) if resume else []
    published=resume["published"] if resume else 0
    ledger_id=resume["id"] if resume else None
    origin=resume["origin_question"] if resume else None
    saved_progress=False
    def pack_partial(error):
        ledger=make_ledger(messages,plan,completed,identity=ledger_id,question=origin,published=published)
        content=render_answer(plan,completed,start=published) if len(completed)>published else "No new complete section is available yet."
        category=error.category if re.fullmatch(r"[A-Z_]{1,50}",error.category) else "PROVIDER_ERROR"
        content+="\n\nPartial answer: "+str(len(completed))+"/"+str(len(plan["sections"]))+" sections complete. Paused: "+category+"."
        return {"role":"assistant","content":content,"continuation":ledger,
                "composition":{"sections":len(completed),"new_sections":len(completed)-published,"model_calls":call_count,
                               "trace":trace,"partial":True,"continuation_saved":saved_progress,"stop_reason":category}}
    if allow_partial:
        ledger=make_ledger(messages,plan,completed,identity=ledger_id,question=origin,published=published)
        ledger_id=ledger["id"]
        try:saved_progress=save_progress(ledger)
        except ProviderError as error:return pack_partial(error)
        section_spec["function"]["parameters"]["properties"]["complete"]={"type":"boolean"}
        section_spec["function"]["parameters"]["required"].append("complete")
    highest=0
    generation_start=len(completed)
    for index in range(generation_start,len(plan["sections"])):
        part=plan["sections"][index]
        identity="section-"+str(index+1)
        def validate_section(value):
            expected={"section_id","content","covered_points"}|({"complete"} if allow_partial else set())
            if set(value)!=expected or value["section_id"]!=identity:raise ValueError()
            if allow_partial:
                if value["complete"] is not True:raise ValueError()
                issue=section_issue(value.get("content"),origin or "")
                if issue and "requires technical source review" in issue:
                    raise ProviderError("model","ANSWER_REVIEW_REQUIRED","The remaining code section requires the existing technical-review flow. Text continuation cannot bypass it.")
                if issue:raise ValueError()
            if not isinstance(value["content"],str) or not value["content"].strip() or len(value["content"])>char_limit:raise ValueError()
            if any(content_identity(value["content"])==content_identity(item["content"]) for item in completed):raise ValueError()
            if not isinstance(value["covered_points"],list) or len(value["covered_points"])>8:raise ValueError()
            if any(not isinstance(item,str) or not item.strip() or len(item)>240 for item in value["covered_points"]):raise ValueError()
            prior_points={" ".join(point.split()).casefold() for part in completed for point in part["covered_points"]}
            if allow_partial and "```" not in value["content"] and "~~~" not in value["content"] and value["covered_points"] and all(" ".join(point.split()).casefold() in prior_points for point in value["covered_points"]):raise ValueError()
        context={"outline":plan,"assigned_section_id":identity,"assigned_section":part,
            "already_completed":[{"section_id":item["section_id"],"covered_points":item["covered_points"]} for item in completed]}
        try:
            value,actual=data_request(order[min(max(index-generation_start,highest),len(order)-1)],
                "Use only submit_answer_section. Write ONLY the assigned section's content, not an introduction, recap, other sections or a closing offer. "
                "Respect the latest requested format and detail level; do not add examples unless appropriate. "
                "Do not repeat completed points. Preserve source references from the supplied evidence. No sources were retrieved by this data function. "
                "Never claim an action executed or that unverified coverage is exhaustive. The application adds the section title. "
                +("Mark complete=true only for a finished section with closed code blocks; otherwise complete=false. " if allow_partial else "")+"Return a fully finished section within this response budget. Section assignment: "+json.dumps(context,ensure_ascii=False),section_spec,validate_section)
            highest=max(highest,order.index(actual))
            candidate=[*completed,value]
            if len(render_answer(plan,candidate))>char_limit:
                raise ProviderError("model","LONG_ANSWER_LIMIT","Combined answer exceeds its configured size budget; the next section was held back.")
            if allow_partial:
                ledger=make_ledger(messages,plan,candidate,identity=ledger_id,question=origin,published=published)
                saved_progress=save_progress(ledger)
            completed.append(value)
        except ProviderError as error:
            if not allow_partial:raise
            return pack_partial(error)
        print(f"Long answer: section {index+1}/{len(plan['sections'])} completed using {actual}.")
    answer=render_answer(plan,completed)
    if len(answer)>char_limit:raise ProviderError("model","LONG_ANSWER_LIMIT","Assembled answer exceeds its configured size budget.")
    if allow_partial:
        ledger=make_ledger(messages,plan,completed,identity=ledger_id,question=origin,published=published)
        return {"role":"assistant","content":render_answer(plan,completed,start=published),"continuation":ledger,
                "composition":{"sections":len(completed),"new_sections":len(completed)-published,"model_calls":call_count,"trace":trace,"partial":False}}
    return {"role":"assistant","content":answer,"composition":{"sections":len(completed),"model_calls":call_count,"trace":trace}}


def render_answer(plan, completed, *, start=0):
    paragraphs=set();bullets=set();rendered=[]
    for part,value in zip(plan["sections"],completed):
        body=value["content"].strip()
        first,*remaining=body.splitlines()
        heading=re.sub(r"^#{1,6}\s+|^\*\*|\*\*:?$","",first).strip().rstrip(":")
        if " ".join(heading.split()).casefold()==" ".join(part["title"].split()).casefold():
            body="\n".join(remaining).strip()
        body=_clean_repetition(body,paragraphs,bullets)
        if not body.strip():raise ProviderError("model","LONG_ANSWER_DUPLICATE","A section contained only repeated material; no assembled answer was published.")
        rendered.append("## "+part["title"]+"\n\n"+body)
    body="\n\n".join(rendered[start:])
    return ("# "+plan["title"]+"\n\n"+plan["scope"]+"\n\n"+body) if start==0 else body

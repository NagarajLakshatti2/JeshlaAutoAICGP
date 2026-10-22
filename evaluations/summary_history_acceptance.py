"""Explicit read-only summary diagnosis. Synthetic or redacted selected default chat.

Only structural diagnostics are saved; live calls use the configured provider.
This runner never commits a summary or changes an application checkpoint.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def selected_history():
    from langgraph.checkpoint.sqlite import SqliteSaver
    user = os.getenv("AI_MEMORY_USER_ID", "local-user")
    space = os.getenv("AI_MEMORY_NAMESPACE", "project")
    identity = json.dumps([user, space, "default"], ensure_ascii=False)
    thread = "main-agent-session" if (user, space) == ("local-user", "project") else "session-" + hashlib.sha256(identity.encode()).hexdigest()
    with closing(sqlite3.connect((ROOT / "agent_memory.db").as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(":memory:")) as snapshot:
        source.backup(snapshot)
        saved = SqliteSaver(snapshot).get_tuple({"configurable": {"thread_id": thread}})
        state = saved.checkpoint["channel_values"] if saved else {}
    return state.get("summary", ""), state.get("history", "")


def redact(text):
    for name, value in os.environ.items():
        if re.search(r"(?:KEY|TOKEN|SECRET|PASSWORD)$", name, re.I) and len(value) > 7:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r'https?://[^\s<>"]+', lambda m: m.group(0).split("?")[0] + "?[QUERY REDACTED]" if "?" in m.group(0) else m.group(0), text)
    text = re.sub(r"\b(?:gsk_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,})", "[CREDENTIAL REDACTED]", text)
    return re.sub(r"(?i)\b(?:bearer\s+|(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|password)\s*[:=]\s*)[^\s,;\"]+", "[CREDENTIAL REDACTED]", text)


def response_shape(reply):
    from agent.runtime.summaries import validate_summary
    calls = reply.get("tool_calls") or []
    row = {"tool_call_count": len(calls), "registered_function": len(calls) == 1 and calls[0].get("function", {}).get("name") == "submit_conversation_summary"}
    name = calls[0].get("function", {}).get("name", "") if len(calls) == 1 else ""
    forms = {"submit_conversation_summary": "exact", "functions.submit_conversation_summary": "functions_namespace", "function.submit_conversation_summary": "function_namespace"}
    row["function_name_form"] = forms.get(name, "other" if name else "none")
    row["name_length"] = len(name) if isinstance(name, str) else None
    raw = calls[0].get("function", {}).get("arguments", "") if len(calls) == 1 else reply.get("content", "")
    try:
        row["encoded_characters"] = len(validate_summary(raw))
        row["schema_valid"] = True
    except (ValueError, TypeError):
        row["schema_valid"] = False
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            row["extra_key_count"] = len(set(value) - {"facts", "decisions", "open_questions"})
            row["fields"] = {}
            for key in ("facts", "decisions", "open_questions"):
                items = value.get(key)
                row["fields"][key] = {"type": type(items).__name__}
                if isinstance(items, list):
                    lengths = [len(x) for x in items if isinstance(x, str)]
                    row["fields"][key].update(count=len(items), nonstring=sum(not isinstance(x, str) for x in items), blanks=sum(isinstance(x, str) and not x.strip() for x in items), min_chars=min(lengths, default=0), max_chars=max(lengths, default=0))
    except (ValueError, TypeError):
        pass
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("synthetic", "saved-default"), default="synthetic")
    parser.add_argument("--force-summary-function", action="store_true")
    parser.add_argument("--one-response", action="store_true")
    parser.add_argument("--review", action="store_true", help="Print only the redacted generated summary for local human review")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from agent.runtime import summary_model
    from agent.runtime.summaries import compact_context
    from agent.providers.errors import ProviderError
    from agent.providers.selection import current_provider
    from agent.providers import tools
    if args.source == "saved-default":
        prior, history = map(redact, selected_history())
    else:
        prior = ""
        history = "".join("\nUser: Fixture note " + str(i) + " " + "neutral " * 100 + "\nAssistant: Noted." for i in range(10))
    report = {"source": args.source, "provider": current_provider(tools.LLM_PROVIDER), "forced_function_experiment": args.force_summary_function, "checkpoint_written": False, "history_chars": len(history), "response_shapes": []}
    original = summary_model.call_tool_messages
    def observed(*positional, **options):
        if args.one_response and report["response_shapes"]:
            raise RuntimeError("One-response diagnostic budget reached")
        if args.force_summary_function and current_provider(tools.LLM_PROVIDER) == "groq":
            options["forced_function"] = "submit_conversation_summary"
        reply = original(*positional, **options)
        shape = response_shape(reply)
        shape["forced_function_requested"] = options.get("forced_function") == "submit_conversation_summary"
        report["response_shapes"].append(shape)
        return reply
    start = time.monotonic()
    try:
        with patch.object(summary_model, "call_tool_messages", side_effect=observed):
            updated, recent, changed = compact_context(prior, history, summary_model.call_summary_messages, threshold=3000, keep=2000)
        report.update(status="generated" if changed else "below_threshold", recent_chars=len(recent))
        if changed:
            value = json.loads(updated)
            report["output_counts"] = {key: len(items) for key, items in value.items()}
            if args.review:
                print(json.dumps({"redacted_summary_for_local_review": value}, ensure_ascii=True, indent=2))
    except ProviderError as error:
        report.update(status="provider_blocked", category=error.category, http_status=error.status)
    except Exception as error:
        report.update(status="validation_failed", error_type=type(error).__name__)
    report["seconds"] = round(time.monotonic() - start, 2)
    suffix = "forced" if args.force_summary_function else "current"
    path = ROOT / "outputs/acceptance" / ("ws2-diagnosis-" + args.source + "-" + suffix + ".json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())

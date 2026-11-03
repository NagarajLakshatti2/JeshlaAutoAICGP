"""Hand a locally built report to the existing exact file-creation approval."""
import hashlib

from agent.actions.receipts import ActionBlocked, ActionDeclined, ActionPending


def submit_report_export(tools, prepared, receipts, approve):
    proposal = prepared["proposal"]
    if (set(proposal) != {"project_root", "action", "arguments"}
            or proposal["project_root"] != str(tools.root)
            or proposal["action"] != "create_file"):
        raise ValueError("Report export must target this exact project and create_file action.")
    args = proposal["arguments"]
    if set(args) != {"relative_path", "content"} or not isinstance(args["content"], str):
        raise ValueError("Report export requires an exact destination and Markdown content.")
    raw = args["content"].encode("utf-8")
    if (hashlib.sha256(raw).hexdigest() != prepared["sha256"]
            or len(raw) != prepared["size_bytes"]):
        raise ValueError("Prepared report content changed before approval.")
    details = ("Report snapshot: " + args["relative_path"]
               + "\nSHA256: " + prepared["sha256"]
               + "\n" + prepared["note"])
    try:
        result = receipts.run(tools.root, "create_file", dict(args), tools.create_file, approve)
    except ActionPending as error:
        return {"answer": str(error) + "\n\nAction status: awaiting approval.\n\n" + details,
                "task_status": "awaiting_input"}
    except ActionDeclined:
        return {"answer": "Report export declined or approval not received. No report file was saved.",
                "task_status": "incomplete"}
    except ActionBlocked as error:
        return {"answer": str(error), "task_status": "incomplete"}
    if (not isinstance(result, dict) or result.get("created") is not True
            or result.get("file") != args["relative_path"]
            or result.get("size_bytes") != len(raw)):
        return {"answer": "Report creation was not confirmed by the saved action result; inspect its receipt before retrying.",
                "task_status": "incomplete"}
    return {"answer": "Saved the exact reviewed historical report.\n\n" + details
            + "\n\nNo new test execution or release acceptance is claimed.",
            "task_status": "completed"}

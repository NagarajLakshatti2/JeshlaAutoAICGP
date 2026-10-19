# Browser activity logging

The Streamlit app writes outputs/logs/browser-activity.jsonl after its next render. Each line is JSON with a UTC timestamp and an allowlisted event. Events: page_render, chat_created, chat_switched, chats_refreshed, memory_viewed, download_clicked, message_started, message_finished and error.

Records contain a hashed chat reference (not the raw title/session), supported provider name, elapsed request time, downloaded turn count and safe error classification where applicable. They exclude prompts, answers, facts, credentials and raw exception/provider messages. Page rendering is distinct from user actions: clicking Show saved facts can produce a page_render followed by memory_viewed. download_clicked records the server-observed click, not proof of successful client file delivery. message_finished means the request returned, not that every task was completed.

Files rotate at 1 MiB with three backups (roughly 4 MiB plus one record). Rotation is intended for one Streamlit process; simultaneous independent servers writing the same file are not a supported rotation scenario. Logging errors are swallowed to keep the app working; missing records can indicate logging permissions/disk problems and are not evidence an action never happened.

Restart or refresh the browser app to load the change. To watch locally in PowerShell after the file exists:

```powershell
Get-Content .\outputs\logs\browser-activity.jsonl -Tail 20 -Wait
```

This enables local inspection when requested; it does not attach the PyCharm terminal or create continuous monitoring in Codex.

Files: agent/browser_activity.py and streamlit_app.py. Tests: tests/test_browser_activity.py and tests/test_streamlit_ui.py. Verified 199 guarded offline tests passing in 47.773 seconds, including log privacy, failure isolation and the UI saved-memory event. Real browser event inspection after deployment remains to be confirmed by the user.


## Live verification — 17 October 2026

Y: inspected real browser logs after user restart and clicks. page_render and memory_viewed retained the same chat reference. Subsequent chat_switched events changed from the default reference to another chat, then back to the default reference, followed by page_render each time. No error events appeared in this inspected sequence. This verifies event logging and switching; logs intentionally contain no messages and cannot independently prove summary/history accuracy.

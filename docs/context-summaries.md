# Automatic conversation summaries

After successful turns, the complete user/assistant text is archived first. When recent history exceeds 10,000 characters, older complete turns are summarized by the selected LLM. The summary is saved in the session checkpoint separately from recent history and shared long-term memory. Normal conversation prompts include the summary plus up to 4,000 recent characters.

Defaults: AI_SUMMARY_THRESHOLD_CHARS=10000 and AI_RECENT_HISTORY_CHARS=4000. This adds a model request only when the threshold is crossed. It is based on character count, not a precise token count or number of questions. Summary quality is model-dependent and can omit details; full newly archived transcripts remain in chats.sqlite3. Older history previously truncated before transcript archiving cannot be recovered by this change.

Summaries do not create approvals, change saved facts or merge sessions. If summary generation fails, the answer still succeeds, recent context is retained within the existing 16,000-character checkpoint cap, and the full archived turn stays saved. Single oversized turns are not split and may exceed model-context limits; request smaller outputs. Invalid summary settings display an unavailable-summary notice and retain bounded context.

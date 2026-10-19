# Local data backup and recovery

Status Y for a stopped-writer synthetic core-store rehearsal; actual user-data restore and optional RAG-index recovery remain unverified. Do not perform a live restore over running processes.

## Consistent backup

1. Stop the console with EXIT. Stop Streamlit with Ctrl+C and stop any other agent processes using this folder.
2. Copy the whole project into a dated backup folder outside the active project. Include agent_memory.db, any matching -wal/-shm files, the complete outputs directory, document/index stores and uploaded originals. Preserve local/Jira receipts and pending or uncertain actions. Keep external inspected repositories separately.
3. Store `.env` separately in protected storage if needed. It contains credentials; do not upload it with diagnostic logs or commit it. Provider keys can be reconfigured instead of backed up.
4. Verify the copy contains the expected files and retain the original untouched. Guard/lock files are coordination artifacts, not proof of an action outcome.

This whole-folder method avoids guessing which optional RAG store is configured. Stop all writers first: copying an actively written SQLite database or only its main file can produce an inconsistent backup.

## Recovery rehearsal

Restore into a separate folder with a newly created virtual environment. Preserve the original project. Use the same user/memory-space identifiers. Before any live request, verify chats, facts, checkpoint summaries and receipt statuses from the restored files. Do not approve restored pending actions during the rehearsal. Run offline tests and inspect SQLite integrity with all processes stopped. Validate stored completed receipts replay without execution and uncertain receipts remain blocked using synthetic fixtures.

Do not delete or relabel uncertain receipts, invent success, automatically resume commands, or merge state from different backup times. A restored checkpoint and transcript can differ because their saves are separate transactions. Review the archive and receipts before any manual continuation. Restoring local state cannot roll back external side effects or reconcile Jira outcomes.

After verification, choose which single project copy will be active. Do not run old and restored copies against the same external targets while testing. Full user-data recovery acceptance remains pending and must be recorded before marking this release gate Y.

## Verified rehearsal on 18 October 2026

A temporary project copy restored facts with user separation, an archived turn, a real LangGraph checkpoint history/summary, and completed/uncertain action receipts. SQLite integrity checks passed. Completed receipt replay for the original bound root made no handler or approval call; uncertain receipts and changed-root replay remained blocked. No user databases were copied or modified. This does not verify optional RAG indexes, every custom output store, or live-user restoration.

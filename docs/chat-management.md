# New Chat and saved conversations

Without --session, startup asks whether to create a new chat. Y/y/yes creates one; N/n/no or Enter resumes default. A new chat asks for a title (maximum 80 characters after whitespace normalization); Enter generates a timestamp title. Internal chat IDs are separate and unique, so identical titles are allowed.

Submit these commands followed by END:

- NEW CHAT or NEW SESSION: ask Y/N, then title.
- NEW CHAT Java learning: ask Y/N; if yes, use the supplied title.
- LIST CHATS: list the 30 most recently active chats in the current user/memory space.
- OPEN CHAT chat-ID: resume an existing chat by its listed ID.
- SESSION default: return to the old default conversation.

On NEW CHAT confirmation, N/no returns to default, as requested. Startup with --session learning skips the Y/N question and resumes that named session.

Full user/assistant text from successful new turns is archived in outputs/memory/chats.sqlite3. Old checkpoint history is preserved but is not backfilled into this archive. The model still receives a bounded recent context; archiving does not automatically add all old messages to the prompt. Automatic summaries are not yet implemented. Shared long-term facts remain in long_term_memory.sqlite3. Jira plans retain their existing project scope.

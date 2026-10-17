# Console and browser chat

Console: `python -m agent.langgraph.langgraph_agent`

Browser: `python -m streamlit run streamlit_app.py --server.address 127.0.0.1`

Run each in a separate terminal. The browser app uses the same .env provider, configured user/memory namespace, checkpoint database, long-term facts and chat catalog. Select existing chats or create new ones with titles up to 80 characters. Enter sends; Shift+Enter inserts a newline. Download saves archived successful turns as JSON. Refresh chats updates the sidebar after console activity.

Concurrent turns in the same chat are blocked by an exclusive chat lock. Use different chats when running both interfaces. If a process is killed, a stale lock can remain in outputs/chat_locks; check the recorded process before removing one. This local app has no authentication and must stay bound to localhost.

Browser tools can read source, search documents/web, use memory commands and existing guarded Jira workflows. Local file edits and command execution retain the console approval interface; browser proposals are declined instead of blocking on a hidden terminal prompt. No approval is inferred from a summary or previous chat.

Old history that predates the chat archive remains available to the model via checkpoints but is not reconstructed as visible browser messages. Both interfaces archive new successful turns and share automatic-summary behavior.

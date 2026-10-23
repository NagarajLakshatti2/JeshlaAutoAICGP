# Console and browser chat

Console: `python -m agent.langgraph.langgraph_agent`

Browser: `python -m streamlit run streamlit_app.py --server.address 127.0.0.1`

Run each in a separate terminal. The browser app uses the same .env provider, configured user/memory namespace, checkpoint database, long-term facts and chat catalog. Select existing chats or create new ones with titles up to 80 characters. Enter sends; Shift+Enter inserts a newline. Download saves archived successful turns as JSON. Refresh chats updates the sidebar after console activity.

Concurrent turns in the same chat are blocked by an exclusive chat lock. Use different chats when running both interfaces. If a process is killed, a stale lock can remain in outputs/chat_locks; check the recorded process before removing one. This local app has no authentication and must stay bound to localhost.

Browser tools can read source, search documents/web, use memory commands and existing guarded Jira workflows. Local file edits and command execution retain the console approval interface; browser proposals are declined instead of blocking on a hidden terminal prompt. No approval is inferred from a summary or previous chat.

Old history that predates the chat archive remains available to the model via checkpoints but is not reconstructed as visible browser messages. Both interfaces archive new successful turns and share automatic-summary behavior.


## CoWork preserves the active conversation - 23 October 2026

Y - Fixed a reproduced navigation bug: switching Chat/Cowork could open another saved chat when the View all picker contained duplicate titles. Streamlit serializes its selectbox choices by their formatted labels. The picker now includes a distinct session reference, extending colliding short references as needed; recent-chat buttons still display only the title. Its callback also rejects stale or unknown session values.

Five new regressions cover welcome-draft isolation, selected history and attachment retention across repeated mode changes, deliberate navigation between same-titled chats, colliding short references, and stale picker values. All 44 focused browser checks and the complete 706-test guarded offline suite pass (79.830 seconds for the full suite). CoWork remains the existing Soon placeholder. Verification used synthetic temporary chats with external network blocked and no provider requests.

Evidence: outputs/acceptance/cowork-chat-isolation-20261023/focused-result.json and focused-tests.log. The running user browser/server was not stopped. Reload the browser after the updated source is loaded; deliberately reselect the intended chat if the earlier bug already switched it.

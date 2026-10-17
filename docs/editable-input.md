# Editable terminal chat

Restart normally. END is no longer required. Enter sends, Alt+Enter (or Ctrl+J/F2) inserts a newline. Arrow keys, Home/End, Backspace/Delete edit the whole current draft. Ctrl+C clears the current draft. Ctrl+D exits only when the draft is empty; otherwise it deletes at the cursor. EXIT/QUIT still exit when sent as a message.

Multiline paste is preserved as one editable draft when the terminal supports bracketed paste. In terminals that send pasted lines as ordinary Enter keystrokes, use legacy mode or a compatible terminal. PyCharm key handling requires a live check; if Alt+Enter is intercepted by the IDE, use Ctrl+J or F2. Avoid PyCharm's output-only Run console for rich input; use its Terminal.

Startup Y/N, chat titles and exact-action approvals use one-line Enter submission. A cancelled or multiline approval is never implicitly accepted. Input does not invoke a shell and does not change Jira approval checks.

Compatibility mode: `python -m agent.langgraph.langgraph_agent --input-mode end`. Piped/noninteractive input in editor mode reads one line per message because cursor editing is unavailable. No prompt history is persisted; chat transcripts remain in the existing chat archive.

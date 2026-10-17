"""Editable terminal drafts, with explicit legacy END compatibility."""
import sys

_mode = "editor"
_session = None


def configure_input(mode):
    global _mode, _session
    if mode not in {"editor", "end"}:
        raise ValueError("Input mode must be editor or end.")
    _mode = mode
    _session = None


def make_bindings():
    from prompt_toolkit.key_binding import KeyBindings
    bindings = KeyBindings()

    @bindings.add("enter", eager=True)
    def send(event):
        event.current_buffer.validate_and_handle()

    @bindings.add("escape", "enter", eager=True)
    @bindings.add("c-j", eager=True)
    @bindings.add("f2", eager=True)
    def newline(event):
        event.current_buffer.insert_text("\n")

    @bindings.add("c-c", eager=True)
    def clear(event):
        event.current_buffer.reset()

    @bindings.add("c-d", eager=True)
    def exit_or_delete(event):
        if not event.current_buffer.text:
            event.app.exit(exception=EOFError())
        else:
            event.current_buffer.delete()

    return bindings


def create_editor(**kwargs):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import DummyHistory
    return PromptSession(
        multiline=True, key_bindings=make_bindings(), history=DummyHistory(),
        prompt_continuation=lambda width,line,wrap: "... ",
        bottom_toolbar="Enter: send | Alt+Enter / Ctrl+J / F2: newline | Ctrl+C: clear | Ctrl+D: exit empty draft",
        **kwargs,
    )


def read_message(prompt="You> "):
    global _session
    if _mode == "end":
        print("Enter your message. END on a separate line submits; EXIT quits.")
        lines=[]
        while True:
            line=input()
            if line.strip().upper() in {"EXIT","QUIT"}:
                raise EOFError()
            if line.strip().upper()=="END":
                return "\n".join(lines)
            lines.append(line)
    if not sys.stdin.isatty():
        # Piped input/IDE output consoles have no editable terminal surface.
        return input(prompt)
    if _session is None:
        _session=create_editor()
    return _session.prompt(prompt)


def read_confirmation():
    if _mode == "end":
        return read_message("Approval> ")
    return input("Approval (yes/no, Enter to submit)> ")

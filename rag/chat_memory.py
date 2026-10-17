import json
from pathlib import Path


# ============================================================
# PERSISTENT MEMORY CONFIGURATION
# ============================================================

MEMORY_FILE = Path("chat_history.json")


# ============================================================
# LOAD CHAT HISTORY
# ============================================================

def load_chat_history():

    if not MEMORY_FILE.exists():

        print("\nNo previous chat memory found.")

        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            chat_history = json.load(file)

        print(
            f"\nLoaded {len(chat_history)} "
            f"previous conversations."
        )

        return chat_history

    except json.JSONDecodeError:

        print(
            "\nChat memory file is invalid."
        )

        return []


# ============================================================
# SAVE CHAT HISTORY
# ============================================================

def save_chat_history(chat_history):

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            chat_history,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nChat memory saved: "
        f"{MEMORY_FILE}"
    )


# ============================================================
# ADD CONVERSATION
# ============================================================

def add_chat(
    chat_history,
    question,
    answer
):

    chat_history.append({
        "question": question,
        "answer": answer
    })

    save_chat_history(
        chat_history
    )
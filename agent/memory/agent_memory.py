import json
import os

from sentence_transformers import SentenceTransformer
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().with_name("agent_memory.json")

model = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------------------------------------------------
# 1. LOAD MEMORY
# ---------------------------------------------------------

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------------------------------------
# 2. SAVE MEMORY
# ---------------------------------------------------------

def save_memory(memories):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            memories,
            file,
            indent=4
        )


# ---------------------------------------------------------
# 3. WRITE MEMORY
# ---------------------------------------------------------

def write_memory(text):
    memories = load_memory()

    memories.append({
        "text": text
    })

    save_memory(memories)

    print("Memory saved.")


# ---------------------------------------------------------
# 4. SEARCH MEMORY
# ---------------------------------------------------------

def search_memory(query, top_k=3):

    memories = load_memory()

    if not memories:
        return []

    memory_texts = [
        memory["text"]
        for memory in memories
    ]

    memory_embeddings = model.encode(
        memory_texts,
        normalize_embeddings=True
    )

    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    )

    scores = model.similarity(
        query_embedding,
        memory_embeddings
    )[0]

    ranked_indexes = scores.argsort(
        descending=True
    )

    results = []

    for index in ranked_indexes[:top_k]:

        results.append({
            "text": memory_texts[index],
            "score": float(scores[index])
        })

    return results


# ---------------------------------------------------------
# 5. AGENT STATE
# ---------------------------------------------------------

def create_state(user_query):

    return {
        "user_query": user_query,
        "memory_results": [],
        "final_answer": None
    }


# ---------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("AGENT MEMORY PRACTICE")
    print("=" * 60)

    while True:

        user_input = input(
            "\nYou: "
        ).strip()

        if user_input.lower() == "exit":
            break

        state = create_state(user_input)

        # SAVE COMMAND
        if user_input.lower().startswith("remember "):

            memory_text = user_input[9:].strip()

            write_memory(memory_text)

            state["final_answer"] = (
                f"I remembered: {memory_text}"
            )

            print(
                "\nAgent:",
                state["final_answer"]
            )

            continue

        # SEARCH MEMORY
        state["memory_results"] = search_memory(
            user_input
        )

        print("\nRelevant memories:")

        if not state["memory_results"]:
            print("No memories found.")

        else:

            for memory in state["memory_results"]:

                print(
                    f"- {memory['text']} "
                    f"(score={memory['score']:.3f})"
                )

        state["final_answer"] = (
            "Memory search completed."
        )


if __name__ == "__main__":
    main()
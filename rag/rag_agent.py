# Command compatibility: use the shared agent's provider, sessions and tools.
# Historical implementation below is retained for learning/reference only.
if __name__ == "__main__":
    if __package__:
        from .entrypoints import launch_console
    else:
        from entrypoints import launch_console
    launch_console()
    raise SystemExit(0)

# ==================================================
# rag AGENT — Phase 2 of Agentic AI
# ==================================================
# DIFFERENCE FROM TOOL CALLING (Phase 1):
#
#   Tool Calling:
#     Question → llm picks ONE tool → execute → answer
#
#   rag Agent (this file):
#     Question → llm thinks → calls tool → observes result
#              → llm thinks again → calls another tool?
#              → keeps looping until it has enough info
#              → final answer
#
# PATTERN: ReAct = Reason + Act + Observe (loop)
#
# REAL EXAMPLE this handles that tool_calling.py cannot:
#   "Find employees who know Playwright and tell me
#    about each person's full career background"
#   → Step 1: search_structured_data → finds names
#   → Step 2: search_documents("Nagaraj background")
#   → Step 3: search_documents("Anita background")
#   → Step 4: combine all → final answer
#
# PLACE THIS FILE in: LLMRAG/rag/rag_agent.py
# ==================================================

import os
import json
import pickle
import requests

from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from sentence_transformers import CrossEncoder

if __package__:
    from .chat_memory import load_chat_history, add_chat
    from .csv_search import search_csv, format_csv_results
    from .paths import FAISS_DB_FOLDER, BM25_FILE, CHUNKS_FILE, PROJECT_ROOT
else:
    from chat_memory import load_chat_history, add_chat
    from csv_search import search_csv, format_csv_results
    from paths import FAISS_DB_FOLDER, BM25_FILE, CHUNKS_FILE, PROJECT_ROOT


# ==================================================
# LOAD ENVIRONMENT
# ==================================================

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")


# ==================================================
# CONFIGURATION
# ==================================================

FAISS_TOP_K   = 10
BM25_TOP_K    = 15
RERANK_TOP_K  = 3

MAX_STEPS     = 6       # max tool calls per question (safety limit)

RERANK_MODEL  = "BAAI/bge-reranker-base"

FREE_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free"
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}


# ==================================================
# LOAD MODELS AND DATABASES
# ==================================================

print("\nLoading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("\nLoading FAISS database...")
vectorstore = FAISS.load_local(
    str(FAISS_DB_FOLDER),
    embeddings,
    allow_dangerous_deserialization=True
)
print("FAISS loaded!")

print("\nLoading BM25 database...")
with open(BM25_FILE, "rb") as f:
    bm25 = pickle.load(f)

with open(CHUNKS_FILE, "rb") as f:
    chunks = pickle.load(f)
print(f"BM25 loaded! Chunks: {len(chunks)}")

print(f"\nLoading reranker: {RERANK_MODEL}")
reranker = CrossEncoder(RERANK_MODEL)
print("Reranker loaded!")

chat_history = load_chat_history()


# ==================================================
# AGENT TOOLS DEFINITION
# ==================================================

AGENT_TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search through PDF, TXT, and DOCX documents "
                "using hybrid semantic + keyword search with reranking. "
                "Use for: resumes, career experience, projects, "
                "education, certifications, skills from documents, "
                "cover letters, or any written document content. "
                "Can be called multiple times with different queries "
                "to gather more information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Specific search query. Be precise — "
                            "e.g. 'Nagaraj Wells Fargo project' "
                            "not just 'experience'."
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Why you are calling this tool now "
                            "and what you expect to find."
                        )
                    }
                },
                "required": ["query", "reason"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "search_structured_data",
            "description": (
                "Search structured employee data from CSV and XLSX files. "
                "Use for: filtering employees by skill, experience, role, "
                "project, or any column value. "
                "Examples: 'Who knows Playwright?', "
                "'Employees with 8+ years experience', "
                "'Who worked on banking projects?'. "
                "Can be called multiple times with different filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language filter question "
                            "about the structured data."
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Why you are calling this tool now "
                            "and what specific data you need."
                        )
                    }
                },
                "required": ["query", "reason"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": (
                "Call this ONLY when you have gathered enough information "
                "from the tools to give a complete, accurate answer. "
                "Do NOT call this if you still need more information. "
                "Compile everything you found into a helpful response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": (
                            "The complete, well-formatted final answer "
                            "based on all information gathered."
                        )
                    },
                    "sources_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of tools and queries used to "
                            "build this answer."
                        )
                    }
                },
                "required": ["answer", "sources_used"]
            }
        }
    }
]


# ==================================================
# TOOL EXECUTOR: BM25
# ==================================================

def bm25_search(query, top_k=BM25_TOP_K):

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    top_indexes = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    return [
        (chunks[i], float(scores[i]))
        for i in top_indexes
    ]


# ==================================================
# TOOL EXECUTOR: HYBRID SEARCH + RERANK
# ==================================================

def execute_search_documents(query):

    # FAISS
    faiss_results = vectorstore.similarity_search_with_score(
        query, k=FAISS_TOP_K
    )

    # BM25
    bm25_results = bm25_search(query, top_k=BM25_TOP_K)

    # Combine + deduplicate
    seen = {}
    for doc, score in faiss_results:
        key = (
            doc.metadata.get("source", ""),
            doc.metadata.get("page", ""),
            doc.page_content
        )
        if key not in seen:
            seen[key] = (doc, score, "FAISS")

    for doc, score in bm25_results:
        key = (
            doc.metadata.get("source", ""),
            doc.metadata.get("page", ""),
            doc.page_content
        )
        if key not in seen:
            seen[key] = (doc, score, "BM25")

    unique_results = list(seen.values())

    # Rerank
    pairs = [
        (query, doc.page_content)
        for doc, _, _ in unique_results
    ]
    rerank_scores = reranker.predict(pairs)

    reranked = sorted(
        zip(unique_results, rerank_scores),
        key=lambda x: x[1],
        reverse=True
    )

    top = reranked[:RERANK_TOP_K]

    # Format for llm
    parts = []
    for i, ((doc, orig, search_type), rerank_score) in enumerate(
        top, start=1
    ):
        parts.append(
            f"\nSOURCE {i}\n"
            f"File: {doc.metadata.get('source', 'Unknown')}\n"
            f"Page: {doc.metadata.get('page', 'Unknown')}\n"
            f"Retrieved By: {search_type}\n"
            f"Reranker Score: {rerank_score:.4f}\n"
            f"Content:\n{doc.page_content}"
        )

    return "\n".join(parts)


# ==================================================
# TOOL EXECUTOR: STRUCTURED DATA
# ==================================================

def execute_search_structured_data(query):

    results = search_csv(query)
    formatted = format_csv_results(results)
    return formatted


# ==================================================
# TOOL ROUTER
# ==================================================

def execute_tool(tool_name, tool_args):

    if tool_name == "search_documents":
        result = execute_search_documents(tool_args["query"])
        return result

    elif tool_name == "search_structured_data":
        result = execute_search_structured_data(tool_args["query"])
        return result

    elif tool_name == "final_answer":
        return None  # Signal: agent is done

    else:
        return f"Unknown tool: {tool_name}"


# ==================================================
# CALL OPENROUTER
# ==================================================

def call_openrouter(messages, tools=None):

    data = {
        "models": FREE_MODELS,
        "messages": messages,
    }

    if tools:
        data["tools"] = tools
        data["tool_choice"] = "required"  # Agent MUST pick a tool

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=data,
        timeout=120
    )

    response.raise_for_status()
    return response.json()


# ==================================================
# MAIN: REACT AGENT LOOP
# ==================================================

def run_agent(user_question):

    print("\n")
    print("=" * 70)
    print("rag AGENT — ReAct Loop")
    print("=" * 70)
    print(f"Question: {user_question}")

    # ------------------------------------------------
    # System prompt — agent instructions
    # ------------------------------------------------

    system_prompt = """You are an intelligent rag Agent that answers questions
by searching documents and structured data step by step.

## YOUR TOOLS:
- search_documents: Search PDF/TXT/DOCX documents (resume, career info)
- search_structured_data: Search CSV/XLSX employee records
- final_answer: Give the final answer when you have enough information

## YOUR PROCESS (ReAct loop):
1. REASON: Think about what information you need
2. ACT: Call the most relevant tool
3. OBSERVE: Read the result carefully
4. REPEAT: Do you have enough? If not, call another tool
5. FINAL: When confident, call final_answer

## RULES:
- Always call a tool — never respond with plain text
- You can call search_documents multiple times with DIFFERENT queries
- You can call search_structured_data multiple times with DIFFERENT filters
- Only call final_answer when you truly have enough to answer completely
- For multi-part questions, gather ALL parts before final_answer
- Be specific in your queries — narrow queries find better results"""

    # ------------------------------------------------
    # Build initial messages
    # ------------------------------------------------

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add recent chat history
    if chat_history:
        for chat in chat_history[-2:]:
            messages.append({
                "role": "user",
                "content": chat.get("question", "")
            })
            messages.append({
                "role": "assistant",
                "content": chat.get("answer", "")
            })

    messages.append({
        "role": "user",
        "content": user_question
    })

    # ------------------------------------------------
    # ReAct Loop — agent keeps going until final_answer
    # ------------------------------------------------

    step = 0
    final_answer = None
    sources_used = []
    used_model = "Unknown"

    while step < MAX_STEPS:

        step += 1

        print("\n")
        print(f"{'─' * 70}")
        print(f"STEP {step} — AGENT THINKING")
        print(f"{'─' * 70}")

        # Ask agent what to do next
        result = call_openrouter(
            messages=messages,
            tools=AGENT_TOOLS
        )

        used_model = result.get("model", "Unknown")
        response_message = result["choices"][0]["message"]
        tool_calls = response_message.get("tool_calls", [])

        if not tool_calls:
            # Agent responded with text instead of tool — shouldn't happen
            print("[AGENT] No tool called — forcing stop")
            final_answer = response_message.get("content", "No answer generated")
            break

        # Process the tool the agent chose
        tool_call    = tool_calls[0]
        tool_name    = tool_call["function"]["name"]
        tool_args    = json.loads(tool_call["function"]["arguments"])
        tool_call_id = tool_call.get("id", f"call_{step}")

        print(f"Tool Chosen : {tool_name}")
        print(f"Query/Reason: {json.dumps(tool_args, indent=2)}")

        # ── FINAL ANSWER: agent is done ──
        if tool_name == "final_answer":

            final_answer  = tool_args.get("answer", "")
            sources_used  = tool_args.get("sources_used", [])

            print(f"\n[AGENT] Decided it has enough info → final_answer")
            break

        # ── SEARCH TOOL: execute and feed result back ──
        print(f"\n[EXECUTING] {tool_name}...")

        tool_result = execute_tool(tool_name, tool_args)

        preview = tool_result[:300] if tool_result else "(empty)"
        print(f"\n[RESULT PREVIEW]\n{preview}...\n")

        # Append assistant's tool call to conversation
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(tool_args)
                    }
                }
            ]
        })

        # Append tool result so agent can read it
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result or "No results found."
        })

    # ------------------------------------------------
    # Safety: hit MAX_STEPS without final_answer
    # ------------------------------------------------

    if not final_answer:

        print(f"\n[AGENT] Hit MAX_STEPS ({MAX_STEPS}) — generating answer from gathered info")

        messages.append({
            "role": "user",
            "content": (
                "You have reached the maximum number of steps. "
                "Please give the best answer you can from what you have gathered."
            )
        })

        fallback = call_openrouter(messages=messages, tools=None)
        final_answer = fallback["choices"][0]["message"].get("content", "")

    # ------------------------------------------------
    # Print final answer
    # ------------------------------------------------

    print("\n")
    print("=" * 70)
    print(f"FINAL ANSWER  (after {step} steps)")
    print("=" * 70)
    print(final_answer)

    if sources_used:
        print("\nSources used by agent:")
        for s in sources_used:
            print(f"  • {s}")

    print(f"\nModel: {used_model}")
    print(f"Steps taken: {step}")

    # Save to chat memory
    add_chat(chat_history, user_question, final_answer)
    print(f"Chat memory: {len(chat_history)} conversations stored")

    return final_answer


# ==================================================
# MAIN
# ==================================================

def main():

    print("\n")
    print("=" * 70)
    print("rag AGENT — Phase 2 Agentic AI")
    print("=" * 70)
    print("Type 'exit' to stop.\n")

    while True:

        question = input("\nAsk your question: ").strip()

        if question.lower() == "exit":
            print("\nExiting...")
            break

        if not question:
            print("Please enter a question.")
            continue

        run_agent(question)


if __name__ == "__main__":

    # ── Test questions — notice Q1 is multi-step ──
    test_questions = [

        # Multi-step: needs structured data THEN documents
        (
            "Find all employees who know Playwright, "
            "then tell me about each person's detailed "
            "career background from the resume"
        ),

        # Single-step document search
        "What certifications does Nagaraj have?",

        # Single-step structured search
        "Who worked on banking projects?",
    ]

    print("\n")
    print("=" * 70)
    print("RUNNING AGENT TEST QUESTIONS")
    print("=" * 70)

    for question in test_questions:
        print(f"\n{'*' * 70}")
        print(f"TEST: {question}")
        print(f"{'*' * 70}")
        run_agent(question)
        print("\n")


if __name__ == "__main__":
    main()
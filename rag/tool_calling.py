# ==================================================
# TOOL CALLING — Phase 1 of Agentic AI
# ==================================================
# This replaces your manual if/else routing in query.py
# The llm decides which tool to call based on the question.
#
# HOW IT WORKS:
#   1. You define tools as JSON schemas
#   2. Send question + tool definitions to OpenRouter
#   3. llm returns: tool_name + arguments
#   4. You execute the tool
#   5. Feed result back to llm
#   6. llm gives the final answer
#
# PLACE THIS FILE in: rag/tool_calling.py
# ==================================================

import os
import json
import pickle
import requests

from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from sentence_transformers import CrossEncoder

from chat_memory import load_chat_history, add_chat
from csv_search import search_csv, format_csv_results


# ==================================================
# LOAD ENVIRONMENT
# ==================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in .env file")


# ==================================================
# CONFIGURATION
# ==================================================

FAISS_TOP_K = 10
BM25_TOP_K = 15
RERANK_TOP_K = 3

RERANK_MODEL = "BAAI/bge-reranker-base"

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
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

print("\nLoading FAISS database...")
vectorstore = FAISS.load_local(
    "faiss_db",
    embeddings,
    allow_dangerous_deserialization=True
)
print("FAISS loaded!")

print("\nLoading BM25 database...")
with open("bm25.pkl", "rb") as f:
    bm25 = pickle.load(f)

with open("chunks.pkl", "rb") as f:
    chunks = pickle.load(f)
print(f"BM25 loaded! Chunks: {len(chunks)}")

print(f"\nLoading reranker: {RERANK_MODEL}")
reranker = CrossEncoder(RERANK_MODEL)
print("Reranker loaded!")

chat_history = load_chat_history()


# ==================================================
# TOOL DEFINITIONS
# (These are what you send to the llm)
# ==================================================

TOOLS = [

    # ------------------------------------------------
    # Tool 1: Search Documents (PDF, TXT, DOCX)
    # ------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search through PDF, TXT, and DOCX documents "
                "using hybrid semantic + keyword search. "
                "Use this for questions about resumes, cover letters, "
                "career experience, projects, skills, education, "
                "Java course topics, or any document content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query to find relevant "
                            "document chunks."
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },

    # ------------------------------------------------
    # Tool 2: Search Structured Data (CSV, XLSX)
    # ------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "search_structured_data",
            "description": (
                "Search structured employee or roadmap data "
                "from CSV and XLSX files. "
                "Use this for questions about employees, "
                "who has a skill, experience years, roles, "
                "projects, or filtering/counting records. "
                "Examples: 'Who knows Playwright?', "
                "'Who has more than 8 years experience?', "
                "'Which employees worked on banking projects?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The natural language question "
                            "about structured data."
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },

    # ------------------------------------------------
    # Tool 3: General Knowledge (No Tool Needed)
    # ------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "answer_directly",
            "description": (
                "Answer the question directly from your own knowledge "
                "without searching any documents. "
                "Use this ONLY when the question is a general knowledge "
                "question that does NOT require document search. "
                "Examples: 'What is Python?', "
                "'Explain what rag means', "
                "'What is a transformer model?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": (
                            "Why no document search is needed "
                            "for this question."
                        )
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


# ==================================================
# TOOL EXECUTOR: BM25 SEARCH
# ==================================================

def bm25_search(query, top_k=BM25_TOP_K):

    tokenized_query = query.lower().split()

    scores = bm25.get_scores(tokenized_query)

    top_indexes = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = []

    for index in top_indexes:
        results.append(
            (chunks[index], float(scores[index]))
        )

    return results


# ==================================================
# TOOL EXECUTOR: HYBRID SEARCH + RERANK
# ==================================================

def execute_search_documents(query):

    print(f"\n[TOOL] search_documents called")
    print(f"Query: {query}")

    # FAISS search
    faiss_results = vectorstore.similarity_search_with_score(
        query,
        k=FAISS_TOP_K
    )

    # BM25 search
    bm25_results = bm25_search(query, top_k=BM25_TOP_K)

    # Combine and deduplicate
    combined = []

    for doc, score in faiss_results:
        combined.append((doc, float(score), "FAISS"))

    for doc, score in bm25_results:
        combined.append((doc, float(score), "BM25"))

    seen = {}
    for doc, score, search_type in combined:
        key = (
            doc.metadata.get("source", ""),
            doc.metadata.get("page", ""),
            doc.page_content
        )
        if key not in seen:
            seen[key] = (doc, score, search_type)

    unique_results = list(seen.values())

    # Rerank
    pairs = [
        (query, doc.page_content)
        for doc, score, search_type in unique_results
    ]

    rerank_scores = reranker.predict(pairs)

    reranked = []
    for (doc, orig_score, search_type), rerank_score in zip(
        unique_results, rerank_scores
    ):
        reranked.append(
            (doc, orig_score, float(rerank_score), search_type)
        )

    reranked.sort(key=lambda x: x[2], reverse=True)

    top_results = reranked[:RERANK_TOP_K]

    # Format result for llm
    context_parts = []

    for i, (doc, orig_score, rerank_score, search_type) in enumerate(
        top_results, start=1
    ):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "Unknown")

        context_parts.append(
            f"\nSOURCE {i}\n"
            f"File: {source}\n"
            f"Page: {page}\n"
            f"Retrieved By: {search_type}\n"
            f"Reranker Score: {rerank_score:.4f}\n"
            f"Content:\n{doc.page_content}"
        )

    result = "\n".join(context_parts)

    print(f"[TOOL] search_documents → {len(top_results)} chunks returned")

    return result


# ==================================================
# TOOL EXECUTOR: STRUCTURED DATA SEARCH
# ==================================================

def execute_search_structured_data(query):

    print(f"\n[TOOL] search_structured_data called")
    print(f"Query: {query}")

    results = search_csv(query)

    formatted = format_csv_results(results)

    print(
        f"[TOOL] search_structured_data → "
        f"{len(results)} records found"
    )

    return formatted


# ==================================================
# TOOL ROUTER
# (Executes whichever tool the llm chose)
# ==================================================

def execute_tool(tool_name, tool_args):

    print(f"\n{'='*60}")
    print(f"EXECUTING TOOL: {tool_name}")
    print(f"ARGUMENTS: {json.dumps(tool_args, indent=2)}")
    print(f"{'='*60}")

    if tool_name == "search_documents":
        return execute_search_documents(
            tool_args["query"]
        )

    elif tool_name == "search_structured_data":
        return execute_search_structured_data(
            tool_args["query"]
        )

    elif tool_name == "answer_directly":
        return None  # llm will answer from its own knowledge

    else:
        return f"Unknown tool: {tool_name}"


# ==================================================
# CALL OPENROUTER WITH TOOLS
# ==================================================

def call_openrouter(messages, tools=None, tool_choice="auto"):

    data = {
        "models": FREE_MODELS,
        "messages": messages,
    }

    if tools:
        data["tools"] = tools
        data["tool_choice"] = tool_choice

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=data,
        timeout=120
    )

    response.raise_for_status()

    return response.json()


# ==================================================
# MAIN: RUN QUERY WITH TOOL CALLING
# ==================================================

def run_query_with_tools(user_question):

    print("\n")
    print("=" * 70)
    print("USER QUESTION")
    print("=" * 70)
    print(user_question)


    # ------------------------------------------------
    # Build conversation context for the llm
    # ------------------------------------------------

    system_prompt = """You are a helpful rag assistant.

You have access to tools to search documents and structured data.

ALWAYS use a tool to answer questions about:
- Resumes, career, experience, projects, skills, education
- Employee records, skills filtering, experience filtering
- Any specific document content

Only use answer_directly for pure general knowledge questions
that have nothing to do with the available documents.

When you use a tool, the result will be shown to you.
Then give a clear, helpful final answer based on that result."""


    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Add recent chat history for context
    if chat_history:
        for chat in chat_history[-3:]:
            messages.append({
                "role": "user",
                "content": chat.get("question", "")
            })
            messages.append({
                "role": "assistant",
                "content": chat.get("answer", "")
            })

    # Add current question
    messages.append({
        "role": "user",
        "content": user_question
    })


    # ------------------------------------------------
    # Step 1: Ask llm which tool to use
    # ------------------------------------------------

    print("\n")
    print("=" * 70)
    print("STEP 1 — llm DECIDES WHICH TOOL TO CALL")
    print("=" * 70)

    result = call_openrouter(
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    response_message = result["choices"][0]["message"]
    used_model = result.get("model", "Unknown")

    print(f"Model: {used_model}")


    # ------------------------------------------------
    # Step 2: Check if llm wants to call a tool
    # ------------------------------------------------

    tool_calls = response_message.get("tool_calls", [])

    if not tool_calls:

        # llm answered directly (no tool needed)
        print("\n[llm] Answered directly — no tool called")
        final_answer = response_message.get("content", "")

    else:

        # llm chose a tool
        tool_call = tool_calls[0]

        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(
            tool_call["function"]["arguments"]
        )

        print(f"\n[llm] Tool chosen: {tool_name}")
        print(f"[llm] Arguments: {json.dumps(tool_args, indent=2)}")


        # ------------------------------------------------
        # Step 3: Execute the chosen tool
        # ------------------------------------------------

        print("\n")
        print("=" * 70)
        print("STEP 2 — EXECUTING TOOL")
        print("=" * 70)

        tool_result = execute_tool(tool_name, tool_args)


        # ------------------------------------------------
        # Step 4: Feed tool result back to llm
        # ------------------------------------------------

        print("\n")
        print("=" * 70)
        print("STEP 3 — llm GENERATES FINAL ANSWER")
        print("=" * 70)

        if tool_result is None:

            # answer_directly was chosen — ask llm to answer
            messages.append({
                "role": "assistant",
                "content": (
                    f"I'll answer this from general knowledge. "
                    f"Reason: {tool_args.get('reason', '')}"
                )
            })

            messages.append({
                "role": "user",
                "content": "Please provide your answer now."
            })

        else:

            # Append assistant's tool call
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.get("id", "call_1"),
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args)
                        }
                    }
                ]
            })

            # Append tool result
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", "call_1"),
                "content": tool_result
            })

        # Final llm call to generate the answer
        final_result = call_openrouter(
            messages=messages,
            tools=None  # No tools in final answer step
        )

        final_answer = (
            final_result["choices"][0]["message"]["content"]
        )

        used_model = final_result.get("model", used_model)


    # ------------------------------------------------
    # Step 5: Print and save the answer
    # ------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(final_answer)

    print(f"\nModel used: {used_model}")

    # Save to chat memory
    add_chat(chat_history, user_question, final_answer)

    print(f"\nChat memory: {len(chat_history)} conversations stored")

    return final_answer


# ==================================================
# MAIN LOOP
# ==================================================

def main():

    print("\n")
    print("=" * 70)
    print("TOOL CALLING rag — PHASE 1 AGENTIC AI")
    print("=" * 70)
    print("\nType 'exit' to stop.")

    while True:

        question = input("\nAsk your question: ").strip()

        if question.lower() == "exit":
            print("\nExiting...")
            break

        if not question:
            print("Please enter a question.")
            continue

        run_query_with_tools(question)


if __name__ == "__main__":

    # Quick test without interactive loop
    test_questions = [
        "Who knows Playwright?",
        "Who has more than 8 years of experience?",
        "What is Nagaraj's work experience?",
        "What is rag in AI?",
    ]

    print("\n")
    print("=" * 70)
    print("RUNNING TEST QUESTIONS")
    print("=" * 70)

    for question in test_questions:
        print(f"\n{'*' * 70}")
        print(f"TEST: {question}")
        print(f"{'*' * 70}")
        run_query_with_tools(question)
        print("\n")
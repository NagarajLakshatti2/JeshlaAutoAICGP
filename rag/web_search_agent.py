# ==================================================
# WEB SEARCH + rag AGENT — Phase 3 of Agentic AI
# ==================================================
# ADDS on top of rag Agent (Phase 2):
#
#   Phase 2 sources:          Phase 3 sources:
#   ─────────────────         ──────────────────────────────
#   search_documents    →     search_documents  (same)
#   search_structured   →     search_structured (same)
#                       +     web_search        (NEW — live internet)
#
# REAL EXAMPLES this handles that Phase 2 cannot:
#
#   "What is the latest Playwright version and who in
#    our team knows it?"
#   → web_search("latest Playwright release 2026")
#   → search_structured_data("who knows Playwright")
#   → combines: latest version + your team members
#
#   "Is Selenium still popular and does our team use it?"
#   → web_search("Selenium popularity trends 2026")
#   → search_documents("Nagaraj Selenium experience")
#   → combines: market context + your team's actual use
#
# PLACE THIS FILE in: LLMRAG/rag/web_search_agent.py
# ==================================================

import os
import json
import pickle
import time

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

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in .env")

# Separate key for web search (using SerpAPI — free tier)
# Sign up free at: https://serpapi.com  (100 searches/month free)
# Then add to .env:  SERPAPI_KEY=your_key_here
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


# ==================================================
# CONFIGURATION
# ==================================================

FAISS_TOP_K   = 10
BM25_TOP_K    = 15
RERANK_TOP_K  = 3
MAX_STEPS     = 8       # more steps — web search adds depth

RERANK_MODEL  = "BAAI/bge-reranker-base"

OPENROUTER_FREE_MODEL = "openrouter/free"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SERPAPI_URL    = "https://serpapi.com/search"
DDG_URL        = "https://api.duckduckgo.com/"  # fallback, no key needed

openrouter_headers = {
    "Authorization": f"Bearer {OPENROUTER_KEY}",
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

# Print web search status
if SERPAPI_KEY:
    print("\nWeb Search: SerpAPI (Google) ✅")
else:
    print("\nWeb Search: DuckDuckGo fallback ✅ (no key needed)")
    print("  Tip: Add SERPAPI_KEY to .env for better results")


# ==================================================
# AGENT TOOLS DEFINITION
# ==================================================

AGENT_TOOLS = [

    # ── Tool 1: Document Search ──────────────────
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search private PDF, TXT, and DOCX documents "
                "using hybrid semantic + keyword search with reranking. "
                "Use for: resumes, career experience, projects, "
                "certifications, skills, cover letters, or any "
                "private document content. "
                "Can be called multiple times with different queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Specific search query — be precise. "
                            "E.g. 'Nagaraj Wells Fargo automation' "
                            "not just 'experience'."
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you are calling this now."
                    }
                },
                "required": ["query", "reason"]
            }
        }
    },

    # ── Tool 2: Structured Data Search ──────────
    {
        "type": "function",
        "function": {
            "name": "search_structured_data",
            "description": (
                "Search structured employee data from CSV and XLSX. "
                "Use for: filtering by skill, experience, role, or project. "
                "Examples: 'Who knows Playwright?', "
                "'Employees with 8+ years experience', "
                "'Who worked on banking projects?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language filter question."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why you are calling this now."
                    }
                },
                "required": ["query", "reason"]
            }
        }
    },

    # ── Tool 3: Web Search (NEW) ─────────────────
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the live internet for current information. "
                "Use for: latest versions, recent news, technology trends, "
                "market information, documentation, salary data, "
                "job market trends, or anything that needs up-to-date info. "
                "DO NOT use for private employee/company data — "
                "use search_documents or search_structured_data for that. "
                "Examples: 'latest Playwright version 2026', "
                "'Selenium vs Playwright popularity 2026', "
                "'average SDET salary India 2026'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Web search query — concise and specific. "
                            "Include the year for recency."
                        )
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Why you need live web data "
                            "instead of documents."
                        )
                    }
                },
                "required": ["query", "reason"]
            }
        }
    },

    # ── Tool 4: Final Answer ─────────────────────
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": (
                "Call ONLY when you have gathered enough information "
                "from all necessary tools to give a complete answer. "
                "Clearly separate private data (from documents/CSV) "
                "from public web information in your answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": (
                            "Complete, well-formatted final answer. "
                            "Label what came from documents vs web."
                        )
                    },
                    "sources_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "All tools and queries used."
                    }
                },
                "required": ["answer", "sources_used"]
            }
        }
    }
]


# ==================================================
# WEB SEARCH EXECUTOR
# ==================================================

def execute_web_search(query):
    """
    Tries SerpAPI first (Google results, best quality).
    Falls back to DuckDuckGo if no SERPAPI_KEY set.
    Returns formatted string of top results.
    """

    print(f"\n[WEB] Searching: {query}")

    # ── Option A: SerpAPI (Google) ───────────────
    if SERPAPI_KEY:
        try:
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": 5,
                "hl": "en",
                "gl": "in"   # India locale, change if needed
            }

            response = requests.get(
                SERPAPI_URL,
                params=params,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("organic_results", [])

            if not results:
                return "No web results found."

            parts = [f"WEB SEARCH RESULTS for: {query}\n"]

            for i, r in enumerate(results[:5], start=1):
                title   = r.get("title", "No title")
                snippet = r.get("snippet", "No snippet")
                link    = r.get("link", "")

                parts.append(
                    f"\nRESULT {i}\n"
                    f"Title  : {title}\n"
                    f"Snippet: {snippet}\n"
                    f"URL    : {link}"
                )

            print(f"[WEB] SerpAPI → {len(results[:5])} results")
            return "\n".join(parts)

        except Exception as e:
            print(f"[WEB] SerpAPI failed: {e} — trying DuckDuckGo")

    # ── Option B: DuckDuckGo (no key needed) ─────
    try:
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }

        response = requests.get(
            DDG_URL,
            params=params,
            timeout=15
        )
        response.raise_for_status()

        data = response.json()

        parts = [f"WEB SEARCH RESULTS for: {query}\n"]

        # Abstract (main answer)
        if data.get("Abstract"):
            parts.append(
                f"\nSUMMARY\n"
                f"{data['Abstract']}\n"
                f"Source: {data.get('AbstractURL', '')}"
            )

        # Related topics
        topics = data.get("RelatedTopics", [])
        count = 0

        for topic in topics[:6]:
            text = topic.get("Text", "")
            url  = topic.get("FirstURL", "")

            if text:
                count += 1
                parts.append(
                    f"\nRESULT {count}\n"
                    f"Info: {text}\n"
                    f"URL : {url}"
                )

        if len(parts) == 1:
            # DDG returned nothing useful — use OpenRouter's knowledge
            return (
                f"Web search returned no results for: {query}\n"
                f"Answer using your training knowledge instead."
            )

        print(f"[WEB] DuckDuckGo → {count} results")
        return "\n".join(parts)

    except Exception as e:
        print(f"[WEB] DuckDuckGo also failed: {e}")
        return (
            f"Web search unavailable. "
            f"Answer '{query}' from your training knowledge."
        )


# ==================================================
# DOCUMENT SEARCH EXECUTOR
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
# STRUCTURED DATA EXECUTOR
# ==================================================

def execute_search_structured_data(query):
    results = search_csv(query)
    return format_csv_results(results)


# ==================================================
# TOOL ROUTER
# ==================================================

def execute_tool(tool_name, tool_args):

    if tool_name == "search_documents":
        return execute_search_documents(tool_args["query"])

    elif tool_name == "search_structured_data":
        return execute_search_structured_data(tool_args["query"])

    elif tool_name == "web_search":
        return execute_web_search(tool_args["query"])

    elif tool_name == "final_answer":
        return None  # Agent is done

    else:
        return f"Unknown tool: {tool_name}"


# ==================================================
# CALL OPENROUTER
# ==================================================

def call_openrouter(messages, tools=None):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_FREE_MODEL,
        "messages": messages
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:

        print(
            f"\n[OPENROUTER] Router: "
            f"{OPENROUTER_FREE_MODEL}"
        )

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        # ==============================
        # SUCCESS
        # ==============================

        if response.status_code == 200:

            result = response.json()

            actual_model = result.get(
                "model",
                "Unknown"
            )

            print(
                f"[OPENROUTER] ✅ Actual model: "
                f"{actual_model}"
            )

            return result

        # ==============================
        # RATE LIMIT
        # ==============================

        if response.status_code == 429:

            print(
                "\n[OPENROUTER] ⚠️ "
                "Free router is rate limited."
            )

            print(response.text)

            return None

        # ==============================
        # BAD REQUEST
        # ==============================

        if response.status_code == 400:

            print(
                "\n❌ OPENROUTER BAD REQUEST"
            )

            print(response.text)

            return None

        # ==============================
        # OTHER ERROR
        # ==============================

        print(
            f"\n❌ OpenRouter HTTP Error: "
            f"{response.status_code}"
        )

        print(response.text)

        return None

    except requests.exceptions.RequestException as error:

        print(
            f"\n❌ OpenRouter connection error: "
            f"{error}"
        )

        return None

# ==================================================
# MAIN: WEB SEARCH + rag AGENT LOOP
# ==================================================

def run_web_agent(user_question):

    print("\n")
    print("=" * 70)
    print("WEB SEARCH + rag AGENT")
    print("=" * 70)
    print(f"Question: {user_question}")

    system_prompt = """You are an intelligent Web Search + rag Agent.

## YOUR 3 DATA SOURCES:
1. search_documents     — Private PDF/TXT/DOCX (resumes, cover letters)
2. search_structured_data — Private CSV/XLSX (employee records)
3. web_search           — Live internet (versions, trends, news, docs)

## HOW TO CHOOSE:
- Employee names, skills, experience, projects → search_structured_data
- Resume content, career details, cover letters → search_documents
- Latest tool versions, trends, salaries, news → web_search
- Comparison of private data WITH public data → use BOTH

## YOUR PROCESS (ReAct loop):
1. REASON: What sources do I need?
2. ACT: Call the most relevant tool first
3. OBSERVE: Read the result
4. REPEAT: Do I need more from another source?
5. FINAL: Call final_answer when complete

## RULES:
- Always call a tool — never respond with plain text
- For hybrid questions (private + public), use BOTH sources
- Clearly label in your final answer: [From Documents] vs [From Web]
- Only call final_answer when you have enough from ALL needed sources"""

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Recent chat history
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

    # ── ReAct loop ───────────────────────────────
    step         = 0
    final_answer = None
    sources_used = []
    used_model   = "Unknown"

    while step < MAX_STEPS:

        step += 1

        print("\n")
        print(f"{'─' * 70}")
        print(f"STEP {step} — AGENT THINKING")
        print(f"{'─' * 70}")

        result = call_openrouter(
            messages=messages,
            tools=AGENT_TOOLS
        )

        # -------------------------------------------------
        # IMPORTANT: Check if OpenRouter failed
        # -------------------------------------------------
        if result is None:
            print("\n" + "=" * 70)
            print("AGENT STOPPED")
            print("=" * 70)

            print(
                "Reason: OpenRouter API is unavailable "
                "or rate limit was reached."
            )

            print(
                "Please wait and run the agent again later."
            )

            return

        # -------------------------------------------------
        # OpenRouter succeeded
        # -------------------------------------------------
        used_model = result.get(
            "model",
            "Unknown"
        )

        used_model       = result.get("model", "Unknown")
        response_message = result["choices"][0]["message"]
        tool_calls       = response_message.get("tool_calls", [])

        if not tool_calls:
            print("[AGENT] No tool called — stopping")
            final_answer = response_message.get(
                "content", "No answer generated."
            )
            break

        tool_call    = tool_calls[0]
        tool_name    = tool_call["function"]["name"]
        tool_args    = json.loads(tool_call["function"]["arguments"])
        tool_call_id = tool_call.get("id", f"call_{step}")

        print(f"Tool   : {tool_name}")
        print(f"Args   : {json.dumps(tool_args, indent=2)}")

        # Final answer reached
        if tool_name == "final_answer":
            final_answer = tool_args.get("answer", "")
            sources_used = tool_args.get("sources_used", [])
            print("\n[AGENT] Has enough info → final_answer")
            break

        # Execute the tool
        print(f"\n[EXECUTING] {tool_name}...")
        tool_result = execute_tool(tool_name, tool_args)

        preview = (tool_result or "(empty)")[:300]
        print(f"\n[RESULT PREVIEW]\n{preview}...\n")

        # Append tool call + result to conversation
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

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": tool_result or "No results found."
        })

    # Safety fallback
    if not final_answer:
        print(f"\n[AGENT] Hit MAX_STEPS ({MAX_STEPS}) — generating from gathered info")
        messages.append({
            "role": "user",
            "content": (
                "You've reached the step limit. "
                "Please give the best answer from what you have."
            )
        })
        fallback = call_openrouter(messages=messages, tools=None)
        final_answer = fallback["choices"][0]["message"].get("content", "")

    # ── Print final answer ────────────────────────
    print("\n")
    print("=" * 70)
    print(f"FINAL ANSWER  (after {step} steps)")
    print("=" * 70)
    print(final_answer)

    if sources_used:
        print("\nSources used:")
        for s in sources_used:
            print(f"  • {s}")

    print(f"\nModel : {used_model}")
    print(f"Steps : {step}")

    add_chat(chat_history, user_question, final_answer)
    print(f"Memory: {len(chat_history)} conversations stored")

    return final_answer


# ==================================================
# MAIN
# ==================================================

def main():

    print("\n")
    print("=" * 70)
    print("WEB SEARCH + rag AGENT — Phase 3 Agentic AI")
    print("=" * 70)
    print("Type 'exit' to stop.\n")

    while True:

        question = input("\nAsk your question: ").strip()

        if question.lower() == "exit":
            print("\nExiting...")
            break

        if not question:
            continue

        run_web_agent(question)


# if __name__ == "__main__":
#
#     # ── Test questions — all 3 sources needed ──
#     test_questions = [
#
#         # Hybrid: private data + live web
#         (
#             "What is the latest Playwright version and "
#             "who in our team knows it?"
#         ),
#
#         # Hybrid: private experience + public market trend
#         (
#             "Is Selenium still popular in 2026 and "
#             "does our team use it?"
#         ),
#
#         # Pure web: no private data needed
#         "What is the difference between Playwright and Cypress in 2026?",
#     ]
#
#     print("\n")
#     print("=" * 70)
#     print("RUNNING WEB SEARCH AGENT TESTS")
#     print("=" * 70)
#
#     for question in test_questions:
#         print(f"\n{'*' * 70}")
#         print(f"TEST: {question}")
#         print(f"{'*' * 70}")
#         run_web_agent(question)
#         print("\n")


if __name__ == "__main__":

    question = (
        "What is the latest Playwright version and "
        "who in our team knows it?"
    )

    print("\n" + "=" * 70)
    print("RUNNING WEB SEARCH AGENT TEST")
    print("=" * 70)

    run_web_agent(question)

    main()
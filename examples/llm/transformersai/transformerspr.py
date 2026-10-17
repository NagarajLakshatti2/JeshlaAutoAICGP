import os
from pathlib import Path
from unittest import result

from dotenv import load_dotenv
from rich import json
from transformers import pipeline
import anthropic
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb, ollama
# from transformers.generation.continuous_batching import requests
import requests


# env_path = Path(__file__).resolve().parents[2] / ".env"
# load_dotenv(env_path)
#
# HF_TOKEN = os.getenv("HF_TOKEN")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
#
# print("Anthropic key loaded:", bool(ANTHROPIC_API_KEY))
# print("HF token loaded:", bool(HF_TOKEN))

# MODEL = "qwen3:8b"
# MODEL = "gpt-oss:20b"
# MODEL = "devstral"

# gen = pipeline("text-generation", model="Qwen/Qwen2.5-0.5B-Instruct", token=HF_TOKEN)
# print(gen("Explain LLMs in one line:", max_new_tokens=50)[0]["generated_text"])
#
# r = ollama.chat(model="llama3.2", messages=[
#     {"role": "user", "content": "What is a token?"}
# ])
# print(r["message"]["content"])

# client = anthropic.Anthropic()  # needs ANTHROPIC_API_KEY
# msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=200,
#     messages=[{"role": "user", "content": "Explain attention simply."}])
# print(msg.content[0].text)


# # 1. Load and chunk the PDF
# text = "".join(p.extract_text() for p in PdfReader("notes.pdf").pages)
# chunks = [text[i:i+800] for i in range(0, len(text), 700)]  # 100-char overlap
#
# # 2. Embed and store
# embedder = SentenceTransformer("all-MiniLM-L6-v2")
# db = chromadb.Client().create_collection("docs")
# db.add(ids=[str(i) for i in range(len(chunks))],
#        documents=chunks,
#        embeddings=embedder.encode(chunks).tolist())

# # 3. Retrieve and generate
# def ask(q):
#     hits = db.query(query_embeddings=embedder.encode([q]).tolist(),
#                     n_results=3)["documents"][0]
#     prompt = ("Answer using only this context:\n" + "\n---\n".join(hits)
#               + f"\n\nQuestion: {q}")
#
#     r = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
#     return r["message"]["content"]
#
# print(ask("What is the main topic of this document?"))

# response = ollama.chat(
#     model="qwen3:8b",
#     messages=[
#         {
#             "role": "user",
#             "content": "Explain Transformer attention in simple terms."
#         }
#     ]
# )
#
# print(response["message"]["content"])
#
# response1 = ollama.chat(
#     model="gpt-oss:20b",
#     messages=[
#         {
#             "role": "user",
#             "content": "Explain how an AI agent can use tools."
#         }
#     ]
# )
#
# print(response1["message"]["content"])
#
# response2 = ollama.chat(
#     model="devstral",
#     messages=[
#         {
#             "role": "user",
#             "content": """
#             Explain this Java code and identify possible problems:
#
#             public void login(String username, String password) {
#                 driver.findElement(By.id("username")).sendKeys(username);
#                 driver.findElement(By.id("password")).sendKeys(password);
#                 driver.findElement(By.id("login")).click();
#             }
#             """
#         }
#     ]
# )
#
# print(response2["message"]["content"])
#
# question = """
# You are an AI testing assistant.
#
# Explain how AI can generate a Playwright test
# from a jira test case.
# """
#
# response3 = ollama.chat(
#     model=MODEL,
#     messages=[
#         {
#             "role": "user",
#             "content": question
#         }
#     ]
# )
#
# print(response3["message"]["content"])


print("Request:", requests)
print("File:", requests.__file__)

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

print("api_key:", bool(api_key))

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "openrouter/free",
    "messages": [
        {
            "role": "user",
            "content": "Explain Selenium Page Object Model"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

print("HTTP Status:", response.status_code)

if response.ok:
    result = response.json()

    print("\n========== AI RESPONSE ==========")

    answer = result["choices"][0]["message"]["content"]

    print(answer)

else:
    print("\n========== API ERROR ==========")
    # print(json.dumps(response.json(), indent=4))
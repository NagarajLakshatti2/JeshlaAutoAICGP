from dotenv import load_dotenv
import os
import requests

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
            "content": "how to play chess"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

print("HTTP Status:", response.status_code)

print("\n========== ACTUAL MODEL ==========")
result = response.json()
print(result.get("model"))

if response.ok:
    result = response.json()

    print("\n========== AI RESPONSE ==========")

    answer = result["choices"][0]["message"]["content"]

    print(answer)

else:
    print("\n========== API ERROR ==========")
    # print(json.dumps(response.json(), indent=4))
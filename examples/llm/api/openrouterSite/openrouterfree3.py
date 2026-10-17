import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

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

response = requests.post(
    url,
    headers=headers,
    json=data
)

result = response.json()

print("\n" + "=" * 60)
print("OPENROUTER RESULT")
print("=" * 60)

print("HTTP Status :", response.status_code)
print("Model       :", result.get("model"))

if "choices" in result:

    answer = result["choices"][0]["message"]["content"]

    print("\nAI RESPONSE")
    print("-" * 60)
    print(answer)

else:

    print("\nERROR")
    print(json.dumps(result, indent=4))
import requests

url = "https://openrouter.ai/api/v1/models"

response = requests.get(url)

models = response.json()["data"]

free_models = []

for model in models:

    pricing = model.get("pricing", {})

    if (
        pricing.get("prompt") == "0"
        and pricing.get("completion") == "0"
    ):
        free_models.append(model)

print("Total free models:", len(free_models))

for model in free_models:
    print(
        model["id"],
        " | ",
        model["name"]
    )
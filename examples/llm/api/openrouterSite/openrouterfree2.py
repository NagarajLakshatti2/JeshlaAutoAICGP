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


print("=" * 100)
print(f"FREE MODELS: {len(free_models)}")
print("=" * 100)

for i, model in enumerate(free_models, start=1):

    print(f"\n{i}. {model['name']}")
    print(f"   ID       : {model['id']}")
    print(f"   Context  : {model.get('context_length')}")

    architecture = model.get("architecture", {})

    print(
        f"   Input    : "
        f"{', '.join(architecture.get('input_modalities', []))}"
    )

    print(
        f"   Output   : "
        f"{', '.join(architecture.get('output_modalities', []))}"
    )

    print(
        f"   Tools    : "
        f"{'tools' in model.get('supported_parameters', [])}"
    )
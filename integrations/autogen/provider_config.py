"""Provider endpoint configuration for the isolated AutoGen worker."""
import os
from agent.providers.errors import ProviderError


PROVIDERS = ("openrouter", "groq", "gemini", "ollama")


def provider_config(provider, environ=None):
    """Return OpenAI-compatible model settings without exposing credentials."""
    env = os.environ if environ is None else environ
    if provider not in PROVIDERS:
        raise ProviderError("model", "CONFIGURATION", "Select OpenRouter, Groq, Gemini, or Ollama.", attempts=0)
    if provider == "openrouter":
        key, model = env.get("OPENROUTER_API_KEY", "").strip(), env.get("OPENROUTER_MODEL", "").strip()
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "groq":
        key, model = env.get("GROQ_API_KEY", "").strip(), env.get("GROQ_MODEL", "").strip()
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "gemini":
        from agent.providers.gemini import KEY_NAMES
        key = next((env.get(name, "").strip() for name in KEY_NAMES if env.get(name, "").strip()), "")
        model = env.get("GEMINI_MODEL", "").strip()
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    else:
        key, model = "ollama", env.get("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        endpoint = env.get("OLLAMA_URL", "http://localhost:11434/api/chat").strip()
        if not endpoint.startswith(("http://localhost:", "http://127.0.0.1:", "http://[::1]:")):
            raise ProviderError("ollama", "CONFIGURATION", "Ollama must use a local loopback endpoint.", attempts=0)
        base_url = endpoint.rsplit("/api/", 1)[0] + "/v1"
    if not model or (provider != "ollama" and not key):
        raise ProviderError(provider, "CONFIGURATION", "Configure the selected provider's model and local API key before using AutoGen.", attempts=0)
    return {"provider": provider, "model": model, "api_key": key, "base_url": base_url}

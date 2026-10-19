"""Google-only endpoint and backward-compatible local key lookup."""
import os
from agent.providers.errors import ProviderError

GEMINI_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
KEY_NAMES=("GEMINI_API_KEY","GOOGLE_AI_STUDIO_KEY","GOOGLE_AI_STUDEO_KEY","GOOGLE_API_KEY")

def credentials():
    key=next((os.getenv(name,"").strip() for name in KEY_NAMES if os.getenv(name,"").strip()),"")
    model=os.getenv("GEMINI_MODEL","").strip()
    if not key:
        raise ProviderError("gemini","CONFIGURATION","Set GEMINI_API_KEY locally, or use your existing GOOGLE_AI_STUDEO_KEY. Never paste the key into chat.",attempts=0)
    if not model:
        raise ProviderError("gemini","CONFIGURATION","Set GEMINI_MODEL to an available eligible model in .env and restart.",attempts=0)
    return key,model

def reasoning_effort():
    value=os.getenv("GEMINI_REASONING_EFFORT","low").strip().lower()
    if value not in {"none","minimal","low","medium","high"}:
        raise ProviderError("gemini","CONFIGURATION","GEMINI_REASONING_EFFORT must be none, minimal, low, medium or high and supported by the selected model.",attempts=0)
    return value

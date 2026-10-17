# Direct hosted model setup (Groq)

Create a Groq API key at https://console.groq.com/keys and check models available to your account at https://console.groq.com/docs/models.

Edit the existing project .env locally (do not share the key in chat):

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-entered-locally
GROQ_MODEL=openai/gpt-oss-20b
GROQ_MAX_TOKENS=1024
GROQ_TIMEOUT=90
```

The example is an open-weight model hosted by Groq; it does not use an OpenAI API key or OpenRouter. Model availability and limits depend on your account. Check pricing before paid usage.

Restart with `python -m agent.langgraph.langgraph_agent`. Test with a general question and confirm Provider: Groq in the logs. Memory shortcuts remain local. Model prompts, selected source content and supplied history are sent to Groq for model requests. Internet speed, rate limits and model response time affect latency.

No additional SDK is required; the existing requests package is used. To use Ollama again, set LLM_PROVIDER=ollama and restart. The standalone rag/rag_agent.py has its own OpenRouter client and is not migrated by this change.

# JeshlaAutoAI architecture

User message -> explicit command/action routing -> model with memory/history and native tool schemas -> validated local tool execution -> tool results linked by call ID -> model answer or clarification.

The model is hosted by Groq when LLM_PROVIDER=groq, hosted through OpenRouter when set to openrouter, or local through Ollama when set to ollama. Model support for native function calling is required. A provider key is not a model. Open weights do not mean free hosting.

Ordinary conversation uses agent/conversation.py and agent/tool_llm.py. It can answer directly, search indexed documents, search public web snippets, and read/search/list source files in AI_PROJECT_ROOT. Maximum six model rounds, eight executed tools, validated arguments and bounded evidence. Tool results remain associated with the native tool-call IDs. Web queries and hosted model context leave the computer; private data must not be put in public search terms. These instruction-based privacy controls are not a complete data-loss-prevention system.

Memory changes remain explicit commands. Jira and project edits/execution retain the existing guarded workflows. They are not yet migrated to native tool calls. This is the general model/tool-loop pattern, not a reproduction of ChatGPT, Claude or Devin internals. No browser interaction, automatic self-training, unrestricted filesystem access or guaranteed correctness is implied.

Web evidence is search snippets only. Indexed document search still depends on the existing ingestion indexes, embeddings and reranker environment. Missing dependencies or failed tools should be explained, never replaced with invented evidence.

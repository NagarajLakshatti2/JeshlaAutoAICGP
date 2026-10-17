# Table and saved-memory conversation tools

Implemented 17 October 2026. Shared by console and Streamlit through the existing conversation node.

## Completed scope (Y)

- list_tables discovers CSV/XLSX under the active configured local project root.
- search_table reads selected file/sheet/header rows, supports text search and one column filter (contains, eq, gt, ge, lt, le), and returns source row numbers.
- Multi-sheet workbooks require a sheet choice; ambiguous/duplicate headers are reported rather than guessed. header_row can select a header in the first 50 rows.
- Files are limited to 5 MB (XLSX expanded content 50 MB), 100 columns and 5,000 scanned data rows. At most 20 matches are returned within a response budget. Truncation is explicit; results are not full-table counts.
- Memory prompt context uses lexical relevance instead of the first saved keys. The model can call search_memory for additional facts in the current configured user/memory space. No model argument can select another user or namespace.
- SHOW MEMORY and the browser memory view retain their existing listing behavior and display budget. Facts remain shared across chats in the same user/memory space.
- Read-only: no spreadsheet edits, formula execution, shell actions or automatic memory writes. XLSX formulas expose cached values, which may be blank or stale.

## Files

| File | Change |
|---|---|
| agent/tools/table_tools.py | New bounded CSV/XLSX discovery, row retrieval, filters and source metadata. |
| agent/memory/long_term_memory.py | Scoped keyword ranking for saved keys and values, without embedding/model downloads. |
| agent/conversation.py | Registers table and memory tools; passes real results to the model; accepts table rows as RAG evidence. |
| agent/langgraph/langgraph_agent.py | Selects relevant prompt facts and supplies a memory-search callback bound to the configured identity. |
| tests/test_table_memory_tools.py | Nine offline tests for real temporary files, SQLite persistence/scope, filtering and fake-model tool integration. |

## Try after restarting the agent

```text
List the CSV and Excel files available in my configured project folder.
```

Then use an actual returned relative path:

```text
Read the workbook <relative path>. Show its sheets first, then ask me which sheet to search.
```

```text
Using my saved memory, what is my project name and build tool?
```

Replace placeholders with real paths. Desktop files outside the configured project root are not accessible through these tools; use a copy under the active root or deliberately configure the intended root. No change to AI_PROJECT_ROOT was made.

## Validation and remaining work

129 guarded offline tests passed in 3.374 seconds. No live provider or Jira call was needed. This verifies code integration, not that every model will always select the ideal tool.

P - broader memory/RAG acceptance: lexical search is not semantic retrieval, arbitrary-language paraphrases may miss facts, and large/complex tables need narrower queries. No total-count aggregation, multi-filter query language, automatic header detection, scanned-PDF parsing or validated final-answer citations was added. The older standalone RAG demos remain intact. Live console/browser model selection and answer grounding remain to be evaluated.

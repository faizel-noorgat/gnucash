## Doc Exploration Policy

Always use jDocMunch-MCP tools for documentation navigation. Never fall back to Read for doc exploration.
**Exception:** Use `Read` when you need exact line numbers for `Edit`.

**Start any session:**
1. `doc_list_repos` — check what's indexed. If your docs aren't there: `index_local { "path": "." }`

**Indexing (always incremental, always summarized + embedded):**
- `index_local { "path": ".", "incremental": true, "use_ai_summaries": true, "use_embeddings": true }`
- `use_embeddings` defaults to `"auto"`, which embeds only when an embedding provider is configured (here: `JDOCMUNCH_OPENAI_COMPAT_URL` + model + key, Voyage). Unset provider → the index comes back lexical-only without failing, so check the response
- incremental runs lag on embeddings: the response reports `embedding_coverage` and warns when it is low, naming the fix. Observed on this repo: 945/4,088 sections (23.1%) after an incremental run. When semantic ranking matters, follow with `index_local { "path": ".", "incremental": false }`

**Finding content:**
- keyword/topic search -> `search_sections` (returns summaries only)
- browse structure -> `get_toc` (flat) or `get_toc_tree` (nested)
- single document -> `get_document_outline`

**Reading content:**
- one section -> `get_section` (full content via byte-range)
- multiple sections -> `get_sections` (batch)
- section + context -> `get_section_context` (ancestors + children)

**Maintenance:**
- broken internal links -> `get_broken_links`
- code/doc coverage gap -> `get_doc_coverage`

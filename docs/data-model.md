# Data Model

Current tables:

- `papers`: bibliographic metadata, DOI, normalized title, provider provenance.
- `paper_contents`: abstract or full-text extraction state, cleaned text, checksums, parser/extractor metadata.
- `paper_content_pages`: page-level text offsets for PDF full text.
- `paper_chunks`: section-aware evidence chunks with character, paragraph, and optional page ranges.
- `paper_relevance_assessments`: cached deterministic relevance scores keyed by paper, content, checksum, scope, and model versions.
- `llm_runs`: provider/model/prompt/schema/input provenance for one LLM request sequence, including selected chunk IDs, request status, repair attempts, provider request ID, token usage, latency, optional cost, error category, and timestamps.
- `paper_analyses`: structured analysis records keyed by paper/content identity, content checksum, selected evidence checksum, schema version, provider/model, and prompt version, with validated analysis JSON, validation errors, and status.

JSONB is used for relevance diagnostics, selected chunk IDs, validation errors, and validated analysis payloads because these are structured values converted at repository boundaries.

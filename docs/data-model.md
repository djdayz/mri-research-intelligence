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

Retrieval query indexes support the public search API:

- `papers.publication_date`, `papers.created_at`, and `papers.ingestion_source` for date/source filters and stable sorts.
- `paper_contents.content_type, extraction_status, paper_id` for content-scope and extraction-state filters.
- `paper_relevance_assessments.rule_label, normalized_score` and a GIN index on `category_scores` for relevance label, score sorting, and category lookup.
- `paper_analyses.status, analysis_scope, paper_id` for analysis availability filters.

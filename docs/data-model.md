# Data Model

Current tables:

- `papers`: bibliographic metadata, DOI, normalized title, provider provenance.
- `paper_contents`: abstract or full-text extraction state, cleaned text, checksums, parser/extractor metadata.
- `paper_content_pages`: page-level text offsets for PDF full text.
- `paper_chunks`: section-aware evidence chunks with character, paragraph, and optional page ranges.
- `paper_relevance_assessments`: cached deterministic relevance scores keyed by paper, content, checksum, scope, and model versions.

JSONB is used for relevance category scores, matched concepts/terms, and supporting locations because these are structured diagnostics returned at repository boundaries.

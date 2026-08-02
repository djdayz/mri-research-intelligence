# Scientific Safety

MRInsight separates deterministic evidence processing from future LLM generation.

Current safety controls:

- Abstract and full-text scopes are distinct.
- Full-text PDF uploads require validation and user-supplied access provenance.
- PDF extraction records page counts, text-bearing pages, checksums, extractor name, and failures.
- Evidence chunks keep section, character, paragraph, and optional page ranges.
- Relevance scoring reports matched concepts, matched terms, category scores, and supporting locations.

Known limits:

- pypdf does not guarantee perfect reading order, tables, equations, columns, or figure relationships.
- OCR is not implemented.
- Deterministic relevance is not clinical validation.
- Future LLM analysis must reject unsupported claims and invalid evidence references.

# Scientific Safety

MRInsight separates deterministic evidence processing from LLM generation.

Current safety controls:

- Abstract and full-text scopes are distinct.
- Full-text PDF uploads require validation and user-supplied access provenance.
- PDF extraction records page counts, text-bearing pages, checksums, extractor name, and failures.
- Evidence chunks keep section, character, paragraph, and optional page ranges.
- Relevance scoring reports matched concepts, matched terms, category scores, and supporting locations.
- Analysis evidence selection excludes references by default, keeps selected chunk IDs reproducible, and respects a configured prompt budget estimate.
- Scientific-analysis schema requires evidence for reported and uncertain claims.
- Analysis evidence validation rejects unknown chunks, wrong content, wrong offsets, unsupported excerpts, abstract/full-text scope mismatch, references-section evidence by default, and numerical values absent from cited text.
- Analysis persistence records provider/model/prompt/schema/input metadata, selected evidence identity, request status, validation errors, and cache identity.
- Discovery records provider provenance, DOI/title-year deduplication outcomes, candidate statuses, rank positions, and errors.
- Digest HTML rendering escapes untrusted paper and provider text, and digest previews do not claim Crossref or any provider has complete literature coverage.

Known limits:

- pypdf does not guarantee perfect reading order, tables, equations, columns, or figure relationships.
- OCR is not implemented.
- Deterministic relevance is not clinical validation.
- Live LLM calls require a configured provider and API key; normal automated tests use deterministic fakes.
- Crossref discovery is metadata search with incomplete abstract and coverage availability.

# Scientific Safety

MRInsight separates deterministic evidence processing from future LLM generation.

Current safety controls:

- Abstract and full-text scopes are distinct.
- Full-text PDF uploads require validation and user-supplied access provenance.
- PDF extraction records page counts, text-bearing pages, checksums, extractor name, and failures.
- Evidence chunks keep section, character, paragraph, and optional page ranges.
- Relevance scoring reports matched concepts, matched terms, category scores, and supporting locations.
- Scientific-analysis schema requires evidence for reported and uncertain claims.
- Analysis evidence validation rejects unknown chunks, wrong content, wrong offsets, unsupported excerpts, abstract/full-text scope mismatch, references-section evidence by default, and numerical values absent from cited text.

Known limits:

- pypdf does not guarantee perfect reading order, tables, equations, columns, or figure relationships.
- OCR is not implemented.
- Deterministic relevance is not clinical validation.
- Real LLM calls and analysis persistence are not yet implemented.

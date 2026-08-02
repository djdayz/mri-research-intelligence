# MRInsight Implementation Progress

Status is based on local repository verification on 2026-08-02. A box is marked complete only when covered by implementation and tests available in this repository.

## Milestones 1-6

- [x] Milestone 1: FastAPI foundation
- [x] Milestone 2: PostgreSQL foundation
- [x] Milestone 3: Paper model and migrations
- [x] Milestone 4: DOI and title normalisation
- [x] Milestone 5: Bibliographic ingestion
- [x] Milestone 6A: Content foundation
- [x] Milestone 6B: Abstract evidence persistence
- [x] Milestone 6C: Section detection
- [x] Milestone 6D: Chunk schema and deterministic chunking
- [x] Milestone 6E: Chunk persistence
- [x] Milestone 6F: PDF extraction boundary
- [x] Milestone 6G: Full-text ingestion

## Milestone 7

- [x] 7A: Versioned MRI/CVR terminology ontology
- [x] 7B: Rule-based relevance scoring
- [x] 7C: TF-IDF topic baseline
- [x] 7D: Relevance persistence and API integration

## Milestones 8-16

- [ ] Milestone 8: Structured scientific-analysis contract
- [ ] Milestone 9: Real LLM analysis
- [ ] Milestone 10: Search and retrieval API
- [ ] Milestone 11: Discovery, subscriptions, and digest preview
- [ ] Milestone 12: MVP hardening
- [ ] Phase 13: Real email and scheduling
- [ ] Phase 14: LLM evaluation and advanced observability
- [ ] Phase 15: Production deployment
- [ ] Phase 16: Portfolio polish

## Current Next Best Step

Implement Milestone 8 before adding live LLM calls: define the strict analysis schema, evidence-reference validation, fake LLM provider, prompt files, and bounded invalid-output repair policy.

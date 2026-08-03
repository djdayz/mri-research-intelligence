# MRInsight Implementation Progress

Status is based on local repository verification on 2026-08-03. A box is marked complete only when covered by implementation and tests available in this repository.

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

## Milestone 8

- [x] 8A: Complete Pydantic analysis schema
- [x] 8B: Evidence and numerical-result validation
- [x] 8C: Prompt files, prompt versioning, and fake LLM provider
- [x] 8D: Invalid-output rejection and repair policy

## Milestone 9

- [x] 9A: Real LLM provider adapter
- [x] 9B: Evidence ranking and prompt assembly
- [x] 9C: Analysis and LLM-run persistence
- [x] 9D: Analysis API

## Milestone 10

- [x] 10A: Paper list and detail endpoints
- [x] 10B: Pagination, filters, and sorting
- [x] 10C: Indexes and query optimisation
- [x] 10D: Retrieval tests and API documentation

## Milestone 11

- [x] 11A: Topic and subscription models
- [x] 11B: Discovery, deduplication, and ranking
- [x] 11C: Digest generation and preview delivery
- [x] 11D: Manual digest API and CLI

## Milestone 12

- [x] 12A: Concurrent duplicate recovery
- [x] 12B: Complete end-to-end test
- [x] 12C: Migration and CI hardening
- [x] 12D: Structured logging and baseline observability
- [x] 12E: README, architecture, and API documentation
- [x] 12F: Release candidate and demo workflow

## Phase 13

- [x] 13A: Real delivery adapter
- [x] 13B: Scheduled execution
- [x] 13C: Delivery idempotency and retry

## Phase 14

- [x] 14A: Golden evaluation set
- [x] 14B: Automated regression evaluation
- [x] 14C: Cost, latency, and quality metrics

## Phase 15

- [x] 15A: Docker
- [x] 15B: Cloud deployment configuration
- [x] 15C: Production database and secrets
- [x] 15D: CI/CD

## Phase 16

- [x] 16A: Portfolio case study
- [x] 16B: Architecture visuals
- [x] 16C: Demonstration assets
- [x] 16D: Employer-facing quality review

## Final Verification

- [x] Repository and tracked-file audit
- [x] Code quality gates
- [x] PostgreSQL-backed test suite
- [x] Alembic head and schema-drift checks, including migration from a clean reset test database schema
- [x] API smoke verification with fake providers
- [x] Security and dead-code searches
- [ ] Local Docker build and compose run, blocked on Docker not being installed in this local environment

## Current Next Best Step

Prepare external live-demo configuration outside source control: OpenAI API key, Crossref contact email, SMTP credentials, production database URL, cloud deployment credentials, and domain/DNS settings.

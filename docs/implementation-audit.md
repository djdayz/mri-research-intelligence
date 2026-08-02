# MRInsight Implementation Audit

Audit date: 2026-08-02

## Repository State

- Branch at audit start: `feat/full-text-ingestion`
- Latest commit at audit start: `2127221 feat: add full text PDF ingestion`
- Package root: `src/mrinsight`
- Local project interpreter used for verification: `.venv/bin/python`
- Python version observed: 3.13.7

## Dependency Snapshot

Major installed packages observed during audit:

- FastAPI 0.140.3
- SQLAlchemy 2.0.51
- Pydantic 2.13.4
- Alembic 1.18.5
- pytest 9.1.1
- Ruff 0.16.0
- mypy 1.20.2
- scikit-learn 1.9.0 added for the deterministic TF-IDF topic baseline

## Implemented Structure

- API layer: health, DOI ingestion, PDF full-text upload, deterministic relevance assessment
- Application services: DOI ingestion, abstract storage, full-text ingestion, chunk building, analysis-content selection, relevance assessment
- Domain records/protocols: papers, content, chunks, providers, relevance records, relevance repository protocol
- Persistence: SQLAlchemy repositories for papers, content, pages, chunks, relevance assessments
- NLP: text cleaning, section detection, section-aware chunking, terminology matching, rule-based relevance scoring, TF-IDF baseline
- External providers: Crossref adapter, fake bibliographic provider, unconfigured provider

## API Routes

- `GET /health`
- `POST /papers`
- `POST /papers/{paper_id}/full-text`
- `POST /papers/{paper_id}/relevance`

## Database Tables

- `papers`
- `paper_contents`
- `paper_content_pages`
- `paper_chunks`
- `paper_relevance_assessments`
- `alembic_version`

Current Alembic head after this pass: `4af4a9d74a1d`

## Verification Results

Baseline before relevance work:

- `.venv/bin/python -m ruff check .`: passed
- `.venv/bin/python -m ruff format --check .`: passed
- `.venv/bin/python -m mypy`: passed
- `.venv/bin/python -m pytest`: 155 passed
- `.venv/bin/python -m alembic current --check-heads`: passed at `8f8d1c2e7b90`
- `.venv/bin/python -m alembic check`: no new upgrade operations detected

After relevance work, final verification commands are recorded in the final response for this pass.

## Repairs And Additions In This Pass

- Added versioned MRI/CVR terminology ontology as `src/mrinsight/relevance/ontology.json`.
- Added boundary-aware terminology matcher with Unicode, hyphen, punctuation, field-strength, overlap, and false-positive tests.
- Added deterministic rule-based relevance scoring with category scores, matched concepts, supporting locations, and explanations.
- Added scikit-learn TF-IDF topic baseline with deterministic fixture tests and explicit metadata.
- Added PostgreSQL `paper_relevance_assessments` model, repository, indexes, constraints, and Alembic migration.
- Added cached relevance-assessment service using selected analysis content and content checksum/version identity.
- Added `POST /papers/{paper_id}/relevance`.
- Added `py.typed` marker so strict typing applies cleanly to package imports in tests.

## Remaining Major Gaps

The repository is not yet a complete implementation of the full master prompt. Major incomplete areas include:

- Structured LLM analysis schema, fake provider, repair policy, and real provider adapter.
- Analysis evidence validation and persistence.
- Search/list/detail retrieval endpoints.
- Discovery, subscriptions, digests, delivery providers, and CLI.
- Concurrency recovery hardening across all duplicate write paths.
- Structured logging, request correlation, readiness checks, Docker/deployment assets, and release/demo automation.
- Complete portfolio documentation and end-to-end fake-provider workflow.

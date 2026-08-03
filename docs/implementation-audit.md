# MRInsight Implementation Audit

Audit date: 2026-08-03

## Repository State

- Branch at latest portfolio review: `feat/portfolio-polish`
- Latest merged baseline before this review: production deployment branch merged into `main`
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

- API layer: health/readiness, DOI ingestion, PDF full-text upload, relevance, analysis, retrieval, discovery, subscriptions, and digest preview
- Application services: DOI ingestion, abstract storage, full-text ingestion, chunk building, analysis-content selection, relevance assessment, analysis generation, retrieval, discovery, and digest generation
- Domain records/protocols: papers, content, chunks, providers, relevance, analysis, retrieval, discovery, digest, and delivery contracts
- Persistence: SQLAlchemy repositories for papers, content, pages, chunks, relevance assessments, LLM runs, analyses, topics, subscriptions, discovery runs/candidates, digests, and deliveries
- NLP: text cleaning, section detection, section-aware chunking, terminology matching, rule-based relevance scoring, TF-IDF baseline, and deterministic evidence selection
- External providers: Crossref bibliographic/discovery adapters, OpenAI Responses adapter, SMTP provider, file/console delivery providers, and deterministic fakes

## API Routes

- `GET /health`
- `GET /ready`
- `POST /papers`
- `POST /papers/{paper_id}/full-text`
- `POST /papers/{paper_id}/relevance`
- `POST /papers/{paper_id}/analysis`
- `GET /papers/{paper_id}/analysis`
- `GET /analyses/{analysis_id}`
- `GET /papers`
- `GET /papers/{paper_id}`
- `GET /papers/{paper_id}/contents`
- `GET /papers/{paper_id}/chunks`
- `GET /topics`
- `POST /subscriptions`
- `GET /subscriptions`
- `POST /subscriptions/{subscription_id}/digest-preview`
- `GET /digests/{digest_id}`

## Database Tables

- `papers`
- `paper_contents`
- `paper_content_pages`
- `paper_chunks`
- `paper_relevance_assessments`
- `llm_runs`
- `paper_analyses`
- `topics`
- `subscriptions`
- `subscription_topics`
- `discovery_runs`
- `discovery_candidates`
- `digests`
- `digest_deliveries`
- `alembic_version`

Current Alembic head after this pass: `5d3b9a1c4e22`

## Current Verification Gates

The repository is expected to pass:

- `.venv/bin/python -m ruff check .`: passed
- `.venv/bin/python -m ruff format --check .`: passed
- `.venv/bin/python -m mypy`: passed
- `.venv/bin/python -m pytest`: 248 passed, 0 skipped
- `.venv/bin/python -m alembic current --check-heads`: passed at current head
- `.venv/bin/python -m alembic check`: no new upgrade operations detected
- `.venv/bin/python -m mrinsight.cli eval run --output var/evaluation/golden-report.json`: passed with deterministic fake provider
- API process smoke test: `/health`, `/ready`, and `/openapi.json` passed against the migrated test database
- Fake-provider API workflow: DOI ingestion, relevance, analysis, retrieval, subscription, digest preview, and digest retrieval passed in `tests/api/test_mvp_workflow.py`
- Docker build and Compose run: not locally verified because Docker is not installed in this environment

See `docs/testing.md` and `docs/release-checklist.md` for the current release gates.

## Selected Implementation Notes

- Added versioned MRI/CVR terminology ontology as `src/mrinsight/relevance/ontology.json`.
- Added boundary-aware terminology matcher with Unicode, hyphen, punctuation, field-strength, overlap, and false-positive tests.
- Added deterministic rule-based relevance scoring with category scores, matched concepts, supporting locations, and explanations.
- Added scikit-learn TF-IDF topic baseline with deterministic fixture tests and explicit metadata.
- Added PostgreSQL `paper_relevance_assessments` model, repository, indexes, constraints, and Alembic migration.
- Added cached relevance-assessment service using selected analysis content and content checksum/version identity.
- Added `POST /papers/{paper_id}/relevance`.
- Added `py.typed` marker so strict typing applies cleanly to package imports in tests.

## Milestone 8 Additions

- Added strict versioned scientific-analysis schema with evidence-backed text fields, unavailable-information statuses, and typed numerical results.
- Added persisted-chunk evidence validator checking paper/content identity, chunk identity, sections, page ranges, character offsets, excerpts, abstract/full-text scope, references-section exclusion, and numerical attribution.
- Added prompt templates with prompt versions and checksums.
- Added provider-independent LLM request/response records and deterministic fake LLM provider modes for valid output, malformed JSON, schema-invalid output, missing evidence, bad chunk references, scope mismatch, numerical inconsistency, timeout, failure, and repairable malformed JSON.
- Added bounded generation service: validate first output, perform at most one repair request, validate repaired output, and fail honestly with diagnostics if still invalid.
- Added retrieval, discovery, digest, SMTP, scheduling, observability, deployment, and portfolio layers with offline tests and synthetic demo assets.

## Current External Actions

The repository now implements the local code, tests, documentation, CI, and deployment scaffolding for the master prompt. The remaining work is intentionally external to source control:

- configure real OpenAI, SMTP, Crossref mailto, database, and cloud deployment secrets in a secret store;
- run live LLM/provider/email checks only when credentials and cost approval are available;
- choose a production hosting target, domain, backup policy, and monitoring retention settings;
- verify Docker build and deployment in an environment with Docker and target infrastructure available.

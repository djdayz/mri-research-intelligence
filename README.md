# MRInsight

MRInsight is an MRI-focused research intelligence API. It ingests papers by DOI, stores bibliographic provenance, persists abstract and permitted PDF full text, creates section-aware evidence chunks, and now computes deterministic MRI/CVR relevance assessments.

The project is intentionally evidence-first. Abstract-only content is kept distinct from full-text evidence, uploaded PDFs are validated rather than scraped, and deterministic extraction/chunking/relevance happens before any future LLM analysis.

## Current Capabilities

- FastAPI application with typed settings under the `MRINSIGHT_` environment prefix.
- PostgreSQL persistence with SQLAlchemy 2.x and Alembic migrations.
- DOI ingestion through Crossref or a deterministic fake provider in tests.
- Abstract cleaning, checksum generation, and section-aware chunk persistence.
- PDF upload validation and pypdf extraction boundary with page-aware records.
- Analysis-content selection preferring successful full text over abstracts.
- Versioned MRI/CVR terminology ontology, rule-based relevance scoring, TF-IDF baseline, and cached relevance API.
- Strict scientific-analysis schema, fake LLM provider contract, prompt versioning, evidence validation, and bounded one-repair invalid-output policy.

## Local Setup

```bash
python -m pip install -e ".[dev]"
set -a
source .env
set +a
python -m alembic upgrade head
python -m uvicorn mrinsight.main:app --reload
```

For this local repository, the verified commands used `.venv/bin/python`.

## Quality Gates

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest
python -m alembic current --check-heads
python -m alembic check
```

Integration tests require PostgreSQL and `MRINSIGHT_TEST_DATABASE_URL`.

## API Examples

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/papers \
  -H "content-type: application/json" \
  -d '{"doi":"10.1234/example"}'
curl -X POST http://localhost:8000/papers/1/relevance
```

PDF upload:

```bash
curl -X POST http://localhost:8000/papers/1/full-text \
  -F "file=@permitted-paper.pdf;type=application/pdf"
```

## Scientific Limitations

- Crossref coverage and abstracts are incomplete.
- pypdf extraction does not guarantee perfect reading order, tables, equations, columns, or figure relationships.
- No OCR is implemented.
- Deterministic relevance is triage logic, not clinical validation.
- The TF-IDF model is an interpretable baseline trained from caller-provided fixtures, not a clinically validated classifier.
- Real LLM provider calls, analysis persistence/API, discovery, subscriptions, digests, delivery, Docker, and production deployment are still pending.

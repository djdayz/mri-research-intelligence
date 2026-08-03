# MRInsight

MRInsight is an MRI-focused research intelligence API. It ingests papers by DOI, stores bibliographic provenance, persists abstract and permitted PDF full text, creates section-aware evidence chunks, computes deterministic MRI/CVR relevance assessments, and generates structured evidence-linked analyses through a configurable LLM provider.

The project is intentionally evidence-first. Abstract-only content is kept distinct from full-text evidence, uploaded PDFs are validated rather than scraped, and deterministic extraction/chunking/evidence selection happens before LLM analysis.

## Current Capabilities

- FastAPI application with typed settings under the `MRINSIGHT_` environment prefix.
- PostgreSQL persistence with SQLAlchemy 2.x and Alembic migrations.
- DOI ingestion through Crossref or a deterministic fake provider in tests.
- Abstract cleaning, checksum generation, and section-aware chunk persistence.
- PDF upload validation and pypdf extraction boundary with page-aware records.
- Analysis-content selection preferring successful full text over abstracts.
- Versioned MRI/CVR terminology ontology, rule-based relevance scoring, TF-IDF baseline, and cached relevance API.
- Strict scientific-analysis schema, fake LLM provider contract, OpenAI Responses API adapter, prompt versioning, deterministic evidence selection, evidence validation, and bounded one-repair invalid-output policy.
- `LLMRun` and `PaperAnalysis` persistence with provider/model/prompt/schema/input checksums, selected chunk IDs, token usage, request IDs, latency, status, validation errors, and cache-aware analysis retrieval.
- Search and retrieval API for paginated paper lists, paper detail, content metadata, explicit chunk retrieval, filters, stable sorting, and related-resource links.
- Topic subscriptions, Crossref discovery search, deterministic fake discovery, DOI/title-year deduplication, discovery run/candidate persistence, digest preview rendering, fake/file/console delivery providers, and SMTP email delivery.
- Scheduled one-shot digest and delivery-retry CLI commands suitable for cron, container schedulers, or cloud scheduled tasks.
- Deterministic golden LLM evaluation command with machine-readable quality, token, latency, and estimated-cost metrics.
- Production Dockerfile, local Docker Compose stack, Kubernetes deployment template, and gated CI/CD workflow scaffolding.
- MVP hardening for duplicate insert recovery, digest idempotency, request correlation IDs, structured JSON logs, readiness checks, and a public API E2E workflow.
- Portfolio case study, architecture diagrams, and synthetic demonstration assets suitable for employer review.

## Local Setup

```bash
python -m pip install -e ".[dev]"
set -a
source .env
set +a
python -m alembic upgrade head
python -m mrinsight.cli seed demo
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

CI runs these checks on Python 3.11 after applying migrations and verifying the Alembic head. Local development in this checkout has also been verified with `.venv/bin/python`.

## Operations

`GET /health` is a liveness check for the API process. `GET /ready` verifies database connectivity and should be used before demos or deployment traffic. Every response includes an `x-request-id` header; callers may supply one, otherwise the API creates it.

Application logs are single-line JSON events. The API logs request completion without request bodies, and the discovery/digest/analysis paths log provider name, status, duration, and compact non-secret identifiers.

Repository writes that have natural uniqueness constraints recover from duplicate insert races through a savepoint and re-query the existing row. This is used for papers, content, chunks, relevance assessments, successful analysis cache rows, digests, and digest deliveries. Failed analyses remain retryable.

Digest delivery can run through `file`, `console`, or `smtp` providers. SMTP requires `MRINSIGHT_DIGEST_DELIVERY_PROVIDER=smtp`, `MRINSIGHT_SMTP_HOST`, `MRINSIGHT_SMTP_SENDER`, and optional SMTP username/password/TLS settings. Normal tests do not send live email.

Scheduled execution should invoke one-shot CLI commands from cron, a container scheduler, or a cloud scheduled task:

```bash
python -m mrinsight.cli digest run-due --rows 20
python -m mrinsight.cli digest retry-deliveries --limit 20
```

Run deterministic LLM regression evaluation without live provider calls:

```bash
python -m mrinsight.cli eval run --output var/evaluation/golden-report.json
```

Configured-provider evaluation requires `--allow-live` and may call OpenAI if `MRINSIGHT_LLM_PROVIDER=openai` and `MRINSIGHT_LLM_API_KEY` are set.

Run the local container stack:

```bash
docker compose up --build api
```

The compose stack starts PostgreSQL, runs Alembic migrations once, then serves the API on `http://localhost:8000`.

## Portfolio And Demo Assets

- [Portfolio case study](docs/portfolio-case-study.md)
- [Architecture diagrams](docs/architecture.md)
- [Demo guide](docs/demo.md)
- [Synthetic demo assets](docs/demo-assets)
- [Final verification report](docs/final-verification.md)

## API Examples

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -X POST http://localhost:8000/papers \
  -H "content-type: application/json" \
  -d '{"doi":"10.1234/example"}'
curl -X POST http://localhost:8000/papers/1/relevance
curl -X POST http://localhost:8000/papers/1/analysis
curl 'http://localhost:8000/papers?limit=25&sort=relevance_score&content_scope=abstract'
curl http://localhost:8000/papers/1
curl http://localhost:8000/papers/1/contents
curl 'http://localhost:8000/papers/1/chunks?section=methods'
curl http://localhost:8000/papers/1/analysis
curl http://localhost:8000/analyses/1
curl http://localhost:8000/topics
curl -X POST http://localhost:8000/subscriptions \
  -H "content-type: application/json" \
  -d '{"name":"Weekly MRI CVR","discovery_query":"MRI CVR","topic_ids":[1]}'
curl -X POST http://localhost:8000/subscriptions/1/digest-preview \
  -H "content-type: application/json" \
  -d '{"rows":10}'
curl http://localhost:8000/digests/1
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
- Live LLM calls require `MRINSIGHT_LLM_PROVIDER=openai` and `MRINSIGHT_LLM_API_KEY`; normal tests use deterministic fakes and do not call live providers.
- Crossref discovery is metadata search and does not represent complete global literature coverage.
- Cloud credentials, production domain configuration, and live deployment verification are intentionally not included.
